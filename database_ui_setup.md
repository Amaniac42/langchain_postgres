# Database UI Setup Guide

## 🖥️ **Available Database UIs**

After running `python start_services.py start`, you'll have access to two powerful database management interfaces:

### **1. pgAdmin (PostgreSQL UI)**
- **URL**: http://localhost:8080
- **Email**: admin@vector.com
- **Password**: admin123

#### **Connecting to PostgreSQL:**
1. Open pgAdmin at http://localhost:8080
2. Login with the credentials above
3. Right-click "Servers" → "Create" → "Server"
4. **General Tab**:
   - Name: `Vector Database`
5. **Connection Tab**:
   - Host: `postgres` (Docker service name)
   - Port: `5432`
   - Database: `vector_db`
   - Username: `postgres`
   - Password: `postgres123`

#### **What You Can View:**
- **Documents Table**: All your PDFs/text files with embeddings
- **Vector Data**: 768-dimensional embedding vectors
- **Metadata**: Source files, timestamps, similarity scores
- **Query Performance**: Execution plans and statistics

### **2. RedisInsight (Redis UI)**
- **URL**: http://localhost:8002

#### **Connecting to Redis:**
1. Open RedisInsight at http://localhost:8002
2. Click "Add Redis Database"
3. **Connection Details**:
   - Host: `redis` (Docker service name)
   - Port: `6379`
   - Name: `Vector Redis`

#### **What You Can View:**
- **Session Keys**: `session:user123` format
- **Conversation Data**: JSON conversation history
- **Memory Usage**: Redis memory consumption
- **Real-time Activity**: Live monitoring of operations

## 🔍 **Exploring Your Data**

### **PostgreSQL Queries**

```sql
-- View all documents
SELECT id, source, LEFT(content, 100) as preview, created_at 
FROM documents 
ORDER BY created_at DESC;

-- Check embedding dimensions
SELECT id, array_length(embedding, 1) as embedding_dim 
FROM documents 
LIMIT 5;

-- Find similar documents
SELECT id, source, content, 
       1 - (embedding <=> (SELECT embedding FROM documents WHERE id = 1)) as similarity
FROM documents 
ORDER BY embedding <=> (SELECT embedding FROM documents WHERE id = 1)
LIMIT 5;
```

### **Redis Commands**

```bash
# List all session keys
KEYS session:*

# View conversation history for a user
GET session:user123

# Check Redis memory usage
INFO memory

# Monitor real-time operations
MONITOR
```

## 📊 **Data Structure Overview**

### **PostgreSQL Tables**
```sql
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,           -- Document text content
    metadata JSONB,                  -- Additional metadata
    embedding vector(768),           -- Gemini embedding vector
    source VARCHAR(255),             -- Source file name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Redis Data Structure**
```json
{
  "session:user123": [
    {
      "timestamp": "2024-01-15T10:30:00",
      "query": "What is machine learning?",
      "strategy_used": "web",
      "document_count": 3,
      "reasoning": "General knowledge question",
      "key_points": ["From web_search: Machine learning is..."]
    }
  ]
}
```

## 🚀 **Quick Start**

1. **Start all services:**
   ```bash
   python start_services.py start
   ```

2. **Wait for services to be ready** (about 30 seconds)

3. **Access the UIs:**
   - pgAdmin: http://localhost:8080
   - RedisInsight: http://localhost:8002

4. **Connect to databases** using the credentials above

## 🔧 **Troubleshooting**

### **pgAdmin Issues:**
- **Can't connect**: Ensure PostgreSQL container is healthy
- **Login fails**: Check email/password are correct
- **Connection refused**: Wait for PostgreSQL to fully start

### **RedisInsight Issues:**
- **Page not loading**: Wait for RedisInsight to start (may take 1-2 minutes)
- **Can't connect to Redis**: Check Redis container is healthy
- **No data visible**: Run some queries first to generate session data

### **Service Health Checks:**
```bash
# Check all services
docker-compose ps

# View service logs
python start_services.py logs

# Restart specific service
docker-compose restart pgadmin
docker-compose restart redisinsight
```

## 📈 **Monitoring & Analytics**

### **PostgreSQL Monitoring:**
- Query execution times
- Database size and growth
- Index usage statistics
- Vector similarity performance

### **Redis Monitoring:**
- Memory usage and trends
- Key expiration patterns
- Session activity levels
- Connection statistics

Both UIs provide real-time monitoring and historical analytics for your vector database and session management system!
