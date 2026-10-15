-- =====================================================================
-- Enterprise Data Management & Analytics Platform
-- File: schema.sql
-- Purpose: Creates every table (production, ETL metadata, monitoring,
--          and staging) with keys and constraints.
-- Target: MySQL 8.0.16+ (CHECK constraints are enforced from 8.0.16)
--
-- Run order: schema.sql -> indexes.sql -> functions_procedures.sql
--            -> triggers.sql -> views.sql -> seed.sql
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- Drop in reverse dependency order so the script can be re-run safely.
DROP TABLE IF EXISTS stg_payments;
DROP TABLE IF EXISTS stg_order_items;
DROP TABLE IF EXISTS stg_orders;
DROP TABLE IF EXISTS stg_products;
DROP TABLE IF EXISTS stg_customers;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS data_quality_issues;
DROP TABLE IF EXISTS etl_execution_logs;
DROP TABLE IF EXISTS etl_jobs;
DROP TABLE IF EXISTS data_sources;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================================
-- PART 1: CORE BUSINESS (PRODUCTION) TABLES
-- =====================================================================

-- ---------------------------------------------------------------------
-- departments: one row per department. Kept separate from employees so
-- the department name is stored once (3NF) instead of on every employee.
-- ---------------------------------------------------------------------
CREATE TABLE departments (
    department_id   INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    department_name VARCHAR(60)   NOT NULL,
    location        VARCHAR(60)   NOT NULL,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_departments PRIMARY KEY (department_id),
    CONSTRAINT uq_departments_name UNIQUE (department_name)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- employees: staff members. manager_id is a SELF-REFERENCING foreign key
-- (an employee's manager is also an employee).
-- ---------------------------------------------------------------------
CREATE TABLE employees (
    employee_id    INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    employee_code  VARCHAR(20)    NOT NULL,               -- business key, e.g. EMP-1001
    first_name     VARCHAR(50)    NOT NULL,
    last_name      VARCHAR(50)    NOT NULL,
    email          VARCHAR(120)   NOT NULL,
    job_title      VARCHAR(80)    NOT NULL,
    department_id  INT UNSIGNED   NOT NULL,
    manager_id     INT UNSIGNED   NULL,                   -- NULL for top-level managers
    hire_date      DATE           NOT NULL,
    salary         DECIMAL(10,2)  NOT NULL,
    is_active      BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_employees PRIMARY KEY (employee_id),
    CONSTRAINT uq_employees_code  UNIQUE (employee_code),
    CONSTRAINT uq_employees_email UNIQUE (email),
    CONSTRAINT fk_employees_department FOREIGN KEY (department_id)
        REFERENCES departments (department_id) ON DELETE RESTRICT,
    CONSTRAINT fk_employees_manager FOREIGN KEY (manager_id)
        REFERENCES employees (employee_id) ON DELETE SET NULL,
    CONSTRAINT chk_employees_salary CHECK (salary > 0)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- customers: people/companies who place orders.
-- customer_id   = surrogate key used inside the database (fast integer).
-- customer_code = business key that arrives from the source CRM file.
-- ---------------------------------------------------------------------
CREATE TABLE customers (
    customer_id    INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    customer_code  VARCHAR(20)   NOT NULL,
    first_name     VARCHAR(50)   NOT NULL,
    last_name      VARCHAR(50)   NOT NULL,
    email          VARCHAR(120)  NOT NULL,
    phone          VARCHAR(20)   NULL,
    city           VARCHAR(60)   NOT NULL,
    state          VARCHAR(60)   NULL,
    country        VARCHAR(60)   NOT NULL,
    segment        VARCHAR(20)   NOT NULL,
    signup_date    DATE          NOT NULL,
    is_active      BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_customers PRIMARY KEY (customer_id),
    CONSTRAINT uq_customers_code  UNIQUE (customer_code),
    CONSTRAINT uq_customers_email UNIQUE (email),
    CONSTRAINT chk_customers_segment CHECK (segment IN ('Retail', 'SMB', 'Corporate')),
    CONSTRAINT chk_customers_email   CHECK (email LIKE '%_@_%._%')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- products: items that can be sold.
-- ---------------------------------------------------------------------
CREATE TABLE products (
    product_id      INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    sku             VARCHAR(20)    NOT NULL,              -- business key, e.g. SKU-LAP-001
    product_name    VARCHAR(120)   NOT NULL,
    category        VARCHAR(50)    NOT NULL,
    unit_price      DECIMAL(10,2)  NOT NULL,
    stock_quantity  INT            NOT NULL DEFAULT 0,
    is_active       BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_products PRIMARY KEY (product_id),
    CONSTRAINT uq_products_sku UNIQUE (sku),
    CONSTRAINT chk_products_price CHECK (unit_price >= 0),
    CONSTRAINT chk_products_stock CHECK (stock_quantity >= 0)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- orders: the order "header". One customer -> many orders.
-- employee_id = sales employee who handled the order (NULL = online order).
-- order_total is a DERIVED value (sum of line totals) that triggers keep
-- up to date. It is a deliberate, documented denormalization so reports
-- do not have to re-sum order_items every time.
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    order_id      INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    order_number  VARCHAR(20)    NOT NULL,                -- business key, e.g. ORD-100001
    customer_id   INT UNSIGNED   NOT NULL,
    employee_id   INT UNSIGNED   NULL,
    order_date    DATETIME       NOT NULL,
    status        VARCHAR(20)    NOT NULL DEFAULT 'PENDING',
    order_total   DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    created_at    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_orders PRIMARY KEY (order_id),
    CONSTRAINT uq_orders_number UNIQUE (order_number),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
        REFERENCES customers (customer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_orders_employee FOREIGN KEY (employee_id)
        REFERENCES employees (employee_id) ON DELETE SET NULL,
    CONSTRAINT chk_orders_status CHECK (status IN ('PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED')),
    CONSTRAINT chk_orders_total  CHECK (order_total >= 0)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- order_items: the order "lines". This is the junction table that
-- resolves the MANY-TO-MANY relationship between orders and products.
-- unit_price is the price AT THE TIME OF SALE (prices change later), so
-- it is a fact about the order line, not a copy of products.unit_price.
-- line_total is a STORED GENERATED column computed by MySQL itself.
-- ---------------------------------------------------------------------
CREATE TABLE order_items (
    order_item_id  INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    order_id       INT UNSIGNED   NOT NULL,
    product_id     INT UNSIGNED   NOT NULL,
    quantity       INT            NOT NULL,
    unit_price     DECIMAL(10,2)  NOT NULL,
    discount_pct   DECIMAL(5,2)   NOT NULL DEFAULT 0.00,
    line_total     DECIMAL(12,2)  AS (ROUND(quantity * unit_price * (1 - discount_pct / 100), 2)) STORED,
    CONSTRAINT pk_order_items PRIMARY KEY (order_item_id),
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id)
        REFERENCES orders (order_id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id)
        REFERENCES products (product_id) ON DELETE RESTRICT,
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_items_price    CHECK (unit_price >= 0),
    CONSTRAINT chk_order_items_discount CHECK (discount_pct BETWEEN 0 AND 100)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- payments: money received against an order. One order -> many payments
-- (failed attempt + retry, or part payments).
-- payment_reference is the gateway transaction id; UNIQUE prevents the
-- same transaction from being recorded twice.
-- ---------------------------------------------------------------------
CREATE TABLE payments (
    payment_id         INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    payment_reference  VARCHAR(30)    NOT NULL,
    order_id           INT UNSIGNED   NOT NULL,
    payment_date       DATETIME       NOT NULL,
    amount             DECIMAL(12,2)  NOT NULL,
    payment_method     VARCHAR(20)    NOT NULL,
    status             VARCHAR(20)    NOT NULL,
    created_at         TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_payments PRIMARY KEY (payment_id),
    CONSTRAINT uq_payments_reference UNIQUE (payment_reference),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id)
        REFERENCES orders (order_id) ON DELETE RESTRICT,
    CONSTRAINT chk_payments_amount CHECK (amount > 0),
    CONSTRAINT chk_payments_method CHECK (payment_method IN ('CARD', 'UPI', 'NET_BANKING', 'BANK_TRANSFER', 'WALLET')),
    CONSTRAINT chk_payments_status CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED'))
) ENGINE = InnoDB;

-- =====================================================================
-- PART 2: ETL METADATA TABLES
-- =====================================================================

-- data_sources: the systems that send us data (CRM, payment gateway...).
CREATE TABLE data_sources (
    source_id    INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    source_name  VARCHAR(80)   NOT NULL,
    source_type  VARCHAR(20)   NOT NULL,
    description  VARCHAR(255)  NULL,
    is_active    BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_data_sources PRIMARY KEY (source_id),
    CONSTRAINT uq_data_sources_name UNIQUE (source_name),
    CONSTRAINT chk_data_sources_type CHECK (source_type IN ('CSV', 'API', 'DATABASE'))
) ENGINE = InnoDB;

-- etl_jobs: the DEFINITION of a job (what to load, from where, to where).
CREATE TABLE etl_jobs (
    job_id        INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    job_name      VARCHAR(80)   NOT NULL,
    source_id     INT UNSIGNED  NOT NULL,
    source_file   VARCHAR(120)  NOT NULL,
    target_table  VARCHAR(64)   NOT NULL,
    description   VARCHAR(255)  NULL,
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_etl_jobs PRIMARY KEY (job_id),
    CONSTRAINT uq_etl_jobs_name UNIQUE (job_name),
    CONSTRAINT fk_etl_jobs_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE RESTRICT
) ENGINE = InnoDB;

-- etl_execution_logs: one row per RUN of a job (a job runs many times).
CREATE TABLE etl_execution_logs (
    execution_id      BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    job_id            INT UNSIGNED     NOT NULL,
    started_at        DATETIME(3)      NOT NULL,       -- (3) = millisecond precision
    ended_at          DATETIME(3)      NULL,           -- NULL while RUNNING
    records_read      INT              NOT NULL DEFAULT 0,
    records_inserted  INT              NOT NULL DEFAULT 0,
    records_updated   INT              NOT NULL DEFAULT 0,
    records_rejected  INT              NOT NULL DEFAULT 0,
    error_count       INT              NOT NULL DEFAULT 0,
    status            VARCHAR(20)      NOT NULL DEFAULT 'RUNNING',
    error_message     VARCHAR(1000)    NULL,
    CONSTRAINT pk_etl_execution_logs PRIMARY KEY (execution_id),
    CONSTRAINT fk_etl_logs_job FOREIGN KEY (job_id)
        REFERENCES etl_jobs (job_id) ON DELETE CASCADE,
    CONSTRAINT chk_etl_logs_status CHECK (status IN ('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED')),
    CONSTRAINT chk_etl_logs_counts CHECK (records_read >= 0 AND records_inserted >= 0
                                          AND records_updated >= 0 AND records_rejected >= 0
                                          AND error_count >= 0),
    CONSTRAINT chk_etl_logs_dates  CHECK (ended_at IS NULL OR ended_at >= started_at)
) ENGINE = InnoDB;

-- =====================================================================
-- PART 3: MONITORING TABLES
-- =====================================================================

-- data_quality_issues: every bad record or rule violation we detect.
-- execution_id is NULL when the issue comes from an in-database check
-- (sp_run_data_quality_checks) instead of an ETL run.
CREATE TABLE data_quality_issues (
    issue_id           BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    execution_id       BIGINT UNSIGNED  NULL,
    source_id          INT UNSIGNED     NULL,
    table_name         VARCHAR(64)      NOT NULL,
    record_identifier  VARCHAR(100)     NULL,          -- business key or CSV row number
    column_name        VARCHAR(64)      NULL,
    rule_name          VARCHAR(60)      NOT NULL,      -- which check found it, e.g. email_format
    issue_type         VARCHAR(40)      NOT NULL,
    description        VARCHAR(500)     NOT NULL,
    severity           VARCHAR(10)      NOT NULL,
    detected_at        DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolution_status  VARCHAR(20)      NOT NULL DEFAULT 'OPEN',
    resolved_at        DATETIME         NULL,
    resolution_note    VARCHAR(255)     NULL,
    CONSTRAINT pk_data_quality_issues PRIMARY KEY (issue_id),
    CONSTRAINT fk_dq_execution FOREIGN KEY (execution_id)
        REFERENCES etl_execution_logs (execution_id) ON DELETE SET NULL,
    CONSTRAINT fk_dq_source FOREIGN KEY (source_id)
        REFERENCES data_sources (source_id) ON DELETE SET NULL,
    CONSTRAINT chk_dq_issue_type CHECK (issue_type IN (
        'MISSING_COLUMN', 'MISSING_VALUE', 'DUPLICATE_RECORD', 'INVALID_FORMAT',
        'INVALID_DATE', 'INVALID_VALUE', 'NEGATIVE_VALUE', 'INVALID_REFERENCE',
        'BUSINESS_RULE')),
    CONSTRAINT chk_dq_severity CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT chk_dq_status   CHECK (resolution_status IN ('OPEN', 'RESOLVED', 'IGNORED')),
    CONSTRAINT chk_dq_resolved CHECK (resolution_status = 'OPEN' OR resolved_at IS NOT NULL)
) ENGINE = InnoDB;

-- audit_logs: who changed what, and when. Written ONLY by triggers.
-- old_values / new_values use MySQL's JSON type so one audit table can
-- hold changes from any table.
CREATE TABLE audit_logs (
    audit_id     BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
    table_name   VARCHAR(64)      NOT NULL,
    record_id    INT UNSIGNED     NOT NULL,
    action       VARCHAR(10)      NOT NULL,
    old_values   JSON             NULL,               -- NULL for INSERT
    new_values   JSON             NULL,               -- NULL for DELETE
    changed_by   VARCHAR(100)     NOT NULL,
    changed_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_audit_logs PRIMARY KEY (audit_id),
    CONSTRAINT chk_audit_action CHECK (action IN ('INSERT', 'UPDATE', 'DELETE'))
) ENGINE = InnoDB;

-- =====================================================================
-- PART 4: STAGING TABLES
-- Landing area for data that already passed row-level validation in
-- Python. They intentionally have NO foreign keys or unique keys: their
-- job is to hold one batch so SQL can check references against
-- production before anything is moved. They are emptied every run.
-- The *_id columns start NULL and are filled by the ETL with
-- UPDATE ... JOIN (business key -> surrogate key). A row whose id stays
-- NULL has an invalid reference and is rejected.
-- load_status shows, after a run, which rows were LOADED or REJECTED.
-- source_row = line number in the CSV, so issues can point to the file.
-- =====================================================================

CREATE TABLE stg_customers (
    stg_id         INT UNSIGNED     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    execution_id   BIGINT UNSIGNED  NOT NULL,
    source_row     INT              NOT NULL,
    customer_code  VARCHAR(20),
    first_name     VARCHAR(50),
    last_name      VARCHAR(50),
    email          VARCHAR(120),
    phone          VARCHAR(20),
    city           VARCHAR(60),
    state          VARCHAR(60),
    country        VARCHAR(60),
    segment        VARCHAR(20),
    signup_date    DATE,
    load_status        VARCHAR(10)      NOT NULL DEFAULT 'PENDING',   -- PENDING / LOADED / REJECTED
    loaded_at      TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE stg_products (
    stg_id          INT UNSIGNED     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    execution_id    BIGINT UNSIGNED  NOT NULL,
    source_row      INT              NOT NULL,
    sku             VARCHAR(20),
    product_name    VARCHAR(120),
    category        VARCHAR(50),
    unit_price      DECIMAL(10,2),
    stock_quantity  INT,
    load_status        VARCHAR(10)      NOT NULL DEFAULT 'PENDING',   -- PENDING / LOADED / REJECTED
    loaded_at       TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE stg_orders (
    stg_id         INT UNSIGNED     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    execution_id   BIGINT UNSIGNED  NOT NULL,
    source_row     INT              NOT NULL,
    order_number   VARCHAR(20),
    customer_code  VARCHAR(20),
    employee_code  VARCHAR(20),
    order_date     DATETIME,
    status         VARCHAR(20),
    customer_id    INT UNSIGNED,          -- resolved from customer_code during load
    employee_id    INT UNSIGNED,          -- resolved from employee_code during load
    load_status        VARCHAR(10)      NOT NULL DEFAULT 'PENDING',   -- PENDING / LOADED / REJECTED
    loaded_at      TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE stg_order_items (
    stg_id        INT UNSIGNED     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    execution_id  BIGINT UNSIGNED  NOT NULL,
    source_row    INT              NOT NULL,
    order_number  VARCHAR(20),
    sku           VARCHAR(20),
    quantity      INT,
    unit_price    DECIMAL(10,2),
    discount_pct  DECIMAL(5,2),
    order_id      INT UNSIGNED,           -- resolved from order_number during load
    product_id    INT UNSIGNED,           -- resolved from sku during load
    load_status        VARCHAR(10)      NOT NULL DEFAULT 'PENDING',   -- PENDING / LOADED / REJECTED
    loaded_at     TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE stg_payments (
    stg_id             INT UNSIGNED     NOT NULL AUTO_INCREMENT PRIMARY KEY,
    execution_id       BIGINT UNSIGNED  NOT NULL,
    source_row         INT              NOT NULL,
    payment_reference  VARCHAR(30),
    order_number       VARCHAR(20),
    payment_date       DATETIME,
    amount             DECIMAL(12,2),
    payment_method     VARCHAR(20),
    status             VARCHAR(20),
    order_id           INT UNSIGNED,      -- resolved from order_number during load
    load_status        VARCHAR(10)      NOT NULL DEFAULT 'PENDING',   -- PENDING / LOADED / REJECTED
    loaded_at          TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE = InnoDB;
