import psycopg2
import redis
import json
import pandas as pd
from typing import List, Dict, Any
import os

class DatabaseExplorer:
    def __init__(self, config=None):
        self.config = config or {
            'db_host': 'localhost',
            'db_port': 5432,
            'db_name': 'vector_db',
            'db_user': 'postgres',
            'db_password': 'postgres123',
            'redis_url': 'redis://localhost:6379'
        }
        self.postgres_conn = None
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        try:
            self.postgres_conn = psycopg2.connect(
                host=self.config['db_host'],
                port=self.config['db_port'],
                database=self.config['db_name'],
                user=self.config['db_user'],
                password=self.config['db_password']
            )
            print("✅ Connected to PostgreSQL")
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
        
        try:
            self.redis_client = redis.from_url(self.config['redis_url'], decode_responses=True)
            self.redis_client.ping()
            print("✅ Connected to Redis")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
    
    def get_documents_summary(self) -> pd.DataFrame:
        """Get summary of all documents in PostgreSQL"""
        if not self.postgres_conn:
            return pd.DataFrame()
        
        query = """
        SELECT 
            id,
            source,
            LEFT(content, 100) as content_preview,
            LENGTH(content) as content_length,
            array_length(embedding, 1) as embedding_dim,
            created_at,
            metadata
        FROM documents 
        ORDER BY created_at DESC
        """
        
        try:
            df = pd.read_sql(query, self.postgres_conn)
            return df
        except Exception as e:
            print(f"Error fetching documents: {e}")
            return pd.DataFrame()
    
    def get_similar_documents(self, doc_id: int, limit: int = 5) -> pd.DataFrame:
        """Find documents similar to a given document"""
        if not self.postgres_conn:
            return pd.DataFrame()
        
        query = """
        SELECT 
            d2.id,
            d2.source,
            LEFT(d2.content, 100) as content_preview,
            1 - (d2.embedding <=> d1.embedding) as similarity
        FROM documents d1
        CROSS JOIN documents d2
        WHERE d1.id = %s AND d2.id != %s
        ORDER BY d2.embedding <=> d1.embedding
        LIMIT %s
        """
        
        try:
            df = pd.read_sql(query, self.postgres_conn, params=[doc_id, doc_id, limit])
            return df
        except Exception as e:
            print(f"Error finding similar documents: {e}")
            return pd.DataFrame()
    
    def get_redis_sessions(self) -> List[Dict]:
        """Get all user sessions from Redis"""
        if not self.redis_client:
            return []
        
        try:
            session_keys = self.redis_client.keys("session:*")
            sessions = []
            
            for key in session_keys:
                user_id = key.replace("session:", "")
                conversation = self.redis_client.lrange(key, 0, -1)
                
                session_data = {
                    'user_id': user_id,
                    'message_count': len(conversation),
                    'conversations': [json.loads(msg) for msg in conversation]
                }
                sessions.append(session_data)
            
            return sessions
        except Exception as e:
            print(f"Error fetching Redis sessions: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {
            'postgresql': {},
            'redis': {}
        }
        
        if self.postgres_conn:
            try:
                cursor = self.postgres_conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM documents")
                stats['postgresql']['total_documents'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT AVG(array_length(embedding, 1)) FROM documents")
                stats['postgresql']['avg_embedding_dim'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT source) FROM documents")
                stats['postgresql']['unique_sources'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                stats['postgresql']['database_size'] = cursor.fetchone()[0]
                
                cursor.close()
            except Exception as e:
                stats['postgresql']['error'] = str(e)
        
        if self.redis_client:
            try:
                stats['redis']['total_keys'] = len(self.redis_client.keys("*"))
                stats['redis']['session_keys'] = len(self.redis_client.keys("session:*"))
                stats['redis']['memory_usage'] = self.redis_client.info('memory')['used_memory_human']
                stats['redis']['connected_clients'] = self.redis_client.info('clients')['connected_clients']
            except Exception as e:
                stats['redis']['error'] = str(e)
        
        return stats
    
    def search_documents(self, search_term: str, limit: int = 10) -> pd.DataFrame:
        """Search documents by content"""
        if not self.postgres_conn:
            return pd.DataFrame()
        
        query = """
        SELECT 
            id,
            source,
            LEFT(content, 200) as content_preview,
            ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) as rank
        FROM documents 
        WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
        ORDER BY rank DESC
        LIMIT %s
        """
        
        try:
            df = pd.read_sql(query, self.postgres_conn, params=[search_term, search_term, limit])
            return df
        except Exception as e:
            print(f"Error searching documents: {e}")
            return pd.DataFrame()
    
    def export_data(self, output_dir: str = "./exports"):
        """Export data to CSV files"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        print("📊 Exporting data...")
        
        # Export documents
        docs_df = self.get_documents_summary()
        if not docs_df.empty:
            docs_df.to_csv(f"{output_dir}/documents.csv", index=False)
            print(f"✅ Exported {len(docs_df)} documents to {output_dir}/documents.csv")
        
        # Export sessions
        sessions = self.get_redis_sessions()
        if sessions:
            sessions_df = pd.json_normalize(sessions, record_path='conversations', meta='user_id')
            sessions_df.to_csv(f"{output_dir}/conversations.csv", index=False)
            print(f"✅ Exported {len(sessions)} sessions to {output_dir}/conversations.csv")
        
        # Export stats
        stats = self.get_database_stats()
        with open(f"{output_dir}/database_stats.json", 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        print(f"✅ Exported database stats to {output_dir}/database_stats.json")

def main():
    explorer = DatabaseExplorer()
    
    print("🔍 Vector Database Explorer")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. View documents summary")
        print("2. Find similar documents")
        print("3. View Redis sessions")
        print("4. Database statistics")
        print("5. Search documents")
        print("6. Export data")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == "1":
            df = explorer.get_documents_summary()
            if not df.empty:
                print(f"\n📚 Documents Summary ({len(df)} total):")
                print(df.to_string(index=False))
            else:
                print("❌ No documents found or connection error")
        
        elif choice == "2":
            doc_id = input("Enter document ID: ").strip()
            try:
                doc_id = int(doc_id)
                df = explorer.get_similar_documents(doc_id)
                if not df.empty:
                    print(f"\n🔍 Similar Documents to ID {doc_id}:")
                    print(df.to_string(index=False))
                else:
                    print("❌ No similar documents found")
            except ValueError:
                print("❌ Invalid document ID")
        
        elif choice == "3":
            sessions = explorer.get_redis_sessions()
            if sessions:
                print(f"\n💬 Redis Sessions ({len(sessions)} users):")
                for session in sessions:
                    print(f"  User: {session['user_id']}")
                    print(f"  Messages: {session['message_count']}")
                    if session['conversations']:
                        latest = session['conversations'][0]
                        print(f"  Latest: {latest['query'][:60]}...")
                    print()
            else:
                print("❌ No sessions found or connection error")
        
        elif choice == "4":
            stats = explorer.get_database_stats()
            print("\n📊 Database Statistics:")
            print(json.dumps(stats, indent=2, default=str))
        
        elif choice == "5":
            search_term = input("Enter search term: ").strip()
            if search_term:
                df = explorer.search_documents(search_term)
                if not df.empty:
                    print(f"\n🔍 Search Results for '{search_term}':")
                    print(df.to_string(index=False))
                else:
                    print("❌ No results found")
        
        elif choice == "6":
            output_dir = input("Output directory (default: ./exports): ").strip() or "./exports"
            explorer.export_data(output_dir)
        
        elif choice == "7":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
