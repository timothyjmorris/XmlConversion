-- ========================================================================
-- LOCK MONITORING SCRIPT FOR INSERT BATCH ANALYSIS
-- ========================================================================
-- Run this script DURING a batch load to capture lock contention patterns
-- Execute in a separate query window while load_xml_to_db.py is running
-- ========================================================================

-- Option 1: Real-time active locks (run every 2-3 seconds during batch)
-- Shows current locks by process, resource, and lock type
SELECT 
    'LOCKS_DETAIL' AS metric_type,
    GETUTCDATE() AS sample_time,
    l.request_session_id AS spid,
    l.request_mode AS lock_mode,           -- Shared, Exclusive, Intent, etc.
    l.request_status AS lock_status,       -- Granted, Wait, Convert
    l.request_type AS lock_type,           -- LOCK, LATCH, etc.
    OBJECT_NAME(l.resource_associated_entity_id) AS object_name,
    l.resource_description AS resource_detail,
    t.text AS query_text
    
    --s.login_name,
    --s.host_name,
    --s.program_name
FROM sys.dm_tran_locks AS l
LEFT JOIN sys.dm_exec_sessions AS s ON l.request_session_id = s.session_id
LEFT JOIN sys.dm_exec_requests AS r ON l.request_session_id = r.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) AS t
WHERE s.database_id = DB_ID()
  AND l.request_session_id > 50  -- Ignore system sessions
ORDER BY l.request_session_id, l.request_mode DESC;

-- ========================================================================

-- Option 2: Lock waits summary (shows who is blocking whom)
-- Run this to see blocking chains and wait stats
SELECT 
    'BLOCKING_CHAIN' AS metric_type,
    GETUTCDATE() AS sample_time,
    blocking_session_id,
    session_id,
    wait_duration_ms,
    last_wait_type,
    COUNT(*) AS num_blocked_sessions
FROM sys.dm_exec_sessions
WHERE blocking_session_id <> 0
  AND session_id > 50
GROUP BY blocking_session_id, session_id, wait_duration_ms, last_wait_type
ORDER BY blocking_session_id;

-- ========================================================================

-- Option 3: Lock wait statistics (cumulative from last restart)
-- Shows which resources have the most contention over time
SELECT 
    'LOCK_WAIT_STATS' AS metric_type,
    GETUTCDATE() AS sample_time,
    OBJECT_NAME(resource_id) AS object_name,
    lock_type,
    lock_request_count,
    lock_request_time_ms,
    lock_timeout_period_ms,
    lock_dequeue_count
FROM sys.dm_db_index_lock_stats
WHERE database_id = DB_ID()
ORDER BY lock_request_count DESC;

-- ========================================================================

-- Option 4: Worker process activity (shows what each Python worker is doing)
-- Run this to see which SPID corresponds to each worker
SELECT 
    'WORKER_ACTIVITY' AS metric_type,
    GETUTCDATE() AS sample_time,
    s.session_id,
    s.login_name,
    r.command,
    r.status,
    --r.command_type,
    r.cpu_time,
    r.logical_reads,
    r.reads,
    r.writes,
    r.row_count,
    SUBSTRING(t.text, 1, 100) AS query_sample
FROM sys.dm_exec_sessions s
LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) AS t
WHERE s.session_id > 50
  AND (r.session_id IS NOT NULL OR s.last_request_start_time > DATEADD(MINUTE, -5, GETUTCDATE()))
ORDER BY s.session_id;

-- ========================================================================

-- Option 5: Page latches (pre-allocation contention check)
-- If you see high contention here, it indicates page allocation lock contention
SELECT 
    'PAGE_LATCH_STATS' AS metric_type,
    GETUTCDATE() AS sample_time,
    database_id,
    object_id,
    index_id,
    partition_number,
    page_io_latch_wait_count,
    page_io_latch_wait_in_ms,
    page_lock_wait_count,
    page_lock_wait_in_ms
FROM sys.dm_db_page_info_internal()
WHERE database_id = DB_ID()
  AND object_id > 0
  AND (page_io_latch_wait_count > 0 OR page_lock_wait_count > 0)
ORDER BY page_io_latch_wait_count DESC;

-- ========================================================================

-- Option 6: Index fragmentation (check if high-contention tables are fragmented)
-- Fragmented tables + heavy inserts = more lock contention
SELECT 
    'INDEX_FRAGMENTATION' AS metric_type,
    GETUTCDATE() AS sample_time,
    OBJECT_NAME(ips.object_id) AS table_name,
    i.name AS index_name,
    ips.index_type_desc,
    ips.avg_fragmentation_in_percent,
    ips.page_count,
    ips.record_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
INNER JOIN sys.indexes i ON ips.object_id = i.object_id 
    AND ips.index_id = i.index_id
WHERE ips.database_id = DB_ID()
  AND ips.avg_fragmentation_in_percent > 5  -- Only show fragmented indexes
  AND ips.page_count > 1000
ORDER BY ips.avg_fragmentation_in_percent DESC;

-- ========================================================================

-- Option 7: Transaction isolation level check (verify if READ UNCOMMITTED would help)
-- Shows what isolation levels are in use
SELECT 
    'ISOLATION_LEVELS' AS metric_type,
    GETUTCDATE() AS sample_time,
    session_id,
    transaction_isolation_level = 
        CASE transaction_isolation_level
            WHEN 0 THEN 'Unspecified'
            WHEN 1 THEN 'ReadUncommitted'
            WHEN 2 THEN 'ReadCommitted'
            WHEN 3 THEN 'Repeatable Read'
            WHEN 4 THEN 'Serializable'
            WHEN 5 THEN 'Snapshot'
        END,
    --is_user_transaction,
    open_transaction_count
FROM sys.dm_exec_sessions
WHERE session_id > 50;

-- ========================================================================

-- Quick summary query (run this first to get overall picture)
-- Shows if there's any active contention right now
SELECT 
    'SUMMARY' AS metric_type,
    GETUTCDATE() AS sample_time,
    COUNT(DISTINCT r.session_id) AS active_sessions,
    SUM(CASE WHEN l.request_status = 'Wait' THEN 1 ELSE 0 END) AS sessions_waiting,
    SUM(CASE WHEN l.request_status = 'Granted' THEN 1 ELSE 0 END) AS sessions_with_locks,
    --COUNT(DISTINCT OBJECT_NAME(l.resource_associated_entity_id)) AS tables_with_locks,
    COUNT(*) AS total_locks
FROM sys.dm_exec_requests r
FULL OUTER JOIN sys.dm_tran_locks l ON r.session_id = l.request_session_id
WHERE (r.session_id > 50 OR l.request_session_id > 50)
  AND DB_ID() = ISNULL(r.database_id, l.database_id);

-- ========================================================================
-- INTERPRETATION GUIDE
-- ========================================================================
-- 
-- LOCKS_DETAIL:
--   - lock_mode: 'Exclusive' = only one process can hold it (INSERT, UPDATE, DELETE use these)
--   - lock_mode: 'Shared' = multiple readers allowed (SELECT uses this)
--   - lock_status: 'Wait' = this SPID is blocked, waiting for another process
--   - lock_status: 'Granted' = this SPID has the lock
--   - lock_type: 'PAGE' = page-level lock (if many WAITs here during INSERT = page allocation contention)
--   - lock_type: 'RID' = row-level lock (many of these = normal INSERT activity)
--   - lock_type: 'KEY' = key lock on index (few of these during INSERT = good)
--   - lock_type: 'OBJECT' = whole table lock (if present during batch = potential issue)
--
-- BLOCKING_CHAIN:
--   - blocking_session_id > 0 means that SPID is holding a lock
--   - blocking_session_id = 0 means no one is blocking it
--   - If you see a chain where SPID 55 blocks SPID 56 blocks SPID 57, you have cascading waits
--   - High wait_duration_ms = long waits = serious contention
--
-- PAGE_LATCH_STATS (most important for INSERT contention):
--   - High page_io_latch_wait_count = workers are fighting over page allocations
--   - High page_lock_wait_count = workers are fighting over page locks during INSERT
--   - These two together = classic multi-worker INSERT contention
--
-- INDEX_FRAGMENTATION:
--   - > 30% fragmentation = reorganize/rebuild needed (can help reduce lock contention)
--   - But probably not the primary issue in your case (low volume)
--
-- WORKER_ACTIVITY:
--   - status = 'running' = worker is actively executing
--   - status = 'suspended' = worker is blocked, waiting for lock
--   - Correlate session_id with your Python worker PIDs if possible
--
-- ========================================================================
-- RECOMMENDED MONITORING SEQUENCE
-- ========================================================================
-- 
-- 1. Run "Quick summary query" every 5 seconds during batch
--    - Watch for "sessions_waiting" increasing (indicates contention)
--
-- 2. If sessions_waiting > 0, run LOCKS_DETAIL
--    - Identify which SPIDs are waiting and which are blocking
--    - Note the object_name (table name)
--
-- 3. Run BLOCKING_CHAIN to see the exact wait chain
--
-- 4. Run PAGE_LATCH_STATS to check if it's page allocation contention
--    - If this is high = INSERT contention (workers fighting over page allocations)
--    - If this is low = some other locking issue
--
-- 5. Run WORKER_ACTIVITY to correlate with your Python processes
--
-- ========================================================================
