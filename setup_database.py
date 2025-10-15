import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

def create_database():
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': input("Enter PostgreSQL password: ").strip()
    }
    
    db_name = input("Enter database name (default: vector_db): ").strip() or "vector_db"
    
    try:
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"CREATE DATABASE {db_name};")
        print(f"Database '{db_name}' created successfully!")
        
        cursor.close()
        conn.close()
        
        db_config['database'] = db_name
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("pgvector extension installed successfully!")
        
        cursor.close()
        conn.close()
        
        print("\nDatabase setup complete!")
        print(f"Use these settings in your config:")
        print(f"  db_host: {db_config['host']}")
        print(f"  db_port: {db_config['port']}")
        print(f"  db_name: {db_config['database']}")
        print(f"  db_user: {db_config['user']}")
        print(f"  db_password: {db_config['password']}")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("PostgreSQL Database Setup for Vector Storage")
    print("=" * 50)
    print("Make sure PostgreSQL is installed and running.")
    print("You need the pgvector extension installed.")
    print()
    
    create_database()
