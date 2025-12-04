

/* -----------------------------------------------------------------------------------------------------------------------------------------
TEAR DOWN TABLES
	DELETE FROM app_base;
	DELETE FROM app_enums;
	DELETE FROM campaign_cc
	DROP TABLE IF EXISTS app_operational_cc;
	DROP TABLE IF EXISTS app_pricing_cc;
	DROP TABLE IF EXISTS app_solicited_cc;
	DROP TABLE IF EXISTS app_transactional_cc;
	DROP TABLE IF EXISTS historical_lookup;
	DROP TABLE IF EXISTS report_results_lookup;
	DROP TABLE IF EXISTS app_contact_address;
	DROP TABLE IF EXISTS app_contact_employment;
	DROP TABLE IF EXISTS app_contact_base;
	DROP TABLE IF EXISTS campaign_cc;
	DROP TABLE IF EXISTS app_base;
	DROP TABLE IF EXISTS app_enums;
-------------------------------------------------------------------------------------------------------------------------------------------- */

/* RESET -----------------------------------------------------------------------------------------------------------------------------------

    DELETE FROM  app_base; -- should cascade
    DBCC CHECKIDENT ('app_base', RESEED, 0);
    DBCC CHECKIDENT ('app_contact_base', RESEED, 0);
	
	DELETE FROM processing_log;
	DBCC CHECKIDENT ('processing_log', RESEED, 0);

	--DELETE FROM app_xml_staging;
	--DELETE FROM  app_base where app_id > 300000
	--DELETE FROM  processing_log where app_id > 300000
-------------------------------------------------------------------------------------------------------------------------------------------- */
select * from app_enums

-- BEWARE THE LOG FILE: shrink, and set to simple recovery while running the xml conversion ------------------------------------------------

	-- Get Filename & shrink
	SELECT TYPE_DESC, NAME, size, max_size, growth, is_percent_growth FROM sys.database_files;
	DBCC SHRINKFILE ('MACQAOperational')
	DBCC SHRINKFILE ('MACQAOperational_log')

	-- Check recovery model
	SELECT name, recovery_model_desc FROM sys.databases WHERE name = 'MACDEVOperational';

	-- Ensure database is in SIMPLE recovery mode for migration
	ALTER DATABASE MACDEVOperational SET RECOVERY SIMPLE;

	-- After migration, switch back if needed
	ALTER DATABASE MACDEVOperational SET RECOVERY FULL;

	
-- PREPARE APP_XML, STAGING, and LOG TABLES -------------------------------------------------------------------------------------------------
	
	-- UPDATE INDEXES ON EXISTING TABLES
	ALTER INDEX ALL ON  application	REBUILD;
	ALTER INDEX ALL ON  app_xml		REBUILD;

	-- Processing Log (error tracking, resumability)
	CREATE TABLE processing_log (
		log_id				int				NOT NULL CONSTRAINT PK_processing_log_log_id PRIMARY KEY IDENTITY(1, 1),
		app_id				int				NOT NULL,
		[status]			varchar(20)		NOT NULL,
		failure_reason		varchar(500)	NULL,
		processing_time		datetime2(7)	NOT NULL CONSTRAINT DF_processing_log_processing_time DEFAULT GETUTCDATE(),
		[session_id]		varchar(50)		NULL,
		app_id_start		int				NULL, 
		app_id_end			int				NULL
	);

	-- On processing_log  
	CREATE NONCLUSTERED INDEX IX_processing_log_app_id 
		ON processing_log(app_id);

	-- This is used to for an XML fragment of "/Provenir/Request/CustData" to speed up load time
	CREATE TABLE app_xml_staging (
	  app_id		int				NOT NULL PRIMARY KEY,	-- IDENTITY not needed
	  app_XML		varchar(MAX)		NULL,
	  extracted_at	datetime2		NOT NULL DEFAULT (SYSUTCDATETIME())
	);
	
	-- For getting batches of xml
	CREATE NONCLUSTERED INDEX IX_app_xml_staging_app_id ON app_xml_staging (app_id) INCLUDE (app_xml);


	-- LOAD UP!
	-- python .\env_prep\appxml_staging_extractor.py --batch 500 --limit 100 --source-table app_XML --source-column  app_XML --metrics metrics\appxml_w0.json

	-- and xml staging table after it's loaded up
	ALTER INDEX ALL ON  app_xml_staging		REBUILD;


-- INSPECT -----------------------------------------------------------------------------------------------------------------------

SELECT COUNT(*) FROM app_base;
SELECT MAX(app_id) FROM app_base;
SELECT COUNT(*) FROM processing_log;
select * from processing_log where status <> 'success'
SELECT COUNT(*) FROM app_xml
SELECT COUNT(*) FROM app_xml_staging;

select top 100 app_id, cast(app_xml as xml) as xml from app_xml_staging where app_id in (326213)


SELECT TOP 10 app_id, CAST(app_xml AS xml) AS XML 
FROM app_xml_staging 
WHERE app_id = 124294
ORDER BY app_id DESC

SELECT app_id FROM [application] WHERE app_id = 124294
UNION
SELECT app_id FROM IL_application WHERE app_id = 124294

-- DELETE FROM app_xml_staging



-- THIS IS INCLUDED IN APP XML STAGING SCRIPT ------------------------------------------------------------------------------------
-- FIND ORPHANED XML (not joined to application or IL_application): some is hard-erroring in SQL as "illegal xml character"
	SELECT app_id --, CAST(app_xml AS xml) AS XML
	FROM app_XML
	WHERE app_id NOT IN (
		SELECT app_id FROM [application]
		UNION
		SELECT app_id FROM IL_application 
		)
	ORDER BY app_id

-- I DON'T WANT TO SEE A WARNING ABOUT EVERY REC LENDING APPLICATION WHEN RUNNING THE MIGRATOR ----------------------------------
-- Probably should do this on the `appxml_staging_extractor.py` if that's how we're going to implement it, but for now...
-- JUST FREAKING REMOVE THE REC LENDING APPS, WE CAN RE-STAGE WHEN WE DO THE RL PRODUCT LINE
	select count(*)
	--delete
	from app_xml_staging
	where 
		cast(app_XML as xml).value('(/Provenir/Request/CustData/application/@app_receive_date)[1]', 'varchar(20)') IS NULL
