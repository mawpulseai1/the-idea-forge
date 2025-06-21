import sqlite3


def init_db():
    DATABASE = 'alchemist_sessions.db'
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        # Create users table first
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Create sessions table with user_id as a foreign key
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                input_text TEXT NOT NULL,
                key_terms TEXT NOT NULL,
                prompts TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # Create index for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
        ''')

        conn.commit()
    print(f"SQLite database '{DATABASE}' initialized with users and sessions tables.")


if __name__ == "__main__":
    init_db()