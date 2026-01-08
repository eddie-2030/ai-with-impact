-- INSECURE: SQL Injection Vulnerability
-- This SQL code is vulnerable to SQL injection attacks

-- VULNERABLE: Direct string concatenation
-- DO NOT USE: This allows SQL injection
SELECT * FROM users WHERE username = 'admin' OR '1'='1';

-- VULNERABLE: Dynamic SQL construction
-- In application code, this would be:
-- query = "SELECT * FROM users WHERE id = " + user_id;
-- This allows injection like: user_id = "1 OR 1=1"

-- VULNERABLE: User input directly in query
SELECT * FROM users WHERE email = 'user@example.com' OR '1'='1';

-- VULNERABLE: No input validation
SELECT * FROM products WHERE name LIKE '%' + user_input + '%';

