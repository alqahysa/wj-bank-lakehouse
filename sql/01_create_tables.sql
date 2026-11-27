-- WJ Bank operational database (Azure SQL, database bank_ops, schema dbo)
-- Every table has a primary key: change tracking and LakeFlow Connect need one.
-- Free text and names are NVARCHAR so Arabic is stored correctly.

CREATE TABLE dbo.branches (
    branch_id     VARCHAR(20)   PRIMARY KEY,
    name          NVARCHAR(100) NOT NULL,
    city          VARCHAR(50)   NOT NULL,
    region        VARCHAR(50),
    opening_date  DATE,
    phone         VARCHAR(30)
);

CREATE TABLE dbo.merchant_categories (
    mcc_code         VARCHAR(4)    PRIMARY KEY,
    category_name    VARCHAR(50)   NOT NULL,
    typical_min_sar  DECIMAL(18,2),
    typical_max_sar  DECIMAL(18,2),
    bnpl_eligible    BIT
);

CREATE TABLE dbo.customers (
    customer_id     VARCHAR(20)   PRIMARY KEY,
    full_name       NVARCHAR(100) NOT NULL,
    national_id     VARCHAR(10)   NOT NULL,   -- PII: National ID (1...) or Iqama (2...)
    customer_type   VARCHAR(10),              -- CITIZEN, RESIDENT
    iban            VARCHAR(24)   NOT NULL,   -- PII
    phone           VARCHAR(20),              -- PII
    email           VARCHAR(100),             -- PII
    city            VARCHAR(50),
    home_branch_id  VARCHAR(20),
    join_date       DATE
);

CREATE TABLE dbo.cards (
    card_id           VARCHAR(20)  PRIMARY KEY,
    customer_id       VARCHAR(20)  NOT NULL,
    card_type         VARCHAR(20)  NOT NULL,  -- MADA_DEBIT, CREDIT_CLASSIC, CREDIT_PLATINUM, PREPAID
    card_scheme       VARCHAR(20),            -- mada, Visa, Mastercard
    last4             CHAR(4),                -- never store a full card number
    credit_limit_sar  DECIMAL(18,2),
    issue_date        DATE,
    expiry_date       DATE,
    card_status       VARCHAR(20)             -- ACTIVE, BLOCKED
);

CREATE TABLE dbo.historical_transactions (
    txn_id          VARCHAR(30)   PRIMARY KEY,
    txn_timestamp   DATETIME2,                -- Riyadh local time
    card_id         VARCHAR(20),
    customer_id     VARCHAR(20),
    branch_id       VARCHAR(20),
    channel         VARCHAR(20),              -- POS, APPLE_PAY, ECOM, ATM
    mcc_code        VARCHAR(4),
    merchant_name   NVARCHAR(100),
    merchant_city   VARCHAR(50),
    amount_sar      DECIMAL(18,2),
    currency        CHAR(3),
    status          VARCHAR(20),              -- APPROVED, DECLINED
    decline_reason  VARCHAR(30),
    is_bnpl         BIT,
    instalments     NVARCHAR(MAX)             -- JSON array of 4 instalments, '[]' if none
);

CREATE TABLE dbo.complaints (
    complaint_id         VARCHAR(20)   PRIMARY KEY,
    txn_id               VARCHAR(30),
    customer_id          VARCHAR(20),
    branch_id            VARCHAR(20),
    channel              VARCHAR(20),         -- MOBILE_APP, CALL_CENTER, BRANCH, EMAIL
    complaint_text       NVARCHAR(MAX),       -- Arabic or English
    satisfaction_score   INT,                 -- 1-5
    complaint_timestamp  DATETIME2
);