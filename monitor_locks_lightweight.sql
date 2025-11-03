-- ========================================================================
-- LIGHTWEIGHT LOCK MONITOR - MINIMAL PERFORMANCE IMPACT
-- ========================================================================
-- Ultra-fast monitoring queries that won't affect batch processing performance
-- Uses only the most efficient DMVs with minimal overhead
-- ========================================================================

USE XmlConversionDB;
GO

DECLARE @iteration INT = 1;

WHILE 1 = 1
BEGIN
    PRINT 'Lock Monitor #' + CAST(@iteration AS VARCHAR) + ' - ' + CONVERT(VARCHAR, GETDATE(), 121);
    PRINT '=' + REPLICATE('=', 50);
    
    -- 1. BLOCKING (fastest blocking detection)
    SELECT TOP 5
        blocking_session_id AS [Blocker],
        session_id AS [Blocked], 
        wait_type,
        wait_duration_ms AS [Wait_MS]
    FROM sys.dm_os_waiting_tasks 
    WHERE blocking_session_id > 0
    ORDER BY wait_duration_ms DESC;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No blocking';
    
    -- 2. LOCK COUNTS (super fast aggregation)
    SELECT 
        request_mode AS [Mode],
        COUNT(*) AS [Locks],
        SUM(CASE WHEN request_status = 'WAIT' THEN 1 ELSE 0 END) AS [Waits]
    FROM sys.dm_tran_locks 
    WHERE resource_database_id = DB_ID()
    GROUP BY request_mode
    HAVING COUNT(*) > 10
    ORDER BY [Waits] DESC;
    
    -- 3. ACTIVE PYTHON SESSIONS (minimal session info)
    SELECT 
        session_id AS [SPID],
        SUBSTRING(program_name, 1, 30) AS [Program],
        status AS [Status]
    FROM sys.dm_exec_sessions 
    WHERE session_id > 50 
      AND program_name LIKE '%python%'
    ORDER BY session_id;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No Python sessions';
    
    -- 4. TOP WAITS (only current active waits)
    SELECT TOP 3
        wait_type,
        waiting_tasks_count AS [Tasks]
    FROM sys.dm_os_wait_stats 
    WHERE waiting_tasks_count > 0
      AND wait_type NOT LIKE 'SLEEP%'
      AND wait_type NOT LIKE 'BROKER%'
      AND wait_type NOT LIKE 'CLR%'
    ORDER BY waiting_tasks_count DESC;
    
    PRINT 'Next refresh in 10 seconds (Ctrl+C to stop)';
    PRINT '';
    
    SET @iteration = @iteration + 1;
    WAITFOR DELAY '00:00:10';
END