import os
import psycopg  # Using psycopg 3
from langchain_huggingface import HuggingFaceEmbeddings  # CHANGED
from langchain_core.documents import Document
from langchain_postgres.vectorstores import PGVector

# --- 1. Configuration ---
# We are using the NEW, clean database settings.
# export POSTGRES_CONNECTION_STRING="postgresql://test_user:test_pass@localhost:5433/vectordb"

# Get connection string from environment variables
CONNECTION_STRING = os.getenv("POSTGRES_CONNECTION_STRING")
if not CONNECTION_STRING:
    raise ValueError("POSTGRES_CONNECTION_STRING environment variable not set. Please run: $env:POSTGRES_CONNECTION_STRING = \"...\"")

# --- 2. Enable the pgvector extension ---
try:
    with psycopg.connect(CONNECTION_STRING) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
    print("pgvector extension enabled successfully.")
except Exception as e:
    print(f"Error connecting to database or enabling pgvector: {e}")
    print("Please ensure your Docker container is running and the connection string is correct.")
    exit(1)

# --- 3. Initialize Langchain Components ---
print("Loading local embedding model... (This may take a moment on first run)")

# The name for your collection (will be used to create a table)
COLLECTION_NAME = "my_local_model_collection"

# Initialize the embedding model (CHANGED to a local Hugging Face model)
# This requires no API key. It runs 100% on your machine.
# The first time this runs, it will download the model (about 90MB).
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
print("Local model loaded successfully.")

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

# This command creates the embeddings (locally) and stores them in Postgres.
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
