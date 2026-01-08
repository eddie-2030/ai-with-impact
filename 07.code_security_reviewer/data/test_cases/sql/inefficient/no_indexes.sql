-- INEFFICIENT: Missing Indexes
-- This SQL code lacks proper indexes, causing slow queries

-- INEFFICIENT: Full table scan on large table
-- No index on email column
SELECT * FROM users WHERE email = 'user@example.com';

-- INEFFICIENT: Multiple full table scans
SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending';

-- INEFFICIENT: Join without indexes
SELECT u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.email = 'user@example.com';

-- INEFFICIENT: ORDER BY without index
SELECT * FROM products ORDER BY name;

-- INEFFICIENT: WHERE clause on non-indexed column
SELECT * FROM logs WHERE created_at > '2024-01-01';

