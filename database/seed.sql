-- =====================================================================
-- File: seed.sql
-- Purpose: REFERENCE / MASTER data that the ETL pipeline depends on:
--          departments, employees, data sources and ETL job definitions.
--
-- Operational data (customers, products, orders, order_items, payments)
-- is NOT inserted here - it arrives through the ETL pipeline from the
-- CSV files in etl/data/raw/, exactly like it would from real systems.
-- =====================================================================

SET @app_user = 'seed_script';

-- ---------------------------------------------------------------------
-- departments
-- ---------------------------------------------------------------------
INSERT INTO departments (department_id, department_name, location) VALUES
    (1, 'Sales',            'Mumbai'),
    (2, 'Finance',          'Pune'),
    (3, 'Operations',       'Bengaluru'),
    (4, 'Data Engineering', 'Bengaluru'),
    (5, 'Customer Support', 'Hyderabad');

-- ---------------------------------------------------------------------
-- employees
-- Department heads first (manager_id = NULL), then their teams, because
-- a manager_id must point to an employee that already exists.
-- ---------------------------------------------------------------------
INSERT INTO employees (employee_id, employee_code, first_name, last_name, email, job_title, department_id, manager_id, hire_date, salary) VALUES
    (1,  'EMP-1001', 'Rajesh',   'Kulkarni',  'rajesh.kulkarni@edp.local',  'Head of Sales',            1, NULL, '2019-04-01', 210000.00),
    (2,  'EMP-1002', 'Meera',    'Iyer',      'meera.iyer@edp.local',       'Finance Manager',          2, NULL, '2019-07-15', 185000.00),
    (3,  'EMP-1003', 'Arjun',    'Menon',     'arjun.menon@edp.local',      'Operations Manager',       3, NULL, '2020-01-06', 170000.00),
    (4,  'EMP-1004', 'Kavya',    'Reddy',     'kavya.reddy@edp.local',      'Data Engineering Lead',    4, NULL, '2020-03-02', 220000.00),
    (5,  'EMP-1005', 'Sanjay',   'Thomas',    'sanjay.thomas@edp.local',    'Support Manager',          5, NULL, '2020-08-17', 140000.00),
    (6,  'EMP-1006', 'Priya',    'Nair',      'priya.nair@edp.local',       'Senior Account Executive', 1, 1,    '2020-11-09', 115000.00),
    (7,  'EMP-1007', 'Vikram',   'Joshi',     'vikram.joshi@edp.local',     'Account Executive',        1, 1,    '2021-02-22',  85000.00),
    (8,  'EMP-1008', 'Ananya',   'Desai',     'ananya.desai@edp.local',     'Account Executive',        1, 1,    '2021-06-14',  82000.00),
    (9,  'EMP-1009', 'Rohit',    'Verma',     'rohit.verma@edp.local',      'Account Executive',        1, 6,    '2022-01-10',  78000.00),
    (10, 'EMP-1010', 'Neha',     'Kapoor',    'neha.kapoor@edp.local',      'Sales Associate',          1, 6,    '2023-03-20',  62000.00),
    (11, 'EMP-1011', 'Daniel',   'Fernandes', 'daniel.fernandes@edp.local', 'Sales Associate',          1, 7,    '2023-09-04',  60000.00),
    (12, 'EMP-1012', 'Ishita',   'Bose',      'ishita.bose@edp.local',      'Sales Associate',          1, 7,    '2024-05-13',  58000.00),
    (13, 'EMP-1013', 'Karan',    'Malhotra',  'karan.malhotra@edp.local',   'Accountant',               2, 2,    '2021-08-02',  72000.00),
    (14, 'EMP-1014', 'Fatima',   'Shaikh',    'fatima.shaikh@edp.local',    'Payments Analyst',         2, 2,    '2022-10-17',  68000.00),
    (15, 'EMP-1015', 'Suresh',   'Pillai',    'suresh.pillai@edp.local',    'Logistics Coordinator',    3, 3,    '2021-12-06',  64000.00),
    (16, 'EMP-1016', 'Lakshmi',  'Rao',       'lakshmi.rao@edp.local',      'Inventory Analyst',        3, 3,    '2023-01-16',  66000.00),
    (17, 'EMP-1017', 'Aditya',   'Banerjee',  'aditya.banerjee@edp.local',  'Data Engineer',            4, 4,    '2022-07-25', 125000.00),
    (18, 'EMP-1018', 'Sneha',    'Patil',     'sneha.patil@edp.local',      'Data Analyst',             4, 4,    '2023-06-12',  95000.00),
    (19, 'EMP-1019', 'Mohammed', 'Khan',      'mohammed.khan@edp.local',    'Support Specialist',       5, 5,    '2022-04-04',  52000.00),
    (20, 'EMP-1020', 'Riya',     'Chatterjee','riya.chatterjee@edp.local',  'Support Specialist',       5, 5,    '2024-02-19',  50000.00);

-- ---------------------------------------------------------------------
-- data_sources: the systems that feed the platform
-- ---------------------------------------------------------------------
INSERT INTO data_sources (source_id, source_name, source_type, description) VALUES
    (1, 'CRM System',              'CSV',      'Customer master data exported nightly from the CRM'),
    (2, 'Product Catalog',         'CSV',      'Product list and stock levels from the inventory system'),
    (3, 'Order Management System', 'CSV',      'Order headers and order lines'),
    (4, 'Payment Gateway',         'CSV',      'Settlement file with payment transactions'),
    (5, 'Production Database',     'DATABASE', 'In-database business rule checks (sp_run_data_quality_checks)');

-- ---------------------------------------------------------------------
-- etl_jobs: one job per source file. The run order matters because of
-- foreign keys: customers & products -> orders -> order_items -> payments.
-- ---------------------------------------------------------------------
INSERT INTO etl_jobs (job_id, job_name, source_id, source_file, target_table, description) VALUES
    (1, 'load_customers',   1, 'customers.csv',   'customers',   'Validate and upsert customer master data'),
    (2, 'load_products',    2, 'products.csv',    'products',    'Validate and upsert product catalog'),
    (3, 'load_orders',      3, 'orders.csv',      'orders',      'Validate orders and resolve customer / employee references'),
    (4, 'load_order_items', 3, 'order_items.csv', 'order_items', 'Validate order lines and resolve order / product references'),
    (5, 'load_payments',    4, 'payments.csv',    'payments',    'Validate payments, detect duplicate transactions');
