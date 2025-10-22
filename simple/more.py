import os
import psycopg  # Using psycopg 3
from langchain_google_genai import GoogleGenerativeAIEmbeddings # CHANGED
from langchain_core.documents import Document
from langchain_postgres.vectorstores import PGVector

# --- 1. Configuration ---
# IMPORTANT: Set these environment variables before running the script.
#
# FOR GEMINI:
# export GOOGLE_API_KEY="AIzaSyAS__dJxmaCNgQA0yTiPU_WoGyG3xaV4pQ"
#
# FOR POSTGRES (from docker-compose.yml):
# export POSTGRES_CONNECTION_STRING="postgresql://myuser:mypassword@localhost:5432/vectordb"

# Get connection string from environment variables
CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")
if not CONNECTION_STRING:
    raise ValueError("POSTGRES_CONNECTION_STRING environment variable not set.")

# Get Google API Key
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

# --- 2. Enable the pgvector extension ---
# This is a one-time setup step for your database.
try:
    with psycopg.connect(CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
    print("pgvector extension enabled successfully.")
except Exception as e:
    print(f"Error enabling pgvector extension: {e}")
    print("Please ensure your database is running and the connection string is correct.")
    exit(1)

# --- 3. Initialize Langchain Components ---

# The name for your collection (will be used to create a table)
COLLECTION_NAME = "my_gemini_collection"

# Initialize the embedding model (CHANGED to Google Generative AI)
# We're using "models/embedding-001", the recommended model.
embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
print("Using Google Generative AI embeddings model.")

# Initialize the PGVector store
store = PGVector(
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    connection=CONNECTION_STRING,
    use_jsonb=True, 
)

# --- 4. Add Documents to the Vector Store ---
print("Adding documents to the vector store...")

documents = [
    Document(
        page_content="The cat sat on the mat.",
        metadata={"source": "proverbs.txt", "chapter": 1}
    ),
    Document(
        page_content="A lazy dog slept in the sun.",
        metadata={"source": "fables.txt", "chapter": 4}
    ),
    Document(
        page_content="A quick brown fox jumps over the lazy dog.",
        metadata={"source": "fables.txt", "chapter": 2}
    ),
]

# This command creates the embeddings (using Gemini) and stores them.
store.add_documents(documents)

print(f"Successfully added {len(documents)} documents to the '{COLLECTION_NAME}' collection.")

# --- 5. Test the Connection with a Similarity Search (in Python) ---
query = "Which animal was sleepy?"

# Perform a similarity search
similar_docs = store.similarity_search(query, k=1)

print("\n--- Test Query ---")
print(f"Query: '{query}'")
if similar_docs:
    print(f"Most Similar Document: '{similar_docs[0].page_content}'")
    print(f"Metadata: {similar_docs[0].metadata}")
else:
    print("No similar documents found.")
