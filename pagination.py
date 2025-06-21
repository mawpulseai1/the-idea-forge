import sqlite3
from datetime import datetime

def get_all_sessions_paginated(user_id, page=1, per_page=10):
    """
    Get paginated sessions for a user.
    
    Args:
        user_id (int): The ID of the user
        page (int): The page number (1-based)
        per_page (int): Number of items per page
        
    Returns:
        dict: Dictionary containing paginated sessions and pagination info
    """
    conn = sqlite3.connect('database.db')  # Update with your DATABASE variable
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get total count for pagination
    cursor.execute('SELECT COUNT(*) as count FROM sessions WHERE user_id = ?', (user_id,))
    total_sessions = cursor.fetchone()['count']
    total_pages = (total_sessions + per_page - 1) // per_page if total_sessions > 0 else 1
    
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get paginated sessions
    cursor.execute('''
        SELECT id, input_text, timestamp 
        FROM sessions 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    ''', (user_id, per_page, offset))
    
    sessions = cursor.fetchall()
    conn.close()
    
    sessions_list = [
        {'id': s['id'], 'input_text': s['input_text'],
         'timestamp': datetime.strptime(s['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')}
        for s in sessions
    ]
    
    return {
        'items': sessions_list,
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'total_items': total_sessions
        }
    }
