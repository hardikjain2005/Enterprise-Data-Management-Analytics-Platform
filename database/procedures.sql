-- =====================================================================
-- File: procedures.sql
-- Purpose: MySQL stored FUNCTIONS and stored PROCEDURES.
--
-- Function  = returns ONE value, can be used inside a SELECT.
-- Procedure = a saved block of SQL you run with CALL. It can return
--             result sets, use OUT parameters, run transactions.
--
-- DELIMITER: inside a routine every statement ends with ';'. We
-- temporarily change the client's statement terminator to '$$' so the
-- mysql client sends the whole CREATE ... END block as ONE statement.
--
-- Binary logging is on by default in MySQL 8, so every function must
-- declare whether it reads or modifies data (READS SQL DATA here).
-- =====================================================================

DROP FUNCTION  IF EXISTS fn_customer_total_spent;
DROP FUNCTION  IF EXISTS fn_order_balance;
DROP FUNCTION  IF EXISTS fn_customer_tier;
DROP PROCEDURE IF EXISTS sp_get_customer_summary;
DROP PROCEDURE IF EXISTS sp_update_order_status;
DROP PROCEDURE IF EXISTS sp_record_payment;
DROP PROCEDURE IF EXISTS sp_sales_report;
DROP PROCEDURE IF EXISTS sp_run_data_quality_checks;

DELIMITER $$

-- =====================================================================
-- FUNCTIONS
-- =====================================================================

