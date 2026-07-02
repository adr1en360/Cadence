import os
import sys
import subprocess
from sqlalchemy import create_engine, MetaData

# Add root folder to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def reset_database():
    print("=" * 60)
    print("      CADENCE ENGINE: DATABASE RESET UTILITY (FRESH START)")
    print("=" * 60)
    
    db_url = settings.DATABASE_URL
    print(f"Database URL: {db_url}")
    
    try:
        engine = create_engine(db_url)
        metadata = MetaData()
        print("Connecting to database...")
        metadata.reflect(bind=engine)
        
        table_names = list(metadata.tables.keys())
        if table_names:
            print(f"Found existing tables: {', '.join(table_names)}")
            print("Dropping all tables in dependency order...")
            metadata.drop_all(bind=engine)
            print("All tables dropped successfully.")
        else:
            print("Database is already empty (no tables found).")
            
        print("Recreating database tables using Alembic migrations...")
        result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode == 0:
            print("Migrations applied successfully! Tables recreated.")
            print("Database has been reset successfully and is ready for clean testing.")
        else:
            print("Failed to run migrations:")
            print(result.stderr or result.stdout)
            
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        print("\nMake sure your PostgreSQL Docker container is running:")
        print("  docker start cadence-db")
    print("=" * 60)

if __name__ == "__main__":
    reset_database()
