import subprocess
import time
import sys
import os

def check_docker():
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is installed")
            return True
        else:
            print("❌ Docker is not installed or not running")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False

def start_services():
    if not check_docker():
        print("\nPlease install Docker Desktop and try again.")
        sys.exit(1)
    
    print("\n🚀 Starting PostgreSQL and Redis services...")
    
    try:
        subprocess.run(['docker-compose', 'up', '-d'], check=True)
        print("✅ Services started successfully!")
        
        print("\n⏳ Waiting for services to be ready...")
        time.sleep(10)
        
        print("\n🔍 Checking service status...")
        result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
        print(result.stdout)
        
        print("\n📋 Service Information:")
        print("   PostgreSQL: localhost:5432")
        print("   Redis: localhost:6379")
        print("   Database: vector_db")
        print("   User: postgres")
        print("   Password: postgres123")
        
        print("\n🖥️  Database UIs Available:")
        print("   pgAdmin (PostgreSQL): http://localhost:8080")
        print("     Email: admin@vector.com")
        print("     Password: admin123")
        print("   RedisInsight (Redis): http://localhost:8002")
        
        print("\n✅ Setup complete! You can now run:")
        print("   python example_usage.py")
        print("   python context_aware_example.py")
        print("   See database_ui_setup.md for UI access details")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting services: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping services...")
        subprocess.run(['docker-compose', 'down'])
        sys.exit(0)

def stop_services():
    print("🛑 Stopping services...")
    try:
        subprocess.run(['docker-compose', 'down'], check=True)
        print("✅ Services stopped successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error stopping services: {e}")

def show_logs():
    print("📋 Service logs:")
    try:
        subprocess.run(['docker-compose', 'logs', '--tail=50'])
    except subprocess.CalledProcessError as e:
        print(f"❌ Error showing logs: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "start":
            start_services()
        elif command == "stop":
            stop_services()
        elif command == "logs":
            show_logs()
        else:
            print("Usage: python start_services.py [start|stop|logs]")
    else:
        start_services()
