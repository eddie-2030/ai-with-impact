# INSECURE: SQL Injection Vulnerability
# This code is vulnerable to SQL injection attacks

def get_user(user_id):
    """INSECURE: Uses string formatting in SQL query - vulnerable to SQL injection"""
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # VULNERABLE: Direct string interpolation
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def search_users(username):
    """INSECURE: User input directly in SQL query"""
    import sqlite3
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # VULNERABLE: String concatenation with user input
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()

