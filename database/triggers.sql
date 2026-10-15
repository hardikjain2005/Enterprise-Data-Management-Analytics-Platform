-- =====================================================================
-- File: triggers.sql
-- Purpose: Triggers = SQL that MySQL runs AUTOMATICALLY when a row is
--          inserted, updated or deleted. Nobody calls them directly.
--
--   BEFORE trigger -> can inspect / change NEW values or reject the row
--   AFTER  trigger -> row is already saved; used for side effects
--   OLD.col = value before the change (UPDATE, DELETE)
--   NEW.col = value after the change  (INSERT, UPDATE)
--
-- Triggers in this file:
--   1. Validation / cleaning  : trg_customers_before_insert / _before_update
--   2. Derived value upkeep   : trg_order_items_after_insert / _update / _delete
--   3. Audit logging          : *_audit_insert / _update / _delete on
--                               customers, products, orders, payments
--   4. Tamper protection      : trg_audit_logs_no_update / _no_delete
--
-- changed_by: applications set a session variable, e.g.
--   SET @app_user = 'etl_pipeline';
-- If it is not set we fall back to the MySQL login, USER().
-- =====================================================================

DROP TRIGGER IF EXISTS trg_customers_before_insert;
DROP TRIGGER IF EXISTS trg_customers_before_update;
DROP TRIGGER IF EXISTS trg_order_items_after_insert;
DROP TRIGGER IF EXISTS trg_order_items_after_update;
DROP TRIGGER IF EXISTS trg_order_items_after_delete;
DROP TRIGGER IF EXISTS trg_customers_audit_insert;
DROP TRIGGER IF EXISTS trg_customers_audit_update;
DROP TRIGGER IF EXISTS trg_customers_audit_delete;
DROP TRIGGER IF EXISTS trg_products_audit_insert;
DROP TRIGGER IF EXISTS trg_products_audit_update;
DROP TRIGGER IF EXISTS trg_products_audit_delete;
DROP TRIGGER IF EXISTS trg_orders_audit_insert;
DROP TRIGGER IF EXISTS trg_orders_audit_update;
DROP TRIGGER IF EXISTS trg_orders_audit_delete;
DROP TRIGGER IF EXISTS trg_payments_audit_insert;
DROP TRIGGER IF EXISTS trg_payments_audit_update;
DROP TRIGGER IF EXISTS trg_payments_audit_delete;
DROP TRIGGER IF EXISTS trg_audit_logs_no_update;
DROP TRIGGER IF EXISTS trg_audit_logs_no_delete;

DELIMITER $$

-- =====================================================================
-- 1. VALIDATION / CLEANING TRIGGERS
-- Last line of defence: even if a row does not come through the ETL
-- (e.g. someone inserts it by hand), it is cleaned and validated.
-- =====================================================================

CREATE TRIGGER trg_customers_before_insert
BEFORE INSERT ON customers
FOR EACH ROW
BEGIN
    SET NEW.email      = LOWER(TRIM(NEW.email));
    SET NEW.first_name = TRIM(NEW.first_name);
    SET NEW.last_name  = TRIM(NEW.last_name);

    IF NEW.signup_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'signup_date cannot be in the future';
    END IF;
END$$

CREATE TRIGGER trg_customers_before_update
BEFORE UPDATE ON customers
FOR EACH ROW
BEGIN
    SET NEW.email      = LOWER(TRIM(NEW.email));
    SET NEW.first_name = TRIM(NEW.first_name);
    SET NEW.last_name  = TRIM(NEW.last_name);

    IF NEW.signup_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'signup_date cannot be in the future';
    END IF;
END$$

-- =====================================================================
-- 2. DERIVED VALUE TRIGGERS
-- Keep orders.order_total = SUM(order_items.line_total) at all times,
-- whatever program changes order_items.
-- =====================================================================

CREATE TRIGGER trg_order_items_after_insert
AFTER INSERT ON order_items
FOR EACH ROW
BEGIN
    UPDATE orders
       SET order_total = (SELECT COALESCE(SUM(line_total), 0)
                            FROM order_items
                           WHERE order_id = NEW.order_id)
     WHERE order_id = NEW.order_id;
END$$

