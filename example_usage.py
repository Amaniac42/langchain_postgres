import os
from dotenv import load_dotenv
from intelligent_retriever import create_retriever, RetrievalConfig

# Load environment variables from .env file
load_dotenv()

def main():
    gemini_api_key = os.getenv("GOOGLE_API_KEY")
    if not gemini_api_key:
        print("Please set GOOGLE_API_KEY environment variable")
        return
    
    config = RetrievalConfig(
        db_host="localhost",
        db_port=5432,
        db_name="vector_db",
        db_user="postgres",
        db_password="postgres123",
        table_name="documents",
        redis_url="redis://localhost:6379",
        max_docs=5,
        similarity_threshold=0.7,
        web_search_max_results=3
    )
    
    retriever = create_retriever(gemini_api_key, config)
    
    user_id = input("Enter your user ID (or press Enter for 'default_user'): ").strip() or "default_user"
    
    while True:
        query = input(f"\n[{user_id}] Enter your query (or 'quit' to exit): ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        print("\nSearching...")
        result = retriever.retrieve(query, user_id)
        
        print(f"\nStrategy Used: {result['strategy_used']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Context Used: {result['context_used']}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Found {result['document_count']} documents")
        print(f"Conversation length: {result['conversation_length']} messages")
        
        if result['documents']:
            print("\nResults:")
            for i, doc in enumerate(result['documents'][:3], 1):
                print(f"\n{i}. Source: {doc.metadata.get('source', 'Unknown')}")
                print(f"Content: {doc.page_content[:300]}...")
                if len(doc.page_content) > 300:
                    print("...")
        else:
            print("No relevant documents found.")

if __name__ == "__main__":
    main()
