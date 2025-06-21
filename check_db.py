import sqlite3

def check_database():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('alchemist_sessions.db')
        cursor = conn.cursor()
        
        # Get the list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("\nTables in the database:")
        for table in tables:
            print(f"- {table[0]}")
        
        # Check if 'sessions' table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions';")
        if not cursor.fetchone():
            print("\nERROR: 'sessions' table does not exist!")
            print("\nCreating the 'sessions' table...")
            
            # Create the sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    input_text TEXT NOT NULL,
                    key_terms TEXT,
                    prompts TEXT,
                    graph_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Create index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
            ''')
            
            conn.commit()
            print("'sessions' table created successfully!")
        else:
            print("\n'sessions' table exists.")
        
        # Show schema of sessions table
        print("\nSchema of 'sessions' table:")
        cursor.execute("PRAGMA table_info(sessions)")
        for column in cursor.fetchall():
            print(f"  {column[1]}: {column[2]}")
        
        # Check if 'users' table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cursor.fetchone():
            print("\nERROR: 'users' table does not exist!")
            print("\nCreating the 'users' table...")
            
            # Create the users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            print("'users' table created successfully!")
        else:
            print("\n'users' table exists.")
        
        # Show schema of users table
        print("\nSchema of 'users' table:")
        cursor.execute("PRAGMA table_info(users)")
        for column in cursor.fetchall():
            print(f"  {column[1]}: {column[2]}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database()
