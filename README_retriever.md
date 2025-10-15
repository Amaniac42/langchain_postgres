# Intelligent Retriever with Gemini + PostgreSQL + Redis

A LangGraph-based intelligent retriever with session memory that automatically chooses between local document search and web search based on query analysis and conversation context.

## Features

- **Context-Aware Decision Making**: Uses Gemini AI with conversation history to make smarter retrieval decisions
- **PostgreSQL Vector Store**: Uses pgvector extension for efficient similarity search
- **Redis Session Memory**: Maintains conversation context with 30-minute TTL and 10-message stack
- **Dual Retrieval**: Local documents + web search capabilities
- **LangGraph Integration**: State-based workflow with conditional routing
- **Async Support**: Both sync and async retrieval methods
- **Docker Support**: Easy setup with Docker Compose

## Prerequisites

1. **Docker Desktop** (recommended) or **PostgreSQL with pgvector extension**
2. **Redis** (included in Docker setup)
3. **Google API Key** for Gemini
4. **Python 3.8+**

## Quick Start with Docker

1. **Start services:**
   ```bash
   python start_services.py start
   ```

2. **Install Python dependencies:**
   ```bash
   python setup_retriever.py
   ```

3. **Set your Google API key:**
   ```bash
   export GOOGLE_API_KEY="your_api_key_here"
   ```

4. **Run the demo:**
   ```bash
   python context_aware_example.py
   ```

## Manual Installation

1. Install PostgreSQL with pgvector extension and Redis
2. Run the setup script:
   ```bash
   python setup_retriever.py
   ```
3. Set up your database:
   ```bash
   python setup_database.py
   ```

## Configuration

### Docker Setup (Default)
The Docker setup uses these default credentials:
```python
config = RetrievalConfig(
    db_host="localhost",
    db_port=5432,
    db_name="vector_db",
    db_user="postgres",
    db_password="postgres123",
    table_name="documents",
    redis_url="redis://localhost:6379",
    session_ttl=1800,
    max_session_messages=10,
    max_docs=5,
    similarity_threshold=0.7,
    web_search_max_results=3
)
```

### Custom Configuration
Update credentials in your usage files if using different settings.

## Usage

### Basic Usage

```python
from intelligent_retriever import create_retriever, RetrievalConfig

config = RetrievalConfig(
    db_host="localhost",
    db_name="vector_db",
    db_user="postgres",
    db_password="postgres123",
    redis_url="redis://localhost:6379"
)

retriever = create_retriever(config=config)

# Retrieve with user context
result = retriever.retrieve("What is machine learning?", user_id="user123")

print(f"Strategy: {result['strategy_used']}")
print(f"Context Used: {result['context_used']}")
print(f"Documents: {result['documents']}")
```

### Interactive Usage

```bash
python example_usage.py
```

### Context-Aware Demo

```bash
python context_aware_example.py
```

### Database Exploration

```bash
python database_explorer.py
```

### Testing

```bash
python test_retriever.py
```

## How It Works

1. **Context Analysis**: Retrieves user's conversation history from Redis
2. **Query Analysis**: Gemini analyzes the query with conversation context to determine the best retrieval strategy
3. **Routing**: Based on confidence, routes to:
   - `custom`: Local document search using PostgreSQL vector store
   - `web`: DuckDuckGo web search
   - `both`: Combines both approaches
4. **Retrieval**: Executes the chosen strategy and returns results
5. **Memory Update**: Stores the interaction in Redis session memory
6. **Response**: Returns documents with metadata including strategy used, confidence, and context usage

## File Structure

- `intelligent_retriever.py` - Main implementation with Redis session memory
- `example_usage.py` - Interactive usage example
- `context_aware_example.py` - Context-aware demo with conversation simulation
- `database_explorer.py` - Command-line database exploration tool
- `test_retriever.py` - Test suite
- `setup_retriever.py` - Installation script
- `setup_database.py` - Database setup helper
- `start_services.py` - Docker services management
- `docker-compose.yml` - Docker configuration for PostgreSQL, Redis, pgAdmin, and RedisInsight
- `init.sql` - Database initialization script
- `database_ui_setup.md` - Database UI setup guide
- `requirements_retriever.txt` - Dependencies

## Environment Variables

- `GOOGLE_API_KEY` - Your Google API key for Gemini

## Database Schema

The retriever automatically creates this table:

```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding vector(768),
    source VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Decision Logic

The system considers these factors when choosing retrieval strategy:

### Query Analysis
- **Current/recent events** → web search
- **General knowledge** → web search  
- **Internal documents/specific topics** → custom search
- **Low confidence** → both strategies combined

### Context-Aware Features
- **Follow-up questions** → considers previous conversation topics
- **Ambiguous queries** → uses context to disambiguate
- **Related topics** → builds on previous search results
- **Session continuity** → maintains conversation flow

## Troubleshooting

### Docker Issues
1. **Services not starting**: Run `docker-compose logs` to check error messages
2. **Connection refused**: Wait a few seconds for services to fully start
3. **Port conflicts**: Change ports in `docker-compose.yml` if needed

### Database Issues
1. **Connection errors**: Check PostgreSQL is running and credentials are correct
2. **pgvector issues**: Make sure pgvector extension is installed (included in Docker setup)
3. **Document loading**: Ensure documents are in supported formats (PDF, TXT, DOCX)

### API Issues
1. **API key issues**: Ensure GOOGLE_API_KEY is set correctly
2. **Rate limiting**: Check your Google API quota and limits

### Redis Issues
1. **Memory errors**: Redis is configured with 256MB limit and LRU eviction
2. **Session not persisting**: Check Redis connection and TTL settings

### Service Management
```bash
# Start services
python start_services.py start

# Stop services
python start_services.py stop

# View logs
python start_services.py logs
```
