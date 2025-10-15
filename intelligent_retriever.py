import os
from typing import Dict, List, Any, Optional, TypedDict
from dataclasses import dataclass
import asyncio
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import redis
from datetime import datetime, timedelta

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver


class RetrieverState(TypedDict):
    query: str
    user_id: str
    documents: List[Document]
    search_type: str
    confidence: float
    reasoning: str
    context_used: bool
    conversation_history: List[Dict]


@dataclass
class RetrievalConfig:
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "vector_db"
    db_user: str = "postgres"
    db_password: str = "postgres123"
    table_name: str = "documents"
    max_docs: int = 5
    similarity_threshold: float = 0.7
    web_search_max_results: int = 3
    redis_url: str = "redis://localhost:6379"
    session_ttl: int = 1800
    max_session_messages: int = 10


class PostgreSQLVectorStore:
    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.connection = None
        self._connect()
        self._create_table_if_not_exists()

    def _connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                database=self.config.db_name,
                user=self.config.db_user,
                password=self.config.db_password
            )
        except Exception as e:
            print(f"Database connection error: {e}")
            self.connection = None

    def _create_table_if_not_exists(self):
        if not self.connection:
            return
        
        create_table_sql = f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        
        CREATE TABLE IF NOT EXISTS {self.config.table_name} (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB,
            embedding vector(768),
            source VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS {self.config.table_name}_embedding_idx 
        ON {self.config.table_name} USING ivfflat (embedding vector_cosine_ops);
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_sql)
                self.connection.commit()
        except Exception as e:
            print(f"Error creating table: {e}")

    def add_documents(self, documents: List[Document], embeddings):
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                for doc, embedding in zip(documents, embeddings):
                    cursor.execute(
                        f"""
                        INSERT INTO {self.config.table_name} (content, metadata, embedding, source)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            doc.page_content,
                            json.dumps(doc.metadata),
                            embedding.tolist(),
                            doc.metadata.get('source', 'unknown')
                        )
                    )
                self.connection.commit()
        except Exception as e:
            print(f"Error adding documents: {e}")

    def similarity_search(self, query_embedding, k: int = 5):
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    f"""
                    SELECT content, metadata, source, 
                           1 - (embedding <=> %s) as similarity
                    FROM {self.config.table_name}
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (query_embedding.tolist(), query_embedding.tolist(), k)
                )
                
                results = cursor.fetchall()
                documents = []
                
                for row in results:
                    metadata = json.loads(row['metadata']) if row['metadata'] else {}
                    doc = Document(
                        page_content=row['content'],
                        metadata={
                            'source': row['source'],
                            'similarity': row['similarity'],
                            **metadata
                        }
                    )
                    documents.append(doc)
                
                return documents
        except Exception as e:
            print(f"Error in similarity search: {e}")
            return []


class SessionMemory:
    def __init__(self, redis_url: str = "redis://localhost:6379", session_ttl: int = 1800, max_messages: int = 10):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.session_ttl = session_ttl
        self.max_messages = max_messages
    
    def _get_session_key(self, user_id: str) -> str:
        return f"session:{user_id}"
    
    def add_message(self, user_id: str, query: str, response: Dict[str, Any]):
        session_key = self._get_session_key(user_id)
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "strategy_used": response.get("strategy_used", "unknown"),
            "document_count": response.get("document_count", 0),
            "reasoning": response.get("reasoning", ""),
            "key_points": self._extract_key_points(response.get("documents", []))
        }
        
        self.redis_client.lpush(session_key, json.dumps(message))
        self.redis_client.ltrim(session_key, 0, self.max_messages - 1)
        self.redis_client.expire(session_key, self.session_ttl)
    
    def get_conversation_context(self, user_id: str) -> List[Dict]:
        session_key = self._get_session_key(user_id)
        messages = self.redis_client.lrange(session_key, 0, -1)
        return [json.loads(msg) for msg in messages]
    
    def _extract_key_points(self, documents: List[Document]) -> List[str]:
        if not documents:
            return []
        
        key_points = []
        for doc in documents[:3]:
            content = doc.page_content[:200]
            key_points.append(f"From {doc.metadata.get('source', 'unknown')}: {content}...")
        return key_points
    
    def clear_session(self, user_id: str):
        session_key = self._get_session_key(user_id)
        self.redis_client.delete(session_key)


