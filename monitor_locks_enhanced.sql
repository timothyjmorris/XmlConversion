-- ========================================================================
-- ENHANCED REAL-TIME LOCK MONITORING FOR XML PROCESSING
-- ========================================================================
-- Run this in SQL Server Management Studio during batch processing
-- Monitors locks, blocking, performance, and XML processing activity
-- Auto-refreshes every 5 seconds with comprehensive analysis
-- ========================================================================

USE XmlConversionDB;
GO

-- Enhanced continuous lock monitoring with performance metrics
DECLARE @iteration INT = 1;

WHILE 1 = 1
BEGIN
    PRINT '========================================================================';
    PRINT 'XML Processing Lock Monitor - Iteration ' + CAST(@iteration AS VARCHAR) + ' - ' + CONVERT(VARCHAR, GETDATE(), 120);
    PRINT '========================================================================';
    
    -- 1. CRITICAL: Active blocking chains (who is blocking whom)
    PRINT '1. BLOCKING CHAINS (Critical Issues):';
    PRINT '-' + REPLICATE('-', 60);
    
    SELECT 
        'BLOCKING' AS [Alert_Type],
        w.session_id AS [Blocked_SPID],
        w.blocking_session_id AS [Blocker_SPID],
        w.wait_type,
        w.wait_duration_ms AS [Wait_Time_MS],
        w.resource_description AS [Wait_Resource],
        bs.program_name AS [Blocker_Program],
        ws.program_name AS [Blocked_Program],
        SUBSTRING(bt.text, 1, 100) AS [Blocker_SQL],
        SUBSTRING(wt.text, 1, 100) AS [Blocked_SQL]
    FROM sys.dm_os_waiting_tasks w
    LEFT JOIN sys.dm_exec_sessions bs ON w.blocking_session_id = bs.session_id
    LEFT JOIN sys.dm_exec_sessions ws ON w.session_id = ws.session_id
    LEFT JOIN sys.dm_exec_requests br ON w.blocking_session_id = br.session_id
    LEFT JOIN sys.dm_exec_requests wr ON w.session_id = wr.session_id
    OUTER APPLY sys.dm_exec_sql_text(br.sql_handle) bt
    OUTER APPLY sys.dm_exec_sql_text(wr.sql_handle) wt
    WHERE w.blocking_session_id > 0
    ORDER BY w.wait_duration_ms DESC;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No blocking detected';
    PRINT '';

    -- 2. Lock contention summary by resource type
    PRINT '2. LOCK CONTENTION SUMMARY:';
    PRINT '-' + REPLICATE('-', 60);
    
    SELECT 
        l.resource_type AS [Resource_Type],
        l.request_mode AS [Lock_Mode], 
        COUNT(*) AS [Total_Locks],
        SUM(CASE WHEN l.request_status = 'WAIT' THEN 1 ELSE 0 END) AS [Waiting_Locks],
        CAST(AVG(CASE WHEN l.request_status = 'WAIT' THEN 1.0 ELSE 0.0 END) * 100 AS DECIMAL(5,1)) AS [Contention_Pct],
        STRING_AGG(CAST(l.request_session_id AS VARCHAR), ',') AS [Sessions]
    FROM sys.dm_tran_locks l
    WHERE l.resource_database_id = DB_ID()
    GROUP BY l.resource_type, l.request_mode
    HAVING COUNT(*) > 1
    ORDER BY [Waiting_Locks] DESC, [Total_Locks] DESC;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No significant lock contention';
    PRINT '';

    -- 3. High-contention database objects
    PRINT '3. HIGH-CONTENTION OBJECTS:';
    PRINT '-' + REPLICATE('-', 60);
    
    SELECT TOP 10
        ISNULL(OBJECT_NAME(l.resource_associated_entity_id), 'System/Unknown') AS [Object_Name],
        l.resource_type AS [Resource_Type],
        COUNT(*) AS [Total_Locks],
        SUM(CASE WHEN l.request_status = 'WAIT' THEN 1 ELSE 0 END) AS [Waiting_Locks],
        CAST(AVG(CASE WHEN l.request_status = 'WAIT' THEN 1.0 ELSE 0.0 END) * 100 AS DECIMAL(5,1)) AS [Contention_Pct],
        COUNT(DISTINCT l.request_session_id) AS [Concurrent_Sessions]
    FROM sys.dm_tran_locks l
    WHERE l.resource_database_id = DB_ID()
        AND l.resource_associated_entity_id IS NOT NULL
    GROUP BY l.resource_associated_entity_id, l.resource_type
    HAVING COUNT(*) > 3
    ORDER BY [Waiting_Locks] DESC, [Contention_Pct] DESC;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No high-contention objects detected';
    PRINT '';

    -- 4. Active XML processing sessions
    PRINT '4. ACTIVE XML PROCESSING SESSIONS:';
    PRINT '-' + REPLICATE('-', 60);
    
    SELECT 
        s.session_id AS [SPID],
        s.program_name AS [Program],
        ISNULL(r.command, 'SLEEPING') AS [Command],
        ISNULL(r.status, s.status) AS [Status],
        ISNULL(r.cpu_time, 0) AS [CPU_Time_MS],
        ISNULL(r.logical_reads, 0) AS [Logical_Reads], 
        ISNULL(r.writes, 0) AS [Writes],
        ISNULL(r.row_count, 0) AS [Rows_Affected],
        CASE 
            WHEN r.start_time IS NOT NULL THEN DATEDIFF(second, r.start_time, GETDATE())
            ELSE DATEDIFF(second, s.last_request_start_time, GETDATE())
        END AS [Duration_Sec],
        ISNULL(r.wait_type, 'N/A') AS [Wait_Type],
        SUBSTRING(ISNULL(t.text, 'No active query'), 1, 80) AS [Current_SQL]
    FROM sys.dm_exec_sessions s
    LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
    OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
    WHERE s.session_id > 50  -- Exclude system sessions
        AND (
            s.program_name LIKE '%python%' 
            OR s.program_name LIKE '%production_processor%'
            OR EXISTS (
                SELECT 1 FROM sys.dm_tran_locks l 
                WHERE l.request_session_id = s.session_id 
                AND l.resource_database_id = DB_ID()
            )
        )
    ORDER BY [Duration_Sec] DESC, s.session_id;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No XML processing sessions detected';
    PRINT '';

    -- 5. Wait statistics (what processes are waiting for)
    PRINT '5. CURRENT WAIT STATISTICS:';
    PRINT '-' + REPLICATE('-', 60);
    
    SELECT TOP 10
        wait_type AS [Wait_Type],
        waiting_tasks_count AS [Current_Waits],
        wait_time_ms AS [Total_Wait_MS],
        CASE 
            WHEN waiting_tasks_count > 0 THEN wait_time_ms / waiting_tasks_count 
            ELSE 0 
        END AS [Avg_Wait_MS],
        signal_wait_time_ms AS [Signal_Wait_MS]
    FROM sys.dm_os_wait_stats
    WHERE waiting_tasks_count > 0
        AND wait_type NOT IN (
            'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE', 
            'SLEEP_TASK', 'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH',
            'WAITFOR', 'LOGMGR_QUEUE', 'CHECKPOINT_QUEUE', 'REQUEST_FOR_DEADLOCK_SEARCH',
            'XE_TIMER_EVENT', 'BROKER_TO_FLUSH', 'BROKER_TASK_STOP', 'CLR_MANUAL_EVENT',
            'CLR_AUTO_EVENT', 'DISPATCHER_QUEUE_SEMAPHORE', 'FT_IFTS_SCHEDULER_IDLE_WAIT'
        )
    ORDER BY waiting_tasks_count DESC;
    
    IF @@ROWCOUNT = 0 PRINT '✓ No significant waits detected';
    PRINT '';

    -- 6. Performance counters for batch processing
    PRINT '6. BATCH PROCESSING PERFORMANCE:';
    PRINT '-' + REPLICATE('-', 60);
    
    SELECT 
        counter_name AS [Counter],
        instance_name AS [Instance],
        cntr_value AS [Value],
        cntr_type AS [Counter_Type]
    FROM sys.dm_os_performance_counters
    WHERE object_name LIKE '%SQL Server:Databases%'
        AND instance_name = 'XmlConversionDB'
        AND counter_name IN (
            'Transactions/sec',
            'Log Flushes/sec', 
            'Lock Requests/sec',
            'Lock Timeouts/sec',
            'Lock Waits/sec',
            'Deadlocks/sec'
        )
    ORDER BY counter_name;
    
    PRINT '';
    PRINT '========================================================================';
    PRINT 'Iteration ' + CAST(@iteration AS VARCHAR) + ' complete. Next refresh in 5 seconds...';
    PRINT 'Press Ctrl+C to stop monitoring';
    PRINT '========================================================================';
    PRINT '';
    
    SET @iteration = @iteration + 1;
    WAITFOR DELAY '00:00:05';  -- Wait 5 seconds before next iteration
    
    -- Clear previous output for better readability (optional)
    -- PRINT REPLICATE(CHAR(10), 3);
END