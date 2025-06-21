import sqlite3
from alchemist_core import DATABASE, init_db

def main():
    print("Initializing database...")
    init_db()
    
    # Verify tables were created
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("\nTables in database:")
    for table in tables:
        print(f"- {table[0]}")
    
    # Show schema for each table
    for table in tables:
        print(f"\nSchema for {table[0]}:")
        cursor.execute(f"PRAGMA table_info({table[0]})")
        for column in cursor.fetchall():
            print(f"  {column[1]}: {column[2]}")
    
    conn.close()
    print("\nDatabase initialization complete!")

if __name__ == "__main__":
    main()
