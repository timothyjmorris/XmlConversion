-- Real-time lock monitoring for production processing
-- Run this in SQL Server Management Studio during processing

USE XmlConversionDB;

-- Monitor active locks every 10 seconds
WHILE 1 = 1
BEGIN
    PRINT 'Lock Monitor - ' + CONVERT(VARCHAR, GETDATE(), 120)
    PRINT '=' + REPLICATE('=', 50)
    
    -- Active blocking sessions
    SELECT 
        'BLOCKING SESSIONS' AS [Type],
        w.blocking_session_id AS [Blocking Session],
        w.session_id AS [Blocked Session],
        w.wait_type,
        w.wait_duration_ms / 1000.0 AS [Wait Time (sec)],
        bs.program_name AS [Blocking Program],
        ws.program_name AS [Blocked Program],
        w.resource_description AS [Resource]
    FROM sys.dm_os_waiting_tasks w
    LEFT JOIN sys.dm_exec_sessions bs ON w.blocking_session_id = bs.session_id
    LEFT JOIN sys.dm_exec_sessions ws ON w.session_id = ws.session_id
    WHERE w.blocking_session_id > 0
    ORDER BY w.wait_duration_ms DESC;
    
    -- Lock counts by type and mode
    SELECT 
        'LOCK SUMMARY' AS [Type],
        resource_type,
        request_mode,
        COUNT(*) AS [Lock Count],
        COUNT(CASE WHEN request_status = 'WAIT' THEN 1 END) AS [Waiting Locks]
    FROM sys.dm_tran_locks
    WHERE resource_database_id = DB_ID()
    GROUP BY resource_type, request_mode
    ORDER BY [Lock Count] DESC;
    
    -- High-contention objects  
    SELECT TOP 10
        'TOP CONTENTION' AS [Type],
        OBJECT_NAME(resource_associated_entity_id, resource_database_id) AS [Object],
        resource_type,
        COUNT(*) AS [Total Locks],
        COUNT(CASE WHEN request_status = 'WAIT' THEN 1 END) AS [Waiting Locks],
        AVG(CASE WHEN request_status = 'WAIT' THEN 1.0 ELSE 0.0 END) * 100 AS [Contention %]
    FROM sys.dm_tran_locks
    WHERE resource_database_id = DB_ID()
        AND resource_associated_entity_id > 0
    GROUP BY resource_associated_entity_id, resource_database_id, resource_type
    HAVING COUNT(*) > 5
    ORDER BY [Contention %] DESC, [Total Locks] DESC;
    
    -- Active sessions processing XML
    SELECT 
        'XML PROCESSORS' AS [Type],
        s.session_id,
        s.program_name,
        ISNULL(r.cpu_time, 0) AS cpu_time,
        ISNULL(r.reads, 0) AS reads,
        ISNULL(r.writes, 0) AS writes,
        ISNULL(r.logical_reads, 0) AS logical_reads,
        ISNULL(r.row_count, 0) AS row_count,
        CASE 
            WHEN r.start_time IS NOT NULL THEN DATEDIFF(second, r.start_time, GETDATE())
            ELSE DATEDIFF(second, s.last_request_start_time, GETDATE())
        END AS [Duration (sec)],
        ISNULL(r.command, 'SLEEPING') AS command,
        ISNULL(r.wait_type, 'N/A') AS wait_type
    FROM sys.dm_exec_sessions s
    LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
    WHERE s.session_id > 50
      AND (s.program_name LIKE '%python%' 
       OR s.program_name LIKE '%production_processor%'
       OR r.command LIKE '%app_xml%'
       OR r.command LIKE '%processing_log%')
    ORDER BY s.session_id;
    
    PRINT ''
    PRINT 'Refreshing in 10 seconds... (Ctrl+C to stop)'
    WAITFOR DELAY '00:00:10'
    
    -- Clear screen for next iteration
    PRINT REPLICATE(CHAR(13) + CHAR(10), 5)
END