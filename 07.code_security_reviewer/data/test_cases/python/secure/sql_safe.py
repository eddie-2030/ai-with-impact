# SECURE: SQL Injection Prevention
# This code uses parameterized queries to prevent SQL injection

def get_user(user_id):
    """SECURE: Uses parameterized queries to prevent SQL injection"""
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # SECURE: Parameterized query
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()

def search_users(username):
    """SECURE: Parameterized query with user input"""
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # SECURE: Parameterized query prevents injection
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()

