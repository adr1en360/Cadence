import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load env variables from .env
load_dotenv()

def test_db_connection():
    print("[*] Loading database configuration from .env...")
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("[ERROR] DATABASE_URL is missing in .env file.")
        return False

    print(f"[*] Connecting to database at {database_url.split('@')[-1]}...")
    try:
        # Create SQLAlchemy engine
        engine = create_engine(database_url)
        
        # Connect and execute a simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1;")).fetchone()
            if result and result[0] == 1:
                print("[OK] Database connection successful and SELECT 1 executed correctly!")
                return True
            else:
                print("[ERROR] Database connected, but test query returned unexpected result.")
                return False
    except Exception as e:
        print(f"[ERROR] Failed to connect to the database: {e}")
        return False

if __name__ == "__main__":
    success = test_db_connection()
    import sys
    sys.exit(0 if success else 1)
