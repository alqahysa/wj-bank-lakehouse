-- Run AFTER sql/00_lakeflow_utility_script.sql (Databricks' official utility procedures).
-- Replace alqahtsa with your SQL admin login. Every @User parameter takes the USERNAME.

-- database-level change tracking, 14-day retention
ALTER DATABASE bank_ops
  SET CHANGE_TRACKING = ON (CHANGE_RETENTION = 14 DAYS, AUTO_CLEANUP = ON);

-- table-level change tracking for every table
EXEC dbo.lakeflowSetupChangeTracking    @Tables = 'ALL', @User = 'alqahtsa';

-- change data capture on the database and its tables
EXEC dbo.lakeflowSetupChangeDataCapture @Tables = 'ALL', @User = 'alqahtsa';

-- permissions the LakeFlow Connect user needs
EXEC dbo.lakeflowFixPermissions         @User = 'alqahtsa', @Tables = 'ALL';

-- ---------- checks ----------
SELECT name, is_cdc_enabled FROM sys.databases WHERE name = 'bank_ops';          -- 1

SELECT t.name,
       t.is_tracked_by_cdc,
       CASE WHEN ct.object_id IS NULL THEN 0 ELSE 1 END AS change_tracking_on
FROM sys.tables t
LEFT JOIN sys.change_tracking_tables ct ON ct.object_id = t.object_id
WHERE t.schema_id = SCHEMA_ID('dbo')
  AND t.name IN ('branches', 'merchant_categories', 'customers', 'cards',
                 'historical_transactions', 'complaints');