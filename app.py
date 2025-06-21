from alchemist_core import app, init_db, DATABASE
import sqlite3

def init_app():
    # Initialize the database
    init_db()
    
    # Verify the database is accessible
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\nDatabase initialized successfully!")
        print("Available tables:")
        for table in tables:
            print(f"- {table[0]}")
        conn.close()
    except sqlite3.Error as e:
        print(f"\nError initializing database: {e}")
        return False
    return True

# Initialize the app
if __name__ == "__main__":
    if init_app():
        print("\nStarting Flask web server...")
        print("Open your web browser and go to: http://127.0.0.1:5000/")
        app.run(debug=True, use_reloader=False)
    else:
        print("\nFailed to initialize the application. Please check the database configuration.")