class CustomDocumentRetriever(BaseRetriever):
    config: RetrievalConfig
    embeddings: Any
    max_docs: int
    vector_store: Optional[PostgreSQLVectorStore] = None
    
    def __init__(self, config: RetrievalConfig, embeddings, max_docs: int = 5):
        super().__init__(config=config, embeddings=embeddings, max_docs=max_docs)
        self.vector_store = PostgreSQLVectorStore(config)
        self._load_documents()

    def _load_documents(self):
        if not self.vector_store.connection:
            return
        
        documents = []
        for filename in os.listdir("."):
            if filename.endswith(('.pdf', '.txt', '.docx')):
                try:
                    if filename.endswith('.pdf'):
                        loader = PyPDFLoader(filename)
                    else:
                        loader = TextLoader(filename)
                    docs = loader.load()
                    documents.extend(docs)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        if documents:
            embeddings = self.embeddings.embed_documents([doc.page_content for doc in documents])
            self.vector_store.add_documents(documents, embeddings)
        else:
            dummy_doc = Document(page_content="No documents found", metadata={"source": "dummy"})
            dummy_embedding = self.embeddings.embed_query(dummy_doc.page_content)
            self.vector_store.add_documents([dummy_doc], [dummy_embedding])

    def _get_relevant_documents(self, query: str) -> List[Document]:
        if not self.vector_store.connection:
            return []
        
        query_embedding = self.embeddings.embed_query(query)
        documents = self.vector_store.similarity_search(query_embedding, self.max_docs)
        
        return [doc for doc in documents if doc.metadata.get('similarity', 0) >= self.config.similarity_threshold]


class WebSearchRetriever(BaseRetriever):
    search_tool: Optional[DuckDuckGoSearchRun] = None
    max_results: int
    
    def __init__(self, max_results: int = 3):
        super().__init__(max_results=max_results)
        self.search_tool = DuckDuckGoSearchRun()

    def _get_relevant_documents(self, query: str) -> List[Document]:
        try:
            search_results = self.search_tool.run(query)
            if not search_results:
                return []
            
            documents = []
            results = search_results.split('\n\n')[:self.max_results]
            
            for i, result in enumerate(results):
                if result.strip():
                    doc = Document(
                        page_content=result,
                        metadata={
                            "source": "web_search",
                            "rank": i + 1,
                            "query": query
                        }
                    )
                    documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Web search error: {e}")
            return []


class IntelligentRetriever:
    def __init__(self, config: RetrievalConfig = None):
        self.config = config or RetrievalConfig()
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        self.session_memory = SessionMemory(
            self.config.redis_url,
            self.config.session_ttl,
            self.config.max_session_messages
        )
        
        self.custom_retriever = CustomDocumentRetriever(
            self.config,
            self.embeddings,
            self.config.max_docs
        )
        
        self.web_retriever = WebSearchRetriever(
            self.config.web_search_max_results
        )
        
        self.context_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a context-aware retrieval engine. Analyze the user query considering their conversation history and determine the best retrieval strategy.

Available strategies:
1. "custom" - Use local document database (good for specific, internal, or known topics)
2. "web" - Use web search (good for current events, general knowledge, or topics not in local database)

Consider these factors:
- Current query context and intent
- Previous conversation topics and patterns
- Whether this builds on previous questions
- If user is asking follow-up questions about previous results
- Current/recent events vs internal knowledge

Conversation History: {conversation_history}