-- ---------------------------------------------------------------------
-- fn_customer_total_spent(customer_id)
-- Lifetime order value of a customer (cancelled orders excluded).
-- Usage: SELECT customer_code, fn_customer_total_spent(customer_id) FROM customers;
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_customer_total_spent(p_customer_id INT UNSIGNED)
RETURNS DECIMAL(12,2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(12,2);

    SELECT COALESCE(SUM(order_total), 0)
      INTO v_total
      FROM orders
     WHERE customer_id = p_customer_id
       AND status <> 'CANCELLED';

    RETURN v_total;
END$$

-- ---------------------------------------------------------------------
-- fn_order_balance(order_id)
-- Amount still to be paid = order total - completed payments.
-- Returns NULL if the order does not exist.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_order_balance(p_order_id INT UNSIGNED)
RETURNS DECIMAL(12,2)
READS SQL DATA
BEGIN
    DECLARE v_total DECIMAL(12,2);
    DECLARE v_paid  DECIMAL(12,2);

    SELECT order_total INTO v_total
      FROM orders
     WHERE order_id = p_order_id;

    SELECT COALESCE(SUM(amount), 0) INTO v_paid
      FROM payments
     WHERE order_id = p_order_id
       AND status = 'COMPLETED';

    RETURN v_total - v_paid;
END$$

-- ---------------------------------------------------------------------
-- fn_customer_tier(customer_id)
-- Business classification used in reports. Reuses fn_customer_total_spent
-- so the "what counts as spend" rule lives in one place.
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_customer_tier(p_customer_id INT UNSIGNED)
RETURNS VARCHAR(10)
READS SQL DATA
BEGIN
    DECLARE v_spent DECIMAL(12,2);
    SET v_spent = fn_customer_total_spent(p_customer_id);

    RETURN CASE
        WHEN v_spent >= 1000000 THEN 'PLATINUM'
        WHEN v_spent >=  400000 THEN 'GOLD'
        WHEN v_spent >=  100000 THEN 'SILVER'
        ELSE 'BRONZE'
    END;
END$$

-- =====================================================================
-- PROCEDURES
-- =====================================================================

-- ---------------------------------------------------------------------
-- sp_get_customer_summary(customer_id)
-- Returns one row: the customer's order totals and payment totals.
-- Usage: CALL sp_get_customer_summary(1);
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_get_customer_summary(IN p_customer_id INT UNSIGNED)
READS SQL DATA
BEGIN
    SELECT  c.customer_id,
            c.customer_code,
            CONCAT(c.first_name, ' ', c.last_name)                         AS customer_name,
            c.segment,
            COUNT(o.order_id)                                              AS total_orders,
            SUM(CASE WHEN o.status = 'CANCELLED' THEN 1 ELSE 0 END)        AS cancelled_orders,
            fn_customer_total_spent(c.customer_id)                         AS total_spent,
            COALESCE((SELECT SUM(p.amount)
                        FROM payments p
                        JOIN orders o2 ON o2.order_id = p.order_id
                       WHERE o2.customer_id = c.customer_id
                         AND p.status = 'COMPLETED'), 0)                   AS total_paid,
            MIN(o.order_date)                                              AS first_order_date,
            MAX(o.order_date)                                              AS last_order_date,
            fn_customer_tier(c.customer_id)                                AS tier
      FROM  customers c
      LEFT JOIN orders o ON o.customer_id = c.customer_id
     WHERE  c.customer_id = p_customer_id
     GROUP BY c.customer_id, c.customer_code, c.first_name, c.last_name, c.segment;
END$$

-- ---------------------------------------------------------------------
-- sp_update_order_status(order_id, new_status)
-- Changes an order's status ONLY along allowed transitions:
--   PENDING -> PROCESSING -> SHIPPED -> DELIVERED
--   PENDING / PROCESSING -> CANCELLED
-- Anything else raises an error with SIGNAL (like "throw" in Java).
-- The audit trigger on orders records the change automatically.
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_update_order_status(
    IN p_order_id   INT UNSIGNED,
    IN p_new_status VARCHAR(20)
)
MODIFIES SQL DATA
BEGIN
    DECLARE v_current VARCHAR(20);

    SELECT status INTO v_current
      FROM orders
     WHERE order_id = p_order_id;

    IF v_current IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order not found';
    END IF;

    IF NOT (
           (v_current = 'PENDING'    AND p_new_status IN ('PROCESSING', 'CANCELLED'))
        OR (v_current = 'PROCESSING' AND p_new_status IN ('SHIPPED', 'CANCELLED'))
        OR (v_current = 'SHIPPED'    AND p_new_status = 'DELIVERED')
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Invalid status transition';
    END IF;

    UPDATE orders
       SET status = p_new_status
     WHERE order_id = p_order_id;

    SELECT order_id, order_number, v_current AS old_status, status AS new_status
      FROM orders
     WHERE order_id = p_order_id;
END$$

-- ---------------------------------------------------------------------
-- sp_record_payment(order_id, amount, method, reference, OUT payment_id)
-- Records a COMPLETED payment inside a TRANSACTION.
--   1. Lock the order row (SELECT ... FOR UPDATE) so two payments for the
--      same order cannot be processed at the same moment.
--   2. Validate: order exists, not cancelled, amount > 0, not overpaying.
--   3. Insert the payment.
--   4. COMMIT. If ANY step fails, the EXIT HANDLER does ROLLBACK, so
--      nothing is half-saved (Atomicity).
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_record_payment(
    IN  p_order_id   INT UNSIGNED,
    IN  p_amount     DECIMAL(12,2),
    IN  p_method     VARCHAR(20),
    IN  p_reference  VARCHAR(30),
    OUT p_payment_id INT UNSIGNED
)
MODIFIES SQL DATA
BEGIN
    DECLARE v_status  VARCHAR(20);
    DECLARE v_balance DECIMAL(12,2);

    -- If any SQL error happens below: undo everything, then re-raise the
    -- same error so the caller (API) sees the real message.
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT status INTO v_status
      FROM orders
     WHERE order_id = p_order_id
       FOR UPDATE;                                   -- row lock until COMMIT

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order not found';
    END IF;

    IF v_status = 'CANCELLED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot pay for a cancelled order';
    END IF;

    IF p_amount IS NULL OR p_amount <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment amount must be greater than zero';
    END IF;

    SET v_balance = fn_order_balance(p_order_id);

    IF p_amount > v_balance THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment exceeds outstanding balance';
    END IF;

    -- A duplicate p_reference violates uq_payments_reference -> handler -> ROLLBACK
    INSERT INTO payments (payment_reference, order_id, payment_date, amount, payment_method, status)
    VALUES (p_reference, p_order_id, NOW(), p_amount, p_method, 'COMPLETED');

    SET p_payment_id = LAST_INSERT_ID();

    COMMIT;
END$$

-- ---------------------------------------------------------------------
-- sp_sales_report(start_date, end_date)
-- Operational report: one row per month in the date range.
-- end_date is EXCLUSIVE (half-open range), e.g. '2026-01-01' to '2026-04-01'
-- means January..March. A half-open range lets the order_date index be used.
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_sales_report(
    IN p_start_date DATE,
    IN p_end_date   DATE
)
READS SQL DATA
BEGIN
    IF p_start_date IS NULL OR p_end_date IS NULL OR p_end_date <= p_start_date THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'end_date must be after start_date';
    END IF;

    SELECT  DATE_FORMAT(o.order_date, '%Y-%m')                               AS sales_month,
            COUNT(*)                                                         AS total_orders,
            SUM(CASE WHEN o.status = 'CANCELLED' THEN 1 ELSE 0 END)          AS cancelled_orders,
            COUNT(DISTINCT o.customer_id)                                    AS unique_customers,
            SUM(CASE WHEN o.status <> 'CANCELLED' THEN o.order_total ELSE 0 END) AS revenue,
            ROUND(AVG(CASE WHEN o.status <> 'CANCELLED' THEN o.order_total END), 2) AS avg_order_value
      FROM  orders o
     WHERE  o.order_date >= p_start_date
       AND  o.order_date <  p_end_date
     GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
     ORDER BY sales_month;
END$$

-- ---------------------------------------------------------------------
-- sp_run_data_quality_checks(OUT issues_found)
-- Business-rule checks that can only be done once data is IN the
-- database (they need several tables). Each check inserts a row into
-- data_quality_issues, but only if the same problem is not already
-- logged as OPEN (so running it twice does not create duplicates).
-- ---------------------------------------------------------------------
CREATE PROCEDURE sp_run_data_quality_checks(OUT p_issues_found INT)
MODIFIES SQL DATA
BEGIN
    DECLARE v_source_id INT UNSIGNED;
    DECLARE v_before    BIGINT;

    SELECT source_id INTO v_source_id
      FROM data_sources
     WHERE source_name = 'Production Database';

    SELECT COUNT(*) INTO v_before FROM data_quality_issues;

    -- Check 1: an active order must have at least one line item.
    INSERT INTO data_quality_issues
        (source_id, table_name, record_identifier, rule_name, issue_type, description, severity)
    SELECT v_source_id, 'orders', o.order_number, 'order_has_items', 'BUSINESS_RULE',
           CONCAT('Order ', o.order_number, ' has no order items'), 'HIGH'
      FROM orders o
     WHERE o.status <> 'CANCELLED'
       AND NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.order_id = o.order_id)
       AND NOT EXISTS (SELECT 1 FROM data_quality_issues d
                        WHERE d.rule_name = 'order_has_items'
                          AND d.record_identifier = o.order_number
                          AND d.resolution_status = 'OPEN');

    -- Check 2: a DELIVERED order should be fully paid.
    INSERT INTO data_quality_issues
        (source_id, table_name, record_identifier, rule_name, issue_type, description, severity)
    SELECT v_source_id, 'orders', o.order_number, 'delivered_order_paid', 'BUSINESS_RULE',
           CONCAT('Delivered order ', o.order_number, ' has unpaid balance of ',
                  o.order_total - COALESCE(p.paid, 0)), 'HIGH'
      FROM orders o
      LEFT JOIN (SELECT order_id, SUM(amount) AS paid
                   FROM payments
                  WHERE status = 'COMPLETED'
                  GROUP BY order_id) p ON p.order_id = o.order_id
     WHERE o.status = 'DELIVERED'
       AND o.order_total - COALESCE(p.paid, 0) > 0
       AND NOT EXISTS (SELECT 1 FROM data_quality_issues d
                        WHERE d.rule_name = 'delivered_order_paid'
                          AND d.record_identifier = o.order_number
                          AND d.resolution_status = 'OPEN');

    -- Check 3: completed payments must never exceed the order total.
    INSERT INTO data_quality_issues
        (source_id, table_name, record_identifier, rule_name, issue_type, description, severity)
    SELECT v_source_id, 'payments', o.order_number, 'no_overpayment', 'BUSINESS_RULE',
           CONCAT('Order ', o.order_number, ' is overpaid by ', p.paid - o.order_total), 'CRITICAL'
      FROM orders o
      JOIN (SELECT order_id, SUM(amount) AS paid
              FROM payments
             WHERE status = 'COMPLETED'
             GROUP BY order_id) p ON p.order_id = o.order_id
     WHERE p.paid > o.order_total
       AND NOT EXISTS (SELECT 1 FROM data_quality_issues d
                        WHERE d.rule_name = 'no_overpayment'
                          AND d.record_identifier = o.order_number
                          AND d.resolution_status = 'OPEN');

    -- Check 4: a payment cannot happen before its order was placed.
    INSERT INTO data_quality_issues
        (source_id, table_name, record_identifier, rule_name, issue_type, description, severity)
    SELECT v_source_id, 'payments', p.payment_reference, 'payment_after_order', 'INVALID_DATE',
           CONCAT('Payment ', p.payment_reference, ' (', p.payment_date,
                  ') is dated before order ', o.order_number, ' (', o.order_date, ')'), 'MEDIUM'
      FROM payments p
      JOIN orders o ON o.order_id = p.order_id
     WHERE p.payment_date < o.order_date
       AND NOT EXISTS (SELECT 1 FROM data_quality_issues d
                        WHERE d.rule_name = 'payment_after_order'
                          AND d.record_identifier = p.payment_reference
                          AND d.resolution_status = 'OPEN');

    -- Check 5: a customer cannot order before they signed up.
    INSERT INTO data_quality_issues
        (source_id, table_name, record_identifier, rule_name, issue_type, description, severity)
    SELECT v_source_id, 'orders', o.order_number, 'order_after_signup', 'INVALID_DATE',
           CONCAT('Order ', o.order_number, ' is dated before customer ',
                  c.customer_code, ' signed up (', c.signup_date, ')'), 'LOW'
      FROM orders o
      JOIN customers c ON c.customer_id = o.customer_id
     WHERE DATE(o.order_date) < c.signup_date
       AND NOT EXISTS (SELECT 1 FROM data_quality_issues d
                        WHERE d.rule_name = 'order_after_signup'
                          AND d.record_identifier = o.order_number
                          AND d.resolution_status = 'OPEN');

    SELECT COUNT(*) - v_before INTO p_issues_found FROM data_quality_issues;
END$$

DELIMITER ;
