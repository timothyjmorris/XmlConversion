

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
	CREATE TABLE dbo.processing_log (
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
		ON dbo.processing_log(app_id);

	-- This is used to for an XML fragment of "/Provenir/Request/CustData" to speed up load time
	CREATE TABLE migration.app_xml_staging_rl (
	  app_id		int				NOT NULL PRIMARY KEY,	-- IDENTITY not needed
	  app_XML		varchar(MAX)		NULL,
	  extracted_at	datetime2		NOT NULL DEFAULT (SYSUTCDATETIME())
	);
	
	-- For getting batches of xml
	CREATE NONCLUSTERED INDEX IX_app_xml_staging_rl_app_id ON migration.app_xml_staging_rl (app_id) INCLUDE (app_xml);


	-- LOAD UP!
	-- python .\env_prep\appxml_staging_extractor.py --batch 500 --limit 15000 --source-table app_XML --source-column  app_XML --metrics metrics\appxml_w0.json

	-- and xml staging table after it's loaded up
	ALTER INDEX ALL ON  dbo.app_xml_staging		REBUILD;


-- INSPECT -----------------------------------------------------------------------------------------------------------------------

-- do-over
/*

truncate table dbo.processing_log;
delete from dbo.app_base where product_line_enum = 602;

--truncate table dbo.app_xml_staging_rl


*/

-- 12240
SELECT COUNT(*) FROM dbo.app_xml_staging;
-- 791
SELECT COUNT(*) FROM migration.app_xml_staging;
select top 100 * from migration.app_xml_staging_rl order by app_id desc
SELECT COUNT(*) FROM dbo.processing_log;
SELECT * FROM migration.processing_log where status <> 'success'

SELECT COUNT(*) FROM dbo.app_base;
SELECT MAX(app_id) FROM dbo.app_base;
SELECT COUNT(*) FROM app_xml


select top 100 app_id, cast(app_xml as xml) as xml from dbo.app_xml_staging where app_id in (116101)


SELECT TOP 10 app_id, CAST(app_xml AS xml) AS XML 
FROM dbo.app_xml_staging 
WHERE app_id = 124294
ORDER BY app_id DESC

SELECT app_id FROM [application] WHERE app_id = 124294
UNION
SELECT app_id FROM IL_application WHERE app_id = 124294

-- Did all of the staged xml apps make it in?
	SELECT s.app_id, CAST(x.app_xml AS xml) AS XML
	FROM dbo.app_xml_staging AS s
	LEFT JOIN dbo.app_XML AS x ON x.app_id = s.app_id
	WHERE s.app_id NOT IN (SELECT app_id FROM dbo.app_base)

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
	from migration.app_xml_staging
	where app_id in (select app_id from IL_application)

	select count(*)
	--delete
	from migration.app_xml_staging_rl
	where app_id in (select app_id from application)


-- MIGRATION SCHEMA -----------------------------------------------------
SELECT count(*) FROM migration.app_base where product_line_enum = 602




-- delete from migration.app_base where app_id = 325725
select * from migration.app_base where product_line_enum = 602 --app_id = 325725


select app_id, cast(app_xml as xml) as xml from migration.app_xml_staging_rl where app_id in (326287)

select  top 10 *
from dbo.app_base as a
left join dbo.app_operational_rl as o on o.app_id = a.app_id
left join dbo.app_dealer_rl as d on d.app_id = a.app_id
left join dbo.app_funding_rl as f on f.app_id = a.app_id
left join dbo.app_funding_checklist_rl as cl on cl.app_id = a.app_id
left join dbo.app_funding_contract_rl as ct on ct.app_id = a.app_id
left join dbo.app_pricing_rl as p on p.app_id = a.app_id
left join dbo.app_transactional_rl as t on t.app_id = a.app_id
left join dbo.app_contact_base as c on c.app_id = a.app_id
left join dbo.app_contact_address as ca on ca.con_id = c.con_id
left join dbo.app_contact_employment as ce on ce.con_id = c.con_id
where product_line_enum = 602 --and a.app_id = 326272
order by a.app_id desc

select * from migration.app_contact_address where con_id = 10557
select * from migration.app_contact_employment where con_id = 10557


select top 100 * from migration.app_base where product_line_enum = 600 order by app_id

select top 100 a.app_id, a.receive_date, o.regb_start_date, o.regb_end_date
from migration.app_base as a
inner join migration.app_operational_cc as o on o.app_id = a.app_id
order by a.app_id

select e1.value, coll.* 
from migration.app_collateral_rl  as coll
left join migration.app_enums as e1 on e1.enum_id = coll.collateral_type_enum
where make = 'unknown' or model = 'unknown' or year = '9999'

select * from migration.app_historical_lookup where app_id = 325725
select * from migration.app_report_results_lookup where app_id = 325725
select * from migration.app_policy_exceptions_rl where app_id = 325725
select * from migration.app_warranties_rl where app_id = 325725
select * from migration.scores where app_id = 325725
select * from migration.Indicators where app_id = 325725


-- are we missing mappings for new fsp_email, fsp_fax, fsp_num
-- nothing maps to app_funding_contract_rl.monthly_payment_amount
-- nothing maps to app_funding_rl.validated_finance_charge