Respond with JSON format:
{{
    "strategy": "custom" or "web",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation considering context",
    "context_used": true/false
}}"""),
            ("human", "Current Query: {query}")
        ])
        
        self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(RetrieverState)
        
        workflow.add_node("analyze_context", self._analyze_with_context)
        workflow.add_node("custom_retrieve", self._custom_retrieve)
        workflow.add_node("web_retrieve", self._web_retrieve)
        workflow.add_node("combine", self._combine_results)
        workflow.add_node("update_memory", self._update_session_memory)
        
        workflow.set_entry_point("analyze_context")
        
        workflow.add_conditional_edges(
            "analyze_context",
            self._route_decision,
            {"custom": "custom_retrieve", "web": "web_retrieve", "both": "combine"}
        )
        
        workflow.add_edge("custom_retrieve", "combine")
        workflow.add_edge("web_retrieve", "combine")
        workflow.add_edge("combine", "update_memory")
        workflow.add_edge("update_memory", END)
        
        self.graph = workflow.compile(checkpointer=MemorySaver())

    def _analyze_with_context(self, state: RetrieverState) -> RetrieverState:
        query = state["query"]
        user_id = state.get("user_id", "default_user")
        
        conversation_history = self.session_memory.get_conversation_context(user_id)
        context_summary = self._summarize_conversation(conversation_history)
        
        chain = self.context_prompt | self.llm
        response = chain.invoke({
            "query": query,
            "conversation_history": context_summary
        })
        
        try:
            decision = json.loads(response.content)
            state["search_type"] = decision["strategy"]
            state["confidence"] = decision["confidence"]
            state["reasoning"] = decision["reasoning"]
            state["context_used"] = decision.get("context_used", False)
            state["conversation_history"] = conversation_history
        except json.JSONDecodeError:
            state["search_type"] = "custom"
            state["confidence"] = 0.5
            state["reasoning"] = "Default fallback to custom search"
            state["context_used"] = False
            state["conversation_history"] = []
        
        return state
    
    def _summarize_conversation(self, history: List[Dict]) -> str:
        if not history:
            return "No previous conversation."
        
        summary = "Recent conversation topics:\n"
        for i, msg in enumerate(history[:5], 1):
            summary += f"{i}. Query: {msg['query'][:100]}...\n"
            summary += f"   Strategy: {msg['strategy_used']}, Documents: {msg['document_count']}\n"
        
        return summary
    
    def _update_session_memory(self, state: RetrieverState) -> RetrieverState:
        user_id = state.get("user_id", "default_user")
        
        response_data = {
            "strategy_used": state["search_type"],
            "document_count": len(state["documents"]),
            "reasoning": state["reasoning"],
            "documents": state["documents"]
        }
        
        self.session_memory.add_message(user_id, state["query"], response_data)
        return state

    def _route_decision(self, state: RetrieverState) -> str:
        strategy = state["search_type"]
        confidence = state["confidence"]
        
        if confidence < 0.6:
            return "both"
        return strategy

    def _custom_retrieve(self, state: RetrieverState) -> RetrieverState:
        query = state["query"]
        documents = self.custom_retriever.get_relevant_documents(query)
        state["documents"] = documents
        return state

    def _web_retrieve(self, state: RetrieverState) -> RetrieverState:
        query = state["query"]
        documents = self.web_retriever.get_relevant_documents(query)
        state["documents"] = documents
        return state

    def _combine_results(self, state: RetrieverState) -> RetrieverState:
        if state["search_type"] == "both":
            custom_docs = self.custom_retriever.get_relevant_documents(state["query"])
            web_docs = self.web_retriever.get_relevant_documents(state["query"])
            
            combined_docs = custom_docs + web_docs
            state["documents"] = combined_docs[:self.config.max_docs]
        else:
            state["documents"] = state.get("documents", [])
        
        return state

    def retrieve(self, query: str, user_id: str = "default_user") -> Dict[str, Any]:
        initial_state = RetrieverState(
            query=query,
            user_id=user_id,
            documents=[],
            search_type="",
            confidence=0.0,
            reasoning="",
            context_used=False,
            conversation_history=[]
        )
        
        final_state = self.graph.invoke(initial_state, config={"configurable": {"thread_id": user_id}})
        
        return {
            "query": query,
            "user_id": user_id,
            "documents": final_state["documents"],
            "strategy_used": final_state["search_type"],
            "confidence": final_state["confidence"],
            "reasoning": final_state["reasoning"],
            "context_used": final_state.get("context_used", False),
            "document_count": len(final_state["documents"]),
            "conversation_length": len(final_state.get("conversation_history", []))
        }

    def async_retrieve(self, query: str, user_id: str = "default_user") -> Dict[str, Any]:
        async def _async_retrieve():
            initial_state = RetrieverState(
                query=query,
                user_id=user_id,
                documents=[],
                search_type="",
                confidence=0.0,
                reasoning="",
                context_used=False,
                conversation_history=[]
            )
            
            final_state = await self.graph.ainvoke(initial_state, config={"configurable": {"thread_id": user_id}})
            
            return {
                "query": query,
                "user_id": user_id,
                "documents": final_state["documents"],
                "strategy_used": final_state["search_type"],
                "confidence": final_state["confidence"],
                "reasoning": final_state["reasoning"],
                "context_used": final_state.get("context_used", False),
                "document_count": len(final_state["documents"]),
                "conversation_length": len(final_state.get("conversation_history", []))
            }
        
        return asyncio.run(_async_retrieve())
    
    def clear_user_session(self, user_id: str):
        self.session_memory.clear_session(user_id)
    
    def get_user_conversation(self, user_id: str) -> List[Dict]:
        return self.session_memory.get_conversation_context(user_id)


def create_retriever(gemini_api_key: str = None, config: RetrievalConfig = None) -> IntelligentRetriever:
    if gemini_api_key:
        os.environ["GOOGLE_API_KEY"] = "AIzaSyAS__dJxmaCNgQA0yTiPU_WoGyG3xaV4pQ"
    
    return IntelligentRetriever(config)


if __name__ == "__main__":
    retriever = create_retriever()
    
    test_queries = [
        "What is the latest news about AI?",
        "Tell me about the business continuity plan",
        "How does machine learning work?",
        "What are the company policies mentioned in our documents?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        result = retriever.retrieve(query)
        print(f"Strategy: {result['strategy_used']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Documents found: {result['document_count']}")
        
        if result['documents']:
            print("\nFirst document preview:")
            doc = result['documents'][0]
            print(f"Content: {doc.page_content[:200]}...")
            print(f"Source: {doc.metadata.get('source', 'unknown')}")
