

-- Ensure database is in SIMPLE recovery mode for migration
-- ALTER DATABASE XmlConversionDB SET RECOVERY SIMPLE;

-- After migration, switch back if needed
-- ALTER DATABASE XmlConversionDB SET RECOVERY FULL;

select top 10 app_id, cast(xml as xml) from app_xml order by app_id desc

select top 11 * from  sandbox.app_base              order by app_id desc
select top 11 * from  sandbox.app_operational_cc    order by app_id desc
select top 11 * from  sandbox.app_pricing_cc        order by app_id desc
select top 11 * from  sandbox.app_solicited_cc      order by app_id desc
select top 11 * from  sandbox.app_transactional_cc  order by app_id desc
select top 11 * from  sandbox.contact_base          order by app_id desc
select top 11 * from  sandbox.contact_address       order by con_id desc
select top 11 * from  sandbox.contact_employment    order by con_id desc 

select top 100 * from app_xml where app_id > 10000 and app_id < 11001 order by app_id desc

select * from  sandbox.app_base where app_id > 100 and app_id < 201


select * from sandbox.app_base

select * from app_xml_staging
select count(*) from app_xml;

select max(app_id) from app_xml
select max(app_id) from  sandbox.app_base;

select count(*) from  sandbox.app_base;
select count(*) from  sandbox.app_operational_cc;
select count(*) from  sandbox.app_pricing_cc;
select count(*) from  sandbox.app_solicited_cc;
select count(*) from  sandbox.app_transactional_cc;
select count(*) from  sandbox.contact_base;
select count(*) from  sandbox.contact_address;
select count(*) from  sandbox.contact_employment;
select count(*) from  sandbox.processing_log

select * from  sandbox.processing_log

select * from  sandbox.app_enums

select * from application
insert into application (app_id) values (1),(2),(3),(4),(5),(6),(7),(9),(10)

/* RESET ----------------------------------------------------------------------------------------------------------------------------------------

    DELETE FROM  sandbox.app_base; -- should cascade
    DBCC CHECKIDENT ('sandbox.app_base', RESEED, 0);
    DBCC CHECKIDENT ('sandbox.contact_base', RESEED, 0);
	delete from sandbox.processing_log;

    delete from sandbox.app_base		where app_id > 100 and app_id < 201
	delete from sandbox.processing_log	where app_id > 100 and app_id < 201

    -- DELETE FROM app_xml where app_id > 300000
	DELETE FROM app_xml_staging
	

    EXEC sp_updatestats;
	ALTER INDEX ALL ON  sandbox.app_base REBUILD;
	ALTER INDEX ALL ON  sandbox.app_enums REBUILD;
	ALTER INDEX ALL ON  sandbox.app_operational_cc REBUILD;
	ALTER INDEX ALL ON  sandbox.app_pricing_cc REBUILD;
	ALTER INDEX ALL ON  sandbox.app_solicited_cc REBUILD;
	ALTER INDEX ALL ON  sandbox.app_transactional_cc REBUILD;
	ALTER INDEX ALL ON  app_xml REBUILD;
	ALTER INDEX ALL ON  sandbox.contact_base REBUILD;
	ALTER INDEX ALL ON  sandbox.contact_employment REBUILD;
	ALTER INDEX ALL ON  sandbox.contact_address REBUILD;
	ALTER INDEX ALL ON  sandbox.processing_log REBUILD;


	CREATE TABLE dbo.app_xml_staging (
	  app_id INT NOT NULL PRIMARY KEY,
	  app_XML NVARCHAR(MAX) NULL,
	  extracted_at DATETIME2 NOT NULL DEFAULT (SYSUTCDATETIME())
	);
	CREATE INDEX IX_app_xml_staging_app_id ON dbo.app_xml_staging (app_id);

	-- Get database file names
	SELECT TYPE_DESC, NAME, size, max_size, growth, is_percent_growth FROM sys.database_files;

	DBCC SHRINKFILE ('XmlConversionDB')
	DBCC SHRINKFILE ('XmlConversionDB_log')

---------------------------------------------------------------------------------------------------------------------------------------------- */




SET STATISTICS TIME ON;
-- Include Actual Execution Plan (SSMS: Ctrl-M / Include Actual Plan)
SELECT TOP (500) ax.app_id,
       CAST(ax.[app_XML] AS XML).value('(/Provenir/Request/@ID)[1]', 'nvarchar(max)') AS req_id,
       CAST(ax.[app_XML] AS XML).query('/Provenir/Request/CustData') AS custdata_xml
FROM dbo.app_xml ax
WHERE ax.[app_XML] IS NOT NULL
ORDER BY ax.app_id;

SET STATISTICS TIME ON;
SELECT TOP (500) ax.app_id, ax.[app_XML]
FROM dbo.app_xml ax
WHERE ax.[app_XML] LIKE '%<CustData%'
ORDER BY ax.app_id;
SET STATISTICS TIME OFF;


-- exec sp_who2;
	SELECT session_id, blocking_session_id, command, status, wait_type, wait_time
    FROM sys.dm_exec_requests
    WHERE blocking_session_id IS NOT NULL and session_id > 50
	ORDER BY session_id DESC;

-- Lock Summary
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

-- BLOCKING (fastest blocking detection)
    SELECT TOP 5
        blocking_session_id AS [Blocker],
        session_id AS [Blocked], 
        wait_type,
        wait_duration_ms AS [Wait_MS]
    FROM sys.dm_os_waiting_tasks 
    WHERE blocking_session_id > 0
    ORDER BY wait_duration_ms DESC;

-- Check for Locks ---
	SELECT
		l.resource_type,
		request_mode AS lock_mode,
		--l.resource_description,
		OBJECT_NAME(p.object_id) AS TableName,
		c.name AS ColumnName -- This might not directly give you the locked column, but columns in the affected index
	FROM sys.dm_tran_locks AS l
	INNER JOIN sys.partitions AS p ON l.resource_associated_entity_id = p.hobt_id
	INNER JOIN sys.index_columns AS ic ON p.object_id = ic.object_id AND p.index_id = ic.index_id
	INNER JOIN sys.columns AS c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
	WHERE request_mode IN ('X')
		--l.resource_type IN ('KEY', 'PAGE', 'TABLE', 'DATABASE') 
		--AND request_mode IN ('IX', 'X')
		--l.resource_database_id = DB_ID('XmlConversionDB');


-- Query to get next processing batch
-- Remove the OFFSET / FETCH
-- under load: ~1s (< 300ms w/o load)
SET STATISTICS TIME ON
	
	-- Running in LIMIT mode
	SELECT TOP (500) ax.app_id, ax.[app_XML]
    FROM [dbo].[app_xml_staging] AS ax
    WHERE ax.[app_XML] IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM [sandbox].[processing_log] AS pl
        WHERE pl.app_id = ax.app_id
    )
    ORDER BY ax.app_id

SET STATISTICS TIME OFF

SET STATISTICS TIME ON
	-- Running in app_id RANGE mode
	SELECT 
		TOP (500) ax.app_id, --batch-size
		ax.app_xml 
	FROM app_xml AS ax
	WHERE 
		ax.app_xml IS NOT NULL
		AND ax.app_id > 200000	--app-id-start (should probably default to 1)
		AND ax.app_id <= 300000 --app-id-end (should be required if using --app-id-start)		(this keeps the batch in it's lane to be safe on top of usig TOP)
		AND NOT EXISTS (
			SELECT 1 
			FROM sandbox.processing_log AS pl 
			WHERE pl.app_id = ax.app_id
		)
	ORDER BY ax.app_id;

SET STATISTICS TIME OFF

select * from sandbox.processing_log

DELETE FROM sandbox.processing_log WHERE app_id = 443306
DELETE FROM sandbox.app_base WHERE app_id = 443306

-- Quick check all tables
	SELECT TOP(10) *
	FROM  sandbox.app_base AS a                                               
	LEFT JOIN  sandbox.app_operational_cc AS o ON o.app_id = a.app_id
	LEFT JOIN  sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
	LEFT JOIN  sandbox.app_solicited_cc AS s ON s.app_id = a.app_id
	LEFT JOIN  sandbox.app_transactional_cc AS t ON t.app_id = a.app_id
	LEFT JOIN  sandbox.contact_base AS c ON a.app_id = c.app_id
	LEFT JOIN  sandbox.contact_address AS ca ON ca.con_id = c.con_id
	LEFT JOIN  sandbox.contact_employment AS ce ON ce.con_id = c.con_id
	--WHERE a.app_id in (154416, 170691, 312916, 325119, 325431, 312437)
	ORDER BY a.app_id DESC
    
	select * from sandbox.contact_base where birth_date is not null

-------------------------------------------------------------------------------------------------------------------------------------------------
-- QUERIES: for new data model being populated by source XML
-------------------------------------------------------------------------------------------------------------------------------------------------
	-- Example getting one application for Credit Card, with the primary address and current employment - as a single row
	SELECT TOP (10) *
	FROM sandbox.app_base AS a
	INNER JOIN sandbox.app_enums AS e1 ON e1.enum_id = a.product_line_enum
	LEFT JOIN sandbox.app_operational_cc AS o ON o.app_id = a.app_id
	LEFT JOIN sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
	LEFT JOIN sandbox.app_solicited_cc AS s ON s.app_id = a.app_id
	LEFT JOIN sandbox.app_transactional_cc AS t ON t.app_id = a.app_id
	INNER JOIN sandbox.campaign_cc AS cam ON cam.campaign_num = p.campaign_num
	INNER JOIN sandbox.contact_base AS c ON c.app_id = a.app_id
	LEFT JOIN sandbox.contact_address AS ca ON ca.con_id = c.con_id AND ca.address_type_enum = 320			-- PRIMARY address
	LEFT JOIN sandbox.contact_employment AS ce ON ce.con_id = c.con_id AND ce.employment_type_enum = 350	-- CURRENT employment
-------------------------------------------------------------------------------------------------------------------------------------------------

SET STATISTICS TIME ON

	SELECT 
		a.app_id, a.app_source_enum, e1.[value] AS app_source, a.app_type_enum AS app_type, e2.[value], a.booked_date, a.decision_enum AS decision, e3.[value], 
		a.decision_date, a.ip_address, a.receive_date, a.retain_until_date, a.sc_multran_booked_date,
		o.assigned_to, o.sc_bank_aba, o.sc_bank_account_num, o.sc_bank_account_type_enum, e4.[value] AS bank_account_type, o.housing_monthly_payment, o.last_updated_by, o.last_updated_date, 
		o.meta_url, o.priority_enum, e5.[value] AS [priority], o.process_enum, e6.[value] AS process, o.regb_end_date, o.regb_start_date, o.sc_ach_amount, 
		o.sc_debit_funding_source_enum, e7.[value] AS debit_funding_source, o.sc_debit_initial_deposit_amount, o.sc_debit_initial_deposit_date, o.sc_debit_nsf_return_date, 
		o.sc_debit_refund_amount, o.sc_debit_refund_date, o.sc_funding_reference, o.signature_flag, o.ssn_match_type_enum, e8.[value] AS ssn_match_type,
		o.status_enum, e9.[value] AS [status], o.verification_source_enum, e10.[value] AS verification_source,
		p.account_number, p.campaign_num, p.card_art_code, p.credit_line, p.credit_line_max, p.credit_line_possible, p.debt_to_income_ratio, 
		p.decision_model_enum, e11.[value] AS decision_model, p.marketing_segment, p.monthly_debt, p.monthly_income, p.min_payment_due, p.sc_multran_account_num, 
		p.population_assignment_enum, e12.[value] AS population_assignment, p.pricing_tier, p.solicitation_num,
		t.*,
		c.con_id, c.birth_date, c.cell_phone, c.contact_type_enum, e13.[value] AS contact_type, c.email, c.esign_consent_flag, UPPER(c.first_name) AS first_name, 
		c.fraud_type_enum, e14.[value] AS fraud_type, c.home_phone, UPPER(c.last_name) AS last_name, UPPER(c.middle_initial) AS middle_initial, 
		UPPER(c.mother_maiden_name) AS mother_maiden_name, c.paperless_flag, c.sms_consent_flag, c.ssn, UPPER(c.suffix) AS suffix,
		ca.address_type_enum, e15.[value] AS address_type, ca.city, ca.ownership_type_enum, ca.po_box, ca.rural_route, ca.[state], ca.street_name, 
		UPPER(ca.street_number) AS street_number, ca.unit, ca.zip,
		ce.con_id, ce.city, ce.business_name, ce.employment_type_enum, e16.[value] AS employment_type, ce.income_source_nontaxable_flag, ce.income_type_enum, 
		e17.[value] AS income_type, ce.job_title, ce.monthly_salary, ce.months_at_job, ce.other_monthly_income, ce.other_income_type_enum, e15.[value] AS other_income_type,
		ce.other_income_source_detail, ce.phone, ce.self_employed_flag, ce.[state], UPPER(ce.street_name) AS street_name, ce.street_number, ce.unit, ce.zip
	FROM  sandbox.app_base AS a
	LEFT JOIN  sandbox.app_enums AS e1 ON e1.enum_id = a.app_source_enum
	LEFT JOIN  sandbox.app_enums AS e2 ON e2.enum_id = a.app_type_enum
	LEFT JOIN  sandbox.app_enums AS e3 ON e3.enum_id = a.decision_enum
	LEFT JOIN  sandbox.app_operational_cc AS o ON o.app_id = a.app_id
	LEFT JOIN  sandbox.app_enums AS e4 ON e4.enum_id = o.sc_bank_account_type_enum
	LEFT JOIN  sandbox.app_enums AS e5 ON e5.enum_id = o.priority_enum
	LEFT JOIN  sandbox.app_enums AS e6 ON e6.enum_id = o.process_enum
	LEFT JOIN  sandbox.app_enums AS e7 ON e7.enum_id = o.sc_debit_funding_source_enum
	LEFT JOIN  sandbox.app_enums AS e8 ON e8.enum_id = o.ssn_match_type_enum
	LEFT JOIN  sandbox.app_enums AS e9 ON e9.enum_id = o.status_enum
	LEFT JOIN  sandbox.app_enums AS e10 ON e10.enum_id = o.verification_source_enum
	LEFT JOIN  sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
	LEFT JOIN  sandbox.app_enums AS e11 ON e11.enum_id = p.decision_model_enum
	LEFT JOIN  sandbox.app_enums AS e12 ON e12.enum_id = p.population_assignment_enum
	LEFT JOIN  sandbox.app_transactional_cc AS t ON t.app_id = a.app_id
	INNER JOIN  sandbox.contact_base AS c ON c.app_id = a.app_id
	LEFT JOIN  sandbox.app_enums AS e13 ON e13.enum_id = c.contact_type_enum
	LEFT JOIN  sandbox.app_enums AS e14 ON e14.enum_id = c.fraud_type_enum
	LEFT JOIN  sandbox.contact_address AS ca ON ca.con_id = c.con_id AND ca.address_type_enum = 320			-- PRIMARY address
	LEFT JOIN  sandbox.app_enums AS e15 ON e15.enum_id = ca.address_type_enum
	LEFT JOIN  sandbox.contact_employment AS ce ON ce.con_id = c.con_id AND ce.employment_type_enum = 350	-- CURRENT employment
	LEFT JOIN  sandbox.app_enums AS e16 ON e16.enum_id = ce.employment_type_enum
	LEFT JOIN  sandbox.app_enums AS e17 ON e17.enum_id = ce.income_type_enum
	LEFT JOIN  sandbox.app_enums AS e18 ON e18.enum_id = ce.other_income_type_enum

	-- USE _enum ID in WHERE clause, not  sandbox.app_enums.value -- otherwise we need all kinds of indexes I think
	-- e.g. use: "WHERE a.decision_enum = 50" vs. "WHERE e3.value = 'APPROVED'"
	WHERE 
		a.product_line_enum = 600 AND -- CC
		a.decision_enum IN (50, 56, 57, 58, 59)
	
	--ORDER BY a.app_id
	--OFFSET 0 ROWS FETCH NEXT 50 ROWS ONLY

SET STATISTICS TIME OFF

-----------------------------------------------------------------------------------------------------------------------------------------------------

-- NEW Dashboard
SET STATISTICS TIME ON
	SELECT 
		a.app_id AS id, a.receive_date AS receiveDate, UPPER(CONCAT(c.first_name, ' ', c.last_name)) AS applicantName, 
		LOWER(o.assigned_to) AS assignedTo, p.campaign_num AS campaign, LOWER(o.last_updated_by) AS updatedBy, 
		o.last_updated_date AS lastUpdated, e2.[value] AS process, 
		CASE
			WHEN (SELECT COUNT(*) FROM Indicators WHERE indicator = 'TU_Doc_Verification' AND value = 'R' AND Indicators.app_id = a.app_id) > 0 
			THEN 'TU Doc'
		ELSE 
			e1.[value]	-- priority
		END AS priority,
		(SELECT TOP (1) isPinned FROM comments WHERE isPinned = 1 AND comments.app_id = a.app_id) AS hasPinnedComments, 
		CASE
			WHEN o.regb_end_date IS NOT NULL THEN DATEDIFF(day, o.regb_start_date, o.regb_end_date)
			WHEN o.regb_start_date IS NOT NULL THEN DATEDIFF(day, o.regb_start_date, GETUTCDATE())
			ELSE 0
		END AS regBDays,
		CASE
			WHEN e2.[value] > '20000' THEN 1
			--WHEN ao.process_enum IN (114, 115, 116, 117) THEN 1	-- completed: 30000, 40000, 99000, 99500
			ELSE 0
		END AS isClosed,
		CASE
			WHEN o.process_enum = 113			THEN 'Approved'
			WHEN o.process_enum = 114			THEN 'Declined'
			WHEN o.process_enum = 115			THEN 'Withdrawn'
			WHEN o.process_enum IN (116, 117)	THEN 'Booked'		
			ELSE 'Pending'
		END AS status, 
		CASE 
			WHEN CAST(DATEDIFF(day, a.receive_date, GETUTCDATE()) AS int) <= 10 THEN 'GREEN'
			WHEN CAST(DATEDIFF(day, a.receive_date, GETUTCDATE()) AS int) > 10 AND CAST(DATEDIFF(day, a.receive_date, GETUTCDATE()) AS int) <= 15 THEN 'YELLOW'
			ELSE 'RED'
		END AS sla,
		CAST(DATEDIFF(day, a.receive_date, GETUTCDATE()) AS int) AS slaDays,
		COUNT(a.app_id) OVER() AS total_count
	FROM  sandbox.app_base AS a                                               
	INNER JOIN  sandbox.app_operational_cc AS o ON o.app_id = a.app_id
	INNER JOIN  sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
	INNER JOIN campaign AS cam ON cam.campaign_num = p.campaign_num
	LEFT JOIN  sandbox.contact_base AS c ON a.app_id = c.app_id 
	LEFT JOIN Indicators AS i ON a.app_id = i.app_id
	LEFT JOIN  sandbox.app_enums AS e1 ON e1.enum_id = o.priority_enum
	LEFT JOIN  sandbox.app_enums AS e2 ON e2.enum_id = o.process_enum
	WHERE (c.contact_type_enum = 281 OR c.contact_type_enum IS NULL)	-- contact type no longer nullable... problem?
		AND p.campaign_num <> 'ORL'
		AND product_line_enum = 600		-- CC
		-- * USING ENUM.VALUE IS FASTER THAN REFERENCING IT BY ENUM.ID AND THE QUERY PLAN LOOKS SO MUCH BETTER * BUT THIS CANNOT BE APPLIED UNIVERSALLY :-(
			-- AND ao.process_enum NOT IN (114, 115, 116, 117)
		AND e2.[value] < '30000'		
		--AND e1.value = 'Step-Up Received'		-- about the same performance: AND o.priority_enum = 82
		--AND o.last_updated_by = 'TIMOTHY.MORRIS@MERRICKBANK.COM'
		--AND (o.assigned_to = '' OR o.assigned_to IS NULL)
		-- Quick Search 'all'
		/*
		AND (CAST(a.app_id AS varchar(12)) = 'MORRIS' OR 
			c.first_name LIKE 'MORRIS%' OR 
			c.last_name LIKE 'MORRIS%' OR 
			c.email LIKE 'MORRIS%' OR 
			c.ssn_last_4 = 'MORRIS')
		*/
		-- Queue Filtering
		/*
		AND a.app_id IN
					(SELECT aq.app_id
					 FROM queue_definitions AS qd
					 INNER JOIN application_queues AS aq ON qd.id = aq.queue_id
					 WHERE [name] = 'Review' AND product = 'cc')
		*/
	--GROUP BY a.app_id, a.receive_date, c.first_name, c.last_name, o.assigned_to, p.campaign_num, o.last_updated_by, o.last_updated_date, e2.[value], o.regb_start_date, o.regb_end_date, e1.[value], o.process_enum
	ORDER BY 
		regBDays DESC, a.receive_date	
		--updatedBy DESC, a.app_id	--a.receive_date DESC, a.app_id	--applicantName DESC, a.app_id
	OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY

	OPTION (USE HINT('QUERY_OPTIMIZER_COMPATIBILITY_LEVEL_150'))	

SET STATISTICS TIME OFF

---------------------------------------------------------------------------------------------------------------------------------------------------------------
/*-------------------------------------------------------------------------------------------------------------------------------------------------------------
-- NEW Dashboard 
[sp_get_cc_applications]

NOTE: we have to get the open/closed ratio right becuase in PRD we only 10k out of 11MM open
 
* MUST USE QUERY_OPTIMIZER_COMPATIBILITY_LEVEL_150 -- or it'll be +8s

	TIMING COMPARISONS
		no filter/sort:		 80ms		vs.		500ms (returns ~10k)	* got same times with sorting as default
		filter: queue		 10ms		vs.		350ms
		filter: unassigned	 80ms		vs.		440ms
		filter: updatedBy	 20ms		vs.		350ms
		filter: priority	 10ms		vs.		330ms
		quicksearch: all	170ms		vs.		400ms

	NOTE:	need to move to just using last 4 SSN or create new ssn_last_6 computed field
			Eliminate corrolated subqueries (one for each row) to CTE once
			Calculated computed values once in CTE (e.g. regB & sla)
			Use set-based operations instead of row-by-row
			Remove group by -- if possible
			in the PROC, conditionally add join when quicksearching
			in the PROC, conditionally add 2 joins to queues instead of subquery
			Add indexes
--------------------------------------------------------------------------------------------------------------------------------------------------------------- */

SET STATISTICS TIME ON;
GO

	WITH BaseApps AS (
		-- Filter to relevant apps first
		SELECT 
			a.app_id,
			a.receive_date,
			a.product_line_enum,
			o.assigned_to,
			o.last_updated_by,
			o.last_updated_date,
			o.priority_enum,
			o.process_enum,
			o.regb_start_date,
			o.regb_end_date,
			p.campaign_num,
			-- Calculate regBDays once in CTE
			CASE
				WHEN o.regb_end_date IS NOT NULL THEN DATEDIFF(day, o.regb_start_date, o.regb_end_date)
				WHEN o.regb_start_date IS NOT NULL THEN DATEDIFF(day, o.regb_start_date, GETUTCDATE())
				ELSE 0
			END AS regBDays,
			-- Calculate slaDays once
			DATEDIFF(day, a.receive_date, GETUTCDATE()) AS slaDays
		FROM  sandbox.app_base AS a
		INNER JOIN  sandbox.app_operational_cc AS o ON o.app_id = a.app_id
		INNER JOIN  sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
		INNER JOIN campaign AS cam ON cam.campaign_num = p.campaign_num
		LEFT JOIN  sandbox.app_enums AS e1 ON e1.enum_id = o.priority_enum
		LEFT JOIN  sandbox.app_enums AS e2 ON e2.enum_id = o.process_enum
		
		-- Uncomment for Queue filtering
		--INNER JOIN application_queues aq ON aq.app_id = a.app_id
		--INNER JOIN queue_definitions qd ON qd.id = aq.queue_id AND qd.[name] = 'Review' AND qd.product = 'cc'
		
		-- Uncomment for Quick-Search filtering
		--LEFT JOIN  sandbox.contact_base AS c_search ON c_search.app_id = a.app_id

		WHERE a.product_line_enum = 600
			AND p.campaign_num <> 'ORL'
			AND e2.[value] < '30000'
			--AND (o.assigned_to = '' OR o.assigned_to IS NULL)
			--AND o.last_updated_by = 'TIMOTHY.MORRIS@MERRICKBANK.COM'
			--AND (o.assigned_to = '' OR o.assigned_to IS NULL)
			--AND e1.value = 'Step-Up Received'		-- about the same performance: AND o.priority_enum = 82
			-- Quick search 'all'
			/*
			AND (
				CAST(a.app_id AS VARCHAR(12)) = 'MORRIS'
				OR c_search.first_name LIKE 'MORRIS%'
				OR c_search.last_name LIKE 'MORRIS%'
				OR c_search.email LIKE 'MORRIS%'
				OR c_search.ssn_last_4 = 'MORRIS'
			)
			*/
	),
	TUDocApps AS (
		-- Check TU Doc indicator once
		SELECT DISTINCT app_id
		FROM Indicators
		WHERE indicator = 'TU_Doc_Verification' 
			AND value = 'R'
	),
	PinnedComments AS (
		-- Check pinned comments once
		SELECT DISTINCT app_id
		FROM comments
		WHERE isPinned = 1
	)
	SELECT 
		base.app_id AS id,
		base.receive_date AS receiveDate,
		UPPER(CONCAT(c.first_name, ' ', c.last_name)) AS applicantName,
		LOWER(base.assigned_to) AS assignedTo,
		base.campaign_num AS campaign,
		LOWER(base.last_updated_by) AS updatedBy,
		base.last_updated_date AS lastUpdated,
		e2.[value] AS process,
		-- Use LEFT JOIN instead of correlated subquery
		CASE WHEN tu.app_id IS NOT NULL THEN 'TU Doc' ELSE e1.[value] END AS priority,
		CASE WHEN pc.app_id IS NOT NULL THEN 1 ELSE 0 END AS hasPinnedComments,
		base.regBDays,
		CASE WHEN e2.[value] > '20000' THEN 1 ELSE 0 END AS isClosed,
		CASE
			WHEN base.process_enum = 113 THEN 'Approved'
			WHEN base.process_enum = 114 THEN 'Declined'
			WHEN base.process_enum = 115 THEN 'Withdrawn'
			WHEN base.process_enum IN (116, 117) THEN 'Booked'
			ELSE 'Pending'
		END AS status,
		CASE 
			WHEN base.slaDays <= 10 THEN 'GREEN'
			WHEN base.slaDays <= 15 THEN 'YELLOW'
			ELSE 'RED'
		END AS sla,
		base.slaDays,
		COUNT(base.app_id) OVER() AS total_count
	FROM BaseApps AS base
	LEFT JOIN  sandbox.contact_base AS c ON base.app_id = c.app_id AND c.contact_type_enum = 281
	LEFT JOIN TUDocApps AS tu ON tu.app_id = base.app_id
	LEFT JOIN PinnedComments pc ON pc.app_id = base.app_id
	LEFT JOIN  sandbox.app_enums AS e1 ON e1.enum_id = base.priority_enum
	LEFT JOIN  sandbox.app_enums AS e2 ON e2.enum_id = base.process_enum
	ORDER BY 
		base.regBDays DESC, base.receive_date
		--updatedBy DESC, base.app_id	--base.receive_date DESC, base.app_id	--applicantName DESC, base.app_id
	OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY

	OPTION (USE HINT('QUERY_OPTIMIZER_COMPATIBILITY_LEVEL_150'))	

SET STATISTICS TIME OFF;
GO

--------------------------------------------------------------------------------------------------------------------------------------------------------------
-- Quick Search - no CTE

SET STATISTICS TIME ON
	SELECT
		a.app_id AS id, UPPER(CONCAT(c.first_name, ' ', c.last_name)) AS [name], a.receive_date AS receiveDate, 
		e1.[value] AS process, e2.[value] AS [status],  p.campaign_num AS campaign,
		(SELECT TOP (1) isPinned FROM comments WHERE isPinned = 1 AND comments.app_id = a.app_id) AS hasPinnedComments,
		COUNT(a.app_id) OVER() AS total_count
	FROM  sandbox.app_base AS a
	INNER JOIN  sandbox.app_operational_cc AS o ON o.app_id = a.app_id
	INNER JOIN  sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
	INNER JOIN  sandbox.contact_base AS c ON c.app_id = a.app_id
	LEFT JOIN  sandbox.app_enums AS e1 ON e1.enum_id = o.process_enum
	LEFT JOIN  sandbox.app_enums AS e2 ON e2.enum_id = o.status_enum
	
	WHERE 
		(c.contact_type_enum = 281 OR c.contact_type_enum IS NULL)	-- contact type no longer nullable... problem?
		AND product_line_enum = 600		-- CC
		--AND (c.home_phone = '8012223333' OR c.cell_phone = '8012223333')
		--AND c.ssn = '131313131'
		--AND c.first_name LIKE '%JOHN%'
		--AND c.last_name LIKE '%TEST%'
		--AND c.first_name LIKE '%KIRNAN%' AND c.last_name LIKE '%MCGUIRE%'
		--AND ssn_last_4 = '6789'		--AND SUBSTRING(c.ssn, LEN(c.ssn) - 3, 4) = '6789' --'1312'
		--AND c.first_name LIKE 'KIRNAN%' AND ssn_last_4 = '6789'
		AND c.first_name LIKE '%KIRNAN%' AND c.last_name LIKE '%MCGUIRE%' AND ssn_last_4 = '6789'
		--AND a.receive_date > '2025-01-01' AND a.receive_date < '2025-08-31' 
		--AND p.campaign_num = 'Z3I' AND a.receive_date > DATEADD(d, -1, '2025-08-19') AND a.receive_date < DATEADD(d, 1, '2025-08-19')
	GROUP BY a.app_id, c.first_name, c.last_name, a.receive_date, e1.[value], e2.[value], p.campaign_num
	ORDER BY a.receive_date DESC	
	OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY

	OPTION (USE HINT('QUERY_OPTIMIZER_COMPATIBILITY_LEVEL_150'))	
	--select * from  sandbox.contact_base where app_id = 3791848
	--update  sandbox.contact_base set first_name='KIRNAN', last_name='MCGUIRE' where con_id = 4238138
SET STATISTICS TIME OFF

-----------------------------------------------------------------------------------------------------------------------------------
/* -----------------------------------------------------------------------------------------------------------------------------------

[sp_search_cc_applications] - 11.1MM in PRD
	TIMING COMPARISONS
		app_id				  0ms
		phone:				  6ms		vs.		300ms (returns 1)
		ssn:				  2ms		vs.		 11ms (returns 1)
		ssn4:				  2ms		vs.		 1.9s (returns 1k)
		phone/first:		  6ms		vs.		180ms (returns 1)		
		first/last4:		  2ms		vs.		220ms (returns 1)	-- variable, really depends on how many results from name (30 - 300ms)
		first/last/ssn4:	  2ms		vs.		340ms (returns 1)	-- variable, really depends on how many results from name (30 - 300ms)
		before/after rec'd:  50ms		vs.		600ms (returns 20k)
		campaign/rec'd:		 20ms		vs.		130ms (returns 130)

		NOTES: use new ssn_last_4 computed column, remove % from beginning of LIKE
----------------------------------------------------------------------------------------------------------------------------------- */

SET STATISTICS TIME ON;
GO
-- FORCE Filter to matching apps FIRST, then get display data (better than correlated subquery in WHERE clause where SQL joins first and creates massive intermediate result sets)
WITH MatchingApps AS (
    SELECT DISTINCT a.app_id, a.receive_date, a.decision_enum, p.campaign_num
    FROM  sandbox.app_base AS a
    INNER JOIN  sandbox.contact_base AS c ON c.app_id = a.app_id 
	INNER JOIN  sandbox.app_pricing_cc AS p ON p.app_id = a.app_id
	WHERE 
		(c.contact_type_enum = 281 OR c.contact_type_enum IS NULL)	-- contact type no longer nullable... problem?
		AND product_line_enum = 600		-- CC
		--AND a.app_id = 3791848
		--AND (c.home_phone = '8012223333' OR c.cell_phone = '8012223333')
		--AND c.ssn = '131313131'
		--AND ssn_last_4 = '3131'		--AND SUBSTRING(c.ssn, LEN(c.ssn) - 3, 4) = '6789' --'1312'
		--AND c.first_name LIKE 'JOHN%' AND (c.home_phone = '8012223333' OR c.cell_phone = '8012223333')
		--AND c.first_name LIKE 'KIRNAN%' AND ssn_last_4 = '6789'
		--AND c.last_name LIKE '%TEST%'
		--AND c.first_name LIKE '%KIRNAN%' AND c.last_name LIKE '%MCGUIRE%'
		--AND c.first_name LIKE 'KIRNAN%' AND c.last_name LIKE 'MCGUIRE%' AND ssn_last_4 = '6789'
		--AND a.receive_date > '2025-08-01' AND a.receive_date < '2025-08-31' 
		AND p.campaign_num = 'Z3I' AND a.receive_date > DATEADD(d, -1, '2025-08-19') AND a.receive_date < DATEADD(d, 1, '2025-08-19')
)
SELECT
    cte.app_id AS id, 
    UPPER(CONCAT(pc.first_name, ' ', pc.last_name)) AS [name], 
    cte.receive_date AS receiveDate, 
    e1.[value] AS process, 
    e2.[value] AS [status],  
	cte.campaign_num AS campaign,
	(SELECT TOP (1) isPinned FROM comments WHERE isPinned = 1 AND comments.app_id = cte.app_id) AS hasPinnedComments,
	COUNT(cte.app_id) OVER() AS total_count
FROM MatchingApps AS cte
INNER JOIN  sandbox.app_operational_cc AS o ON o.app_id = cte.app_id
--INNER JOIN  sandbox.contact_base AS pc ON pc.app_id = cte.app_id AND pc.contact_type_enum = 281
-- Essentially a correlated subquery (executes once per row), works with smaller result-sets only, otherwise use a JOIN for larger expected results
OUTER APPLY (
        SELECT TOP 1 first_name, last_name
        FROM  sandbox.contact_base
        WHERE app_id = cte.app_id AND contact_type_enum = 281
    ) AS pc
LEFT JOIN  sandbox.app_enums AS e1 ON e1.enum_id = o.process_enum
LEFT JOIN  sandbox.app_enums AS e2 ON e2.enum_id = o.status_enum
ORDER BY cte.receive_date DESC
OFFSET 0 ROWS FETCH NEXT 20 ROWS ONLY
OPTION (USE HINT('QUERY_OPTIMIZER_COMPATIBILITY_LEVEL_150'));

SET STATISTICS TIME OFF;
GO
