-- SECURE: Parameterized Queries
-- This SQL code uses parameterized queries to prevent SQL injection

-- SECURE: Use parameterized queries
-- In application code, this would be:
-- query = "SELECT * FROM users WHERE id = ?"
-- cursor.execute(query, (user_id,))
SELECT * FROM users WHERE id = ?;

-- SECURE: Parameterized query with user input
SELECT * FROM users WHERE email = ?;

-- SECURE: Parameterized LIKE query
SELECT * FROM products WHERE name LIKE ?;

-- SECURE: Multiple parameters
SELECT * FROM users WHERE email = ? AND status = ?;

-- SECURE: Stored procedures (also safe)
CREATE PROCEDURE GetUser(@user_id INT)
AS
BEGIN
    SELECT * FROM users WHERE id = @user_id;
END;

