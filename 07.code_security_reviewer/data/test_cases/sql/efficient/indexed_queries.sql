-- EFFICIENT: Proper Indexes
-- This SQL code uses indexes for optimal performance

-- EFFICIENT: Index on email column
CREATE INDEX idx_users_email ON users(email);
SELECT * FROM users WHERE email = 'user@example.com';

-- EFFICIENT: Composite index for multiple conditions
CREATE INDEX idx_orders_customer_status ON orders(customer_id, status);
SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending';

-- EFFICIENT: Indexes on join columns
CREATE INDEX idx_orders_user_id ON orders(user_id);
SELECT u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.email = 'user@example.com';

-- EFFICIENT: Index for ORDER BY
CREATE INDEX idx_products_name ON products(name);
SELECT * FROM products ORDER BY name;

-- EFFICIENT: Index on date column
CREATE INDEX idx_logs_created_at ON logs(created_at);
SELECT * FROM logs WHERE created_at > '2024-01-01';

