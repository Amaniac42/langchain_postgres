import os
import time
from dotenv import load_dotenv
from intelligent_retriever import create_retriever, RetrievalConfig

# Load environment variables from .env file
load_dotenv()

def simulate_conversation():
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
        session_ttl=1800,
        max_session_messages=10
    )
    
    retriever = create_retriever(gemini_api_key, config)
    
    user_id = "demo_user_123"
    
    print("🧠 Context-Aware Intelligent Retriever Demo")
    print("=" * 60)
    print("This demo shows how the retriever uses conversation context")
    print("to make smarter decisions about retrieval strategy.\n")
    
    conversation_flow = [
        {
            "query": "What is machine learning?",
            "description": "Initial query - should use web search for general knowledge"
        },
        {
            "query": "How does it differ from deep learning?",
            "description": "Follow-up question - should consider previous context"
        },
        {
            "query": "Can you find any internal documents about AI policies?",
            "description": "Specific internal query - should use custom search"
        },
        {
            "query": "What are the latest developments in that field?",
            "description": "Ambiguous follow-up - should use context to determine meaning"
        },
        {
            "query": "Tell me about our business continuity plan",
            "description": "Internal document query - should use custom search"
        }
    ]
    
    for i, turn in enumerate(conversation_flow, 1):
        print(f"\n🗣️  Turn {i}: {turn['description']}")
        print(f"Query: '{turn['query']}'")
        print("-" * 50)
        
        result = retriever.retrieve(turn['query'], user_id)
        
        print(f" Strategy Used: {result['strategy_used']}")
        print(f" Confidence: {result['confidence']:.2f}")
        print(f" Context Used: {result['context_used']}")
        print(f" Documents Found: {result['document_count']}")
        print(f" Reasoning: {result['reasoning']}")
        print(f" Conversation Length: {result['conversation_length']} messages")
        
        if result['documents']:
            print(f"\n Sample Result:")
            sample_doc = result['documents'][0]
            print(f"   Source: {sample_doc.metadata.get('source', 'unknown')}")
            print(f"   Content: {sample_doc.page_content[:150]}...")
        
        print("\n" + "⏱️  Processing next query in 3 seconds...")
        time.sleep(3)
    
    print(f"\n🎉 Conversation Complete!")
    print(f"📊 Final conversation history:")
    
    conversation_history = retriever.get_user_conversation(user_id)
    for j, msg in enumerate(conversation_history, 1):
        print(f"   {j}. {msg['query'][:60]}... → {msg['strategy_used']}")

def interactive_mode():
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
        redis_url="redis://localhost:6379"
    )
    
    retriever = create_retriever(gemini_api_key, config)
    
    print("🎯 Interactive Context-Aware Retriever")
    print("=" * 50)
    print("Commands:")
    print("  /clear - Clear your conversation history")
    print("  /history - Show conversation history")
    print("  /quit - Exit the program")
    print()
    
    user_id = input("Enter your user ID (or press Enter for 'demo_user'): ").strip() or "demo_user"
    
    while True:
        query = input(f"\n[{user_id}] Enter your query: ").strip()
        
        if query.lower() in ['/quit', '/exit', 'quit', 'exit']:
            break
        elif query.lower() == '/clear':
            retriever.clear_user_session(user_id)
            print("✅ Conversation history cleared!")
            continue
        elif query.lower() == '/history':
            history = retriever.get_user_conversation(user_id)
            if history:
                print(f"\n📚 Conversation History ({len(history)} messages):")
                for i, msg in enumerate(history, 1):
                    print(f"   {i}. {msg['query'][:80]}...")
                    print(f"      Strategy: {msg['strategy_used']}, Docs: {msg['document_count']}")
            else:
                print("📭 No conversation history found.")
            continue
        elif not query:
            continue
        
        print("\n🔍 Searching...")
        result = retriever.retrieve(query, user_id)
        
        print(f"\n✅ Results:")
        print(f"   Strategy: {result['strategy_used']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Context Used: {result['context_used']}")
        print(f"   Documents: {result['document_count']}")
        print(f"   Reasoning: {result['reasoning']}")
        
        if result['documents']:
            print(f"\n📄 Top Result:")
            doc = result['documents'][0]
            print(f"   Source: {doc.metadata.get('source', 'unknown')}")
            print(f"   Content: {doc.page_content[:200]}...")

if __name__ == "__main__":
    print("Choose mode:")
    print("1. Simulated conversation demo")
    print("2. Interactive mode")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        simulate_conversation()
    elif choice == "2":
        interactive_mode()
    else:
        print("Invalid choice. Running demo...")
        simulate_conversation()
