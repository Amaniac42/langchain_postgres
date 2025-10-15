import os
import asyncio
from intelligent_retriever import create_retriever, RetrievalConfig

async def test_retriever():
    if not os.getenv("GOOGLE_API_KEY"):
        print("Skipping test - GOOGLE_API_KEY not set")
        return
    
    config = RetrievalConfig(
        db_host="localhost",
        db_port=5432,
        db_name="test_vector_db",
        db_user="postgres",
        db_password="your_password",
        table_name="test_documents",
        max_docs=3,
        web_search_max_results=2
    )
    
    retriever = create_retriever(config=config)
    
    test_cases = [
        {
            "query": "What is artificial intelligence?",
            "expected_strategy": "web",
            "description": "General knowledge question"
        },
        {
            "query": "Tell me about our business continuity plan",
            "expected_strategy": "custom", 
            "description": "Internal document question"
        },
        {
            "query": "Latest news about ChatGPT",
            "expected_strategy": "web",
            "description": "Current events question"
        },
        {
            "query": "Company policies and procedures",
            "expected_strategy": "custom",
            "description": "Internal knowledge question"
        }
    ]
    
    print("Testing Intelligent Retriever...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Query: {test_case['query']}")
        
        result = retriever.retrieve(test_case['query'])
        
        print(f"Strategy: {result['strategy_used']} (expected: {test_case['expected_strategy']})")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Documents: {result['document_count']}")
        
        strategy_match = result['strategy_used'] == test_case['expected_strategy']
        print(f"Strategy Match: {'✓' if strategy_match else '✗'}")
        
        if result['documents']:
            print("Sample content:")
            sample_doc = result['documents'][0]
            print(f"  {sample_doc.page_content[:100]}...")
    
    print("\n" + "=" * 60)
    print("Testing async functionality...")
    
    async_result = retriever.async_retrieve("What is machine learning?")
    print(f"Async result strategy: {async_result['strategy_used']}")
    print(f"Async documents found: {async_result['document_count']}")

if __name__ == "__main__":
    asyncio.run(test_retriever())