CREATE TRIGGER trg_order_items_after_update
AFTER UPDATE ON order_items
FOR EACH ROW
BEGIN
    UPDATE orders
       SET order_total = (SELECT COALESCE(SUM(line_total), 0)
                            FROM order_items
                           WHERE order_id = NEW.order_id)
     WHERE order_id = NEW.order_id;

    -- If the line was moved to another order, fix the old order too.
    IF OLD.order_id <> NEW.order_id THEN
        UPDATE orders
           SET order_total = (SELECT COALESCE(SUM(line_total), 0)
                                FROM order_items
                               WHERE order_id = OLD.order_id)
         WHERE order_id = OLD.order_id;
    END IF;
END$$

-- Note: rows removed by ON DELETE CASCADE (deleting a whole order) do
-- NOT fire this trigger - a known MySQL rule. That is fine here because
-- the parent order is being deleted anyway.
CREATE TRIGGER trg_order_items_after_delete
AFTER DELETE ON order_items
FOR EACH ROW
BEGIN
    UPDATE orders
       SET order_total = (SELECT COALESCE(SUM(line_total), 0)
                            FROM order_items
                           WHERE order_id = OLD.order_id)
     WHERE order_id = OLD.order_id;
END$$

-- =====================================================================
-- 3. AUDIT TRIGGERS
-- Every INSERT / UPDATE / DELETE on important tables writes one row to
-- audit_logs with the old and new values as JSON.
-- UPDATE triggers only log when a business column actually changed, so
-- re-loading identical data does not flood the audit log.
-- =====================================================================

-- ----------------------------- customers -----------------------------
CREATE TRIGGER trg_customers_audit_insert
AFTER INSERT ON customers
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('customers', NEW.customer_id, 'INSERT', NULL,
            JSON_OBJECT('customer_code', NEW.customer_code, 'first_name', NEW.first_name,
                        'last_name', NEW.last_name, 'email', NEW.email, 'city', NEW.city,
                        'segment', NEW.segment, 'is_active', NEW.is_active),
            COALESCE(@app_user, USER()));
END$$

CREATE TRIGGER trg_customers_audit_update
AFTER UPDATE ON customers
FOR EACH ROW
BEGIN
    -- <=> is the NULL-safe "equals" operator (NULL <=> NULL is TRUE)
    IF NOT (OLD.first_name <=> NEW.first_name AND OLD.last_name <=> NEW.last_name
            AND OLD.email <=> NEW.email AND OLD.phone <=> NEW.phone
            AND OLD.city <=> NEW.city AND OLD.state <=> NEW.state
            AND OLD.country <=> NEW.country AND OLD.segment <=> NEW.segment
            AND OLD.is_active <=> NEW.is_active) THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES ('customers', NEW.customer_id, 'UPDATE',
                JSON_OBJECT('first_name', OLD.first_name, 'last_name', OLD.last_name,
                            'email', OLD.email, 'phone', OLD.phone, 'city', OLD.city,
                            'segment', OLD.segment, 'is_active', OLD.is_active),
                JSON_OBJECT('first_name', NEW.first_name, 'last_name', NEW.last_name,
                            'email', NEW.email, 'phone', NEW.phone, 'city', NEW.city,
                            'segment', NEW.segment, 'is_active', NEW.is_active),
                COALESCE(@app_user, USER()));
    END IF;
END$$

CREATE TRIGGER trg_customers_audit_delete
AFTER DELETE ON customers
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('customers', OLD.customer_id, 'DELETE',
            JSON_OBJECT('customer_code', OLD.customer_code, 'first_name', OLD.first_name,
                        'last_name', OLD.last_name, 'email', OLD.email),
            NULL, COALESCE(@app_user, USER()));
END$$

-- ----------------------------- products ------------------------------
CREATE TRIGGER trg_products_audit_insert
AFTER INSERT ON products
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('products', NEW.product_id, 'INSERT', NULL,
            JSON_OBJECT('sku', NEW.sku, 'product_name', NEW.product_name, 'category', NEW.category,
                        'unit_price', NEW.unit_price, 'stock_quantity', NEW.stock_quantity),
            COALESCE(@app_user, USER()));
END$$

CREATE TRIGGER trg_products_audit_update
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    IF NOT (OLD.product_name <=> NEW.product_name AND OLD.category <=> NEW.category
            AND OLD.unit_price <=> NEW.unit_price AND OLD.stock_quantity <=> NEW.stock_quantity
            AND OLD.is_active <=> NEW.is_active) THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES ('products', NEW.product_id, 'UPDATE',
                JSON_OBJECT('product_name', OLD.product_name, 'category', OLD.category,
                            'unit_price', OLD.unit_price, 'stock_quantity', OLD.stock_quantity,
                            'is_active', OLD.is_active),
                JSON_OBJECT('product_name', NEW.product_name, 'category', NEW.category,
                            'unit_price', NEW.unit_price, 'stock_quantity', NEW.stock_quantity,
                            'is_active', NEW.is_active),
                COALESCE(@app_user, USER()));
    END IF;
END$$

CREATE TRIGGER trg_products_audit_delete
AFTER DELETE ON products
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('products', OLD.product_id, 'DELETE',
            JSON_OBJECT('sku', OLD.sku, 'product_name', OLD.product_name, 'unit_price', OLD.unit_price),
            NULL, COALESCE(@app_user, USER()));
END$$

-- ------------------------------ orders -------------------------------
CREATE TRIGGER trg_orders_audit_insert
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('orders', NEW.order_id, 'INSERT', NULL,
            JSON_OBJECT('order_number', NEW.order_number, 'customer_id', NEW.customer_id,
                        'employee_id', NEW.employee_id, 'order_date', NEW.order_date,
                        'status', NEW.status),
            COALESCE(@app_user, USER()));
END$$

-- order_total is NOT compared: it is a derived value recalculated by the
-- order_items triggers, and logging every recalculation would be noise.
CREATE TRIGGER trg_orders_audit_update
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF NOT (OLD.status <=> NEW.status AND OLD.customer_id <=> NEW.customer_id
            AND OLD.employee_id <=> NEW.employee_id AND OLD.order_date <=> NEW.order_date) THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES ('orders', NEW.order_id, 'UPDATE',
                JSON_OBJECT('status', OLD.status, 'customer_id', OLD.customer_id,
                            'employee_id', OLD.employee_id, 'order_date', OLD.order_date),
                JSON_OBJECT('status', NEW.status, 'customer_id', NEW.customer_id,
                            'employee_id', NEW.employee_id, 'order_date', NEW.order_date),
                COALESCE(@app_user, USER()));
    END IF;
END$$

CREATE TRIGGER trg_orders_audit_delete
AFTER DELETE ON orders
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('orders', OLD.order_id, 'DELETE',
            JSON_OBJECT('order_number', OLD.order_number, 'customer_id', OLD.customer_id,
                        'status', OLD.status, 'order_total', OLD.order_total),
            NULL, COALESCE(@app_user, USER()));
END$$

-- ----------------------------- payments ------------------------------
CREATE TRIGGER trg_payments_audit_insert
AFTER INSERT ON payments
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('payments', NEW.payment_id, 'INSERT', NULL,
            JSON_OBJECT('payment_reference', NEW.payment_reference, 'order_id', NEW.order_id,
                        'amount', NEW.amount, 'payment_method', NEW.payment_method,
                        'status', NEW.status),
            COALESCE(@app_user, USER()));
END$$

CREATE TRIGGER trg_payments_audit_update
AFTER UPDATE ON payments
FOR EACH ROW
BEGIN
    IF NOT (OLD.amount <=> NEW.amount AND OLD.status <=> NEW.status
            AND OLD.payment_method <=> NEW.payment_method AND OLD.order_id <=> NEW.order_id) THEN
        INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
        VALUES ('payments', NEW.payment_id, 'UPDATE',
                JSON_OBJECT('amount', OLD.amount, 'status', OLD.status,
                            'payment_method', OLD.payment_method, 'order_id', OLD.order_id),
                JSON_OBJECT('amount', NEW.amount, 'status', NEW.status,
                            'payment_method', NEW.payment_method, 'order_id', NEW.order_id),
                COALESCE(@app_user, USER()));
    END IF;
END$$

CREATE TRIGGER trg_payments_audit_delete
AFTER DELETE ON payments
FOR EACH ROW
BEGIN
    INSERT INTO audit_logs (table_name, record_id, action, old_values, new_values, changed_by)
    VALUES ('payments', OLD.payment_id, 'DELETE',
            JSON_OBJECT('payment_reference', OLD.payment_reference, 'order_id', OLD.order_id,
                        'amount', OLD.amount, 'status', OLD.status),
            NULL, COALESCE(@app_user, USER()));
END$$

-- =====================================================================
-- 4. TAMPER PROTECTION
-- An audit trail is only trustworthy if it cannot be edited, so the
-- audit_logs table is append-only.
-- =====================================================================

CREATE TRIGGER trg_audit_logs_no_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_logs is append-only: updates are not allowed';
END$$

CREATE TRIGGER trg_audit_logs_no_delete
BEFORE DELETE ON audit_logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_logs is append-only: deletes are not allowed';
END$$

DELIMITER ;
