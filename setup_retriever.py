import os
import subprocess
import sys

def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_retriever.txt"])
        print("Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def setup_environment():
    if not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY not found in environment variables.")
        api_key = input("Enter your Google API key (or press Enter to skip): ").strip()
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
            print("API key set for this session.")
        else:
            print("You'll need to set GOOGLE_API_KEY before using the retriever.")
    
    print("\nDatabase Setup Required:")
    print("1. Install PostgreSQL with pgvector extension")
    print("2. Create a database for vector storage")
    print("3. Update database credentials in example_usage.py")
    
    print("\nSetup complete!")
    print("You can now run: python example_usage.py")

if __name__ == "__main__":
    print("Setting up Intelligent Retriever...")
    
    if install_requirements():
        setup_environment()
    else:
        print("Setup failed. Please install requirements manually.")
