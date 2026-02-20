-- IF NOT EXISTS(SELECT * FROM sys.schemas WHERE name = N'sandbox') EXEC('CREATE SCHEMA [sandbox] AUTHORIZATION [dbo]');

/* -----------------------------------------------------------------------------------------------------------------------------------------
TEAR DOWN TABLES
	DELETE FROM dbo.app_base;
	DELETE FROM dbo.app_enums;
	DELETE FROM dbo.app_campaign_cc
	DROP TABLE IF EXISTS dbo.app_operational_cc;
	DROP TABLE IF EXISTS dbo.app_pricing_cc;
	DROP TABLE IF EXISTS dbo.app_solicited_cc;
	DROP TABLE IF EXISTS dbo.app_transactional_cc;
	DROP TABLE IF EXISTS dbo.app_campaign_cc;

	DROP TABLE IF EXISTS dbo.app_historical_lookup;
	DROP TABLE IF EXISTS dbo.app_report_results_lookup;
	--DROP TABLE IF EXISTS dbo.app_contact_address;
	--DROP TABLE IF EXISTS dbo.app_contact_employment;
	DROP TABLE IF EXISTS dbo.app_contact_base;
	DROP TABLE IF EXISTS dbo.app_base;
	DROP TABLE IF EXISTS dbo.app_enums;
-------------------------------------------------------------------------------------------------------------------------------------------- */

/* -----------------------------------------------------------------------------------------------------------------------------------------
# OVERVIEW FOR NEW OPERATIONAL DATA MODEL USED BY MAC AS THE SOURCE OF TRUTH FOR LOAN APPLICATIONS
	The tables below include central tables that support all products and product-specific tables, which are 
	differentiated by their suffix, e.g. app_base.product_line_enum = 600 (for Credit Card) will also use tables ending with `*_cc`.
	The [sandbox] schema is temporary to support an application upgrade transition. There are many other tables related
	to an application in the [dbo] schema which can be joined on with a related [app_id] column (which remain unchanged by the new data model)
	`Contact` tables are also product agnostic and support the application. Unlike the other tables supporting application (ending with `*_cc`),
	There can be more than one [app_contact_base] table. This table is supported by [app_contact_address] and [contract_employment], which may also 
	have more than one.
-------------------------------------------------------------------------------------------------------------------------------------------- */

/* -----------------------------------------------------------------------------------------------------------------------------------------
Example getting one application for Credit Card, with the primary address and current employment - as a single row
	SELECT TOP (1) *
	FROM dbo.app_base AS a
	INNER JOIN dbo.app_enums AS e1 ON e1.enum_id = a.product_line_enum
	LEFT JOIN dbo.app_operational_cc AS o ON o.app_id = a.app_id
	LEFT JOIN dbo.app_pricing_cc AS p ON p.app_id = a.app_id
	LEFT JOIN dbo.app_solicited_cc AS s ON s.app_id = a.app_id
	LEFT JOIN dbo.app_transactional_cc AS t ON t.app_id = a.app_id
	INNER JOIN dbo.app_campaign_cc AS cam ON cam.campaign_num = p.campaign_num
	INNER JOIN dbo.app_contact_base AS c ON c.app_id = a.app_id
	LEFT JOIN dbo.app_contact_address AS ca ON ca.con_id = c.con_id AND ca.address_type_enum = 320			-- PRIMARY address
	LEFT JOIN dbo.app_contact_employment AS ce ON ce.con_id = c.con_id AND ce.employment_type_enum = 350	-- CURRENT employment
-------------------------------------------------------------------------------------------------------------------------------------------- */



-- SET LOGGING FOR PROCESS SO WE DON'T KILL OURSELVES --------------------------------------------------------------------------------------------
-- Ensure database is in SIMPLE recovery mode for migration
-- ALTER DATABASE XmlConversionDB SET RECOVERY SIMPLE;

-- After migration, switch back if needed
-- ALTER DATABASE XmlConversionDB SET RECOVERY FULL;


---------------------------------------------------------------------------------------------------------------------------------------------------

-- ================================================================================================================================================
--
-- PREPARE FOR XML MIGRATION
--
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

	-- Convert xml to varchar max so we can index
	ALTER TABLE app_XML
		ALTER COLUMN app_XML	varchar(MAX)	NOT NULL;
	-- On filtered index on app_xml

	CREATE NONCLUSTERED INDEX IX_app_xml_app_id_xml 
		ON app_XML(app_id) INCLUDE (app_XML) --WHERE xml IS NOT NULL;

-- ================================================================================================================================================

---------------------------------------------------------------------------------------------------------------------------------------------------
-- Enable the data to lookup up a consistent/static value from a list by storing it's reference id
CREATE TABLE dbo.app_enums (
	enum_id							smallint		NOT NULL CONSTRAINT PK_app_enums_enum_id PRIMARY KEY,
	[type]							varchar(50)		NOT NULL,	-- purely for human readability, could be used to create a list if needed
	[value]							varchar(100)	NOT NULL,	-- the intent is that the name in this field is determined and used by the business
	[description]					varchar(200)	NULL		-- extended information, especially useful if the value is still used in it's abbreviate form, e.g. "HU" vs. "TU FICO 10T"
);

-- Parent table that supports all product types (product_line_enum). These values do not change.
CREATE TABLE dbo.app_base (
	app_id							int				NOT NULL CONSTRAINT PK_app_base_app_id PRIMARY KEY IDENTITY(1, 1),
	app_source_enum					smallint		NULL	 CONSTRAINT FK_app_base_app_source_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	app_type_enum					smallint		NULL	 CONSTRAINT FK_app_base_app_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	booked_date						datetime		NULL,
	decision_enum					smallint		NULL	 CONSTRAINT FK_app_base_decision_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	decision_date					datetime		NULL,
	funding_date					datetime		NULL,
	ip_address						varchar(39)		NULL,
	product_line_enum				smallint		NOT NULL CONSTRAINT FK_app_base_product_line_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	receive_date					datetime		NOT NULL CONSTRAINT DF_app_base_receive_date DEFAULT GETUTCDATE(),
	retain_until_date				datetime		NULL,
	sc_multran_booked_date			datetime		NULL,
	sub_type_enum					smallint		NULL	 CONSTRAINT FK_app_base_sub_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION
);

-- Extended persistent child application fields are specific to application - and may be changed throughout the lifecycle
-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table)
CREATE TABLE dbo.app_operational_cc (
	app_id							int				NOT NULL CONSTRAINT FK_app_operational_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,
	assigned_to						varchar(80)		NULL,
	auth_user_issue_card_flag		bit				NULL,
	auth_user_spouse_flag			bit				NULL,
	backend_fico_grade				char(1)			NULL,
	backend_risk_grade				char(1)			NULL,
	cb_score_factor_code_1			varchar(10)		NULL,
	cb_score_factor_code_2			varchar(10)		NULL,
	cb_score_factor_code_3			varchar(10)		NULL,
	cb_score_factor_code_4			varchar(10)		NULL,
	cb_score_factor_code_5			varchar(10)		NULL,
	cb_score_factor_type_1			varchar(25)		NULL,
	cb_score_factor_type_2			varchar(25)		NULL,
	cb_score_factor_type_3			varchar(25)		NULL,
	cb_score_factor_type_4			varchar(25)		NULL,
	cb_score_factor_type_5			varchar(25)		NULL,
	housing_monthly_payment			decimal(12,2)	NULL,
	last_bureau_pulled_type			varchar(5)		NULL,
	last_updated_by					varchar(80)		NULL,
	last_updated_date				datetime		NULL,
	meta_url						varchar(50)		NULL,
	payment_protection_plan			char(1)			NULL,	-- CONSTRAINT DF_app_operational_cc_payment_protection_plan DEFAULT (0),
	priority_enum					smallint		NULL	 CONSTRAINT FK_app_operational_cc_priority_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	process_enum					smallint		NULL	 CONSTRAINT FK_app_operational_cc_process_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	regb_end_date					datetime		NULL,
	regb_start_date					datetime		NULL	 CONSTRAINT DF_app_operational_cc_regb_start_date DEFAULT GETUTCDATE(),
	risk_model_score_factor_code_1	varchar(10)		NULL,
	risk_model_score_factor_code_2	varchar(10)		NULL,
	risk_model_score_factor_code_3	varchar(10)		NULL,
	risk_model_score_factor_code_4	varchar(10)		NULL,
	risk_model_score_factor_type_1	varchar(25)		NULL,
	risk_model_score_factor_type_2	varchar(25)		NULL,
	risk_model_score_factor_type_3	varchar(25)		NULL,
	risk_model_score_factor_type_4	varchar(25)		NULL,
	sc_ach_amount					decimal(12,2)	NULL,
	sc_bank_aba						varchar(9)			NULL,
	sc_bank_account_num				varchar(17)		NULL,
	sc_bank_account_type_enum		smallint		NULL	 CONSTRAINT FK_app_operational_cc_sc_bank_account_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,	
	sc_debit_funding_source_enum	smallint		NULL	 CONSTRAINT FK_app_operational_cc_sc_debit_funding_source_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	sc_debit_initial_deposit_amount	decimal(12,2)	NULL,
	sc_debit_initial_deposit_date	datetime		NULL,	
	sc_debit_nsf_return_date		datetime		NULL,
	sc_debit_refund_amount			decimal(12,2)	NULL,
	sc_debit_refund_date			datetime		NULL,
	sc_funding_reference			int				NULL,
	signature_flag					bit				NOT NULL CONSTRAINT DF_app_operational_cc_signature_flag DEFAULT (0),
	ssn_match_type_enum				smallint		NULL	 CONSTRAINT FK_app_operational_cc_ssn_match_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	status_enum						smallint		NULL	 CONSTRAINT FK_app_operational_cc_status_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	verification_source_enum		smallint		NULL	 CONSTRAINT FK_app_operational_cc_verification_source_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	CONSTRAINT PK_app_operational_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- Extended child application fields, which are somewhat temporary values that only need to exist until loan is decisioned (can be cleaned out by a separate job)
-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table unless it is from an app)
/*
TODO: 
add xml mapping contract 
	- alloy_tag_list (not implemented)
	- app_pricing_cc.clear_card_flag
*/

CREATE TABLE dbo.app_transactional_cc (
	app_id							int				NOT NULL CONSTRAINT FK_app_transactional_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,	
	alloy_tag_list					varchar(MAX)	NULL,
	analyst_review_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_analyst_review_flag DEFAULT (0),
	billing_tree_response_status	varchar(20)		NULL,
	billing_tree_token				varchar(500)	NULL,
	booking_paused_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_booking_paused_flag DEFAULT (0),
	disclosures_read_flag			bit				NULL	 CONSTRAINT DF_app_transactional_cc_disclosures_read_flag DEFAULT (0),
	duplicate_ssn_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_duplicate_ssn_flag DEFAULT (0),
	[error_message]					varchar(255)	NULL,
	ex_freeze_code					varchar(4)		NULL,
	fraud_review_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_fraud_review_flag DEFAULT (0),
	iovation_blackbox				varchar(MAX)	NULL,
	locked_by_user					varchar(80)	NULL,
	locked_date						datetime		NULL,
	pending_verification_flag		bit				NULL	 CONSTRAINT DF_app_transactional_cc_pending_verification_flag DEFAULT (0),
	provenir_transaction			varchar(40)		NULL,
	sc_ach_sent_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_sc_ach_sent_flag DEFAULT (0),
	sc_debit_refund_failed_flag		bit				NULL	 CONSTRAINT DF_app_transactional_cc_sc_debit_refund_failed_flag DEFAULT (0),
	supervisor_review_flag			bit				NULL	 CONSTRAINT DF_app_transactional_cc_supervisor_review_flag DEFAULT (0),
	CONSTRAINT PK_app_transactional_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- Mail solicitation / Marketing campaign information
CREATE TABLE dbo.app_campaign_cc (
	campaign_num					varchar(6)		NOT NULL CONSTRAINT PK_campaign_campaign_num PRIMARY KEY,
	agreement_num					int				NULL,
	booking_on_flag					bit				NOT NULL CONSTRAINT DF_campaign_booking_on_flag DEFAULT (0),
	in_home_date					date			NULL,	 -- should we not allow nulls and default ancient null dates to 1900-01-01 or something?
	internet_responses_on_flag		bit				NOT NULL CONSTRAINT DF_campaign_internet_responses_on_flag DEFAULT (0),
	letters_on_flag					bit				NOT NULL CONSTRAINT DF_campaign_letters_on_flag DEFAULT (0),
	processing_complete_flag		bit				NOT NULL CONSTRAINT DF_campaign_processing_complete_flag DEFAULT (0),
	processing_expiration_date		date			NULL,	 -- SC & U2FL are nulls for the following dates
	solicitation_expiration_date	date			NULL,	 -- SC is null
	pricing_as_of_date				date			NULL
);


-- Information that drives the pricing and the outcome
-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table unless it is from an app)
CREATE TABLE dbo.app_pricing_cc (
	app_id								int				NOT NULL CONSTRAINT FK_app_pricing_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,	
	account_number						varchar(16)		NULL,
	campaign_num						varchar(6)		NOT NULL CONSTRAINT FK_app_pricing_cc_campaign_num__campaign_campaign_num FOREIGN KEY REFERENCES dbo.app_campaign_cc(campaign_num) ON DELETE NO ACTION,
	card_art_code						varchar(2)		NULL,
	card_account_setup_fee				tinyint			NULL,
	card_additional_card_fee			tinyint			NULL,
	card_annual_fee						decimal(12,2)	NULL,
	card_cash_advance_apr				decimal(5,2)	NULL,
	card_cash_advance_fee				tinyint			NULL,
	card_cash_advance_percent			decimal(5,2)	NULL,
	card_cash_advance_margin_apr		decimal(5,2)	NULL,
	card_foreign_percent				decimal(5,2)	NULL,
	card_intro_cash_advance_apr			decimal(8,5)	NULL,
	card_intro_purchase_apr				decimal(8,5)	NULL,
	card_late_payment_fee				tinyint			NULL,
	card_min_payment_fee				tinyint			NULL,
	card_min_payment_percent			decimal(5,2)	NULL,
	card_min_interest_charge			decimal(5,2)	NULL,
	card_over_limit_fee					tinyint			NULL,
	card_purchase_apr					decimal(5,2)	NULL,
	card_purchase_apr_margin			decimal(5,2)	NULL,
	card_returned_payment_fee			tinyint			NULL,
	clear_card_flag						bit				NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_clear_card_flag DEFAULT (0),
	credit_line							smallint		NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_credit_line DEFAULT (0),
	credit_line_max						smallint		NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_credit_line_max DEFAULT (0),
	credit_line_possible				smallint		NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_credit_line_possible DEFAULT (0),
	debt_to_income_ratio				decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_debt_to_income_ratio DEFAULT (0),
	decision_model_enum					smallint		NULL	 CONSTRAINT FK_app_pricing_cc_decision_model_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	marketing_segment					varchar(10)		NULL,	
	min_payment_due						decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_min_payment_due DEFAULT (0),
	monthly_debt						decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_monthly_debt DEFAULT (0),
	monthly_income						decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_monthly_income DEFAULT (0),
	population_assignment_enum			smallint		NULL	 CONSTRAINT FK_app_pricing_cc_population_assignment_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	pricing_tier						varchar(2)		NULL,
	sc_multran_account_num				varchar(16)		NULL,
	segment_plan_version				varchar(3)		NULL,
	solicitation_num					varchar(15)		NULL,
	special_flag_5						char(1)			NULL,
	special_flag_6						char(1)			NULL,
	special_flag_7						char(1)			NULL,
	special_flag_8						char(1)			NULL,
	CONSTRAINT PK_app_pricing_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);


-- Solicitation information from applicant for Mail Offer
-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table)
CREATE TABLE dbo.app_solicited_cc (
	app_id						int				NOT NULL CONSTRAINT FK_app_solicited_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,	
	birth_date					date			NULL,
	city						varchar(50)		NULL,
	first_name					varchar(50)		NULL,
	last_name					varchar(50)		NULL,
	middle_initial				varchar(1)		NULL,
	po_box						varchar(10)		NULL,
	prescreen_fico_grade		char(1)			NULL,
	prescreen_risk_grade		char(1)			NULL,
	rural_route					varchar(10)		NULL,
	ssn							varchar(9)			NULL,
	[state]						char(2)			NULL,
	street_name					varchar(50)		NULL,
	street_number				varchar(10)		NULL,
	suffix						varchar(10)		NULL,
	unit						varchar(10)		NULL,
	zip							varchar(9)		NULL,	
	CONSTRAINT PK_app_solicited_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- Used as a convenient method to store and retrieve key/value pairs from a report w/o parsing it again 
--	(when it doesn't fit in neatly to a score or an indicator or part of every app)
--	e.g. GIACT_Response, InstantID_Score, VeridQA_Result
CREATE TABLE dbo.app_report_results_lookup (
	app_id						int				NOT NULL CONSTRAINT FK_app_report_results_lookup_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,	
	[name]						varchar(100)	NOT NULL,
	[value]						varchar(250)	NULL,
	-- Value preferred but not enforced from [reports].[source] as a key
	[source_report_key]			varchar(20)		NULL,
	[rowstamp]					datetime		NOT NULL CONSTRAINT DF_app_report_results_lookup_value_rowstamp DEFAULT GETUTCDATE(),
	CONSTRAINT PK_app_report_results_lookup_app_id PRIMARY KEY CLUSTERED (app_id, [name])	-- composite unique PK
);

-- This table is used to retain fields and their values from applications that have "retired" fields (column no longer exists)
-- NOTE: MAC won't operationally join on this
CREATE TABLE dbo.app_historical_lookup (
	app_id						int				NOT NULL CONSTRAINT FK_app_historical_lookup_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,	
	-- column name
	[name]						varchar(100)	NOT NULL,
	-- original table name
	[source]					varchar(50)		NULL,
	-- column value
	[value]						varchar(250)	NULL,
	[rowstamp]					datetime		NOT NULL CONSTRAINT DF_app_historical_lookup_value_rowstamp DEFAULT GETUTCDATE(),
	CONSTRAINT PK_app_historical_lookup_app_id PRIMARY KEY CLUSTERED (app_id, [name])	-- composite unique PK
);

-- Base indentity information on contact. There may be multiple contacts, categorized by contact_type_enum.
-- (Unique Constaint is on con_id & contact_type_enum to prevent duplicates)
CREATE TABLE dbo.app_contact_base (
	con_id						int				NOT NULL CONSTRAINT PK_app_contact_base_con_id PRIMARY KEY IDENTITY(1, 1),
	app_id						int				NOT NULL CONSTRAINT FK_app_contact_base_app_id__app_base_app_id FOREIGN KEY REFERENCES dbo.app_base(app_id) ON DELETE CASCADE,
	birth_date					date			NOT NULL,	-- PROBLEM, we have a bunch of NULL AUTHU accounts, before 2008: suggest migrating this to 1900-01-01
	cell_phone					varchar(10)		NULL,
	contact_type_enum			smallint		NOT NULL CONSTRAINT FK_app_contact_base_con_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	email						varchar(100)	NULL,
	esign_consent_flag			bit				NOT NULL CONSTRAINT DF_app_contact_base_esign_consent_flag DEFAULT (0),
	first_name					varchar(50)		NOT NULL,
	fraud_type_enum				smallint		NULL	 CONSTRAINT FK_app_contact_base_fraud_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	home_phone					varchar(10)		NULL,
	last_name					varchar(50)		NOT NULL,
	middle_initial				varchar(1)		NULL,
	mother_maiden_name			varchar(50)		NULL,
	paperless_flag				bit				NOT NULL CONSTRAINT DF_app_contact_base_paperless_flag DEFAULT (0),
	sms_consent_flag			bit				NOT NULL CONSTRAINT DF_app_contact_base_sms_consent_flag DEFAULT (0),
	ssn							varchar(9)			NOT NULL,	-- PROBLEM, we have a bunch of NULL AUTHU accounts, before 2008: suggest migrating this to 000000000
	ssn_last_4					AS RIGHT(ssn, 4) PERSISTED,	-- Greatly improves SSN_4 searching
	suffix						varchar(10)		NULL,
	CONSTRAINT UC_app_contact_base_con_id_contact_type_enum UNIQUE (con_id, contact_type_enum)
);

-- Extended indentity information on contact for addresses. There may be multiple contacts, categorized by address_type_enum.
-- NOTE: con_id is both the FK & PK, PK is on con_id & address_type_enum to prevent duplicates
CREATE TABLE dbo.app_contact_address (
	con_id						int				NOT NULL CONSTRAINT FK_app_contact_address_con_id__app_contact_base_con_id FOREIGN KEY REFERENCES dbo.app_contact_base(con_id) ON DELETE CASCADE,
	address_line_1				varchar(100)	NULL,
	address_type_enum			smallint		NOT NULL CONSTRAINT FK_app_contact_address_address_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	city						varchar(50)		NULL,
	months_at_address			smallint		NULL,
	ownership_type_enum			smallint		NULL CONSTRAINT FK_app_contact_address_ownership_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	po_box						varchar(10)		NULL,
	rural_route					varchar(10)		NULL,
	[state]						char(2)			NULL,
	street_name					varchar(50)		NULL,
	street_number				varchar(10)		NULL,
	unit						varchar(10)		NULL,
	zip							varchar(9)		NULL,
	CONSTRAINT PK_app_contact_address_con_id_address_type_enum PRIMARY KEY CLUSTERED (con_id, address_type_enum)
);

-- Extended indentity information on contact for employments. There may be multiple employments, categorized by employment_type_enum.
-- NOTE: con_id is both the FK & PK, PK is on con_id & employment_type_enum to prevent duplicates
CREATE TABLE dbo.app_contact_employment (
	con_id							int				NOT NULL CONSTRAINT FK_app_contact_employment_con_id__app_contact_base_con_id FOREIGN KEY REFERENCES dbo.app_contact_base(con_id) ON DELETE CASCADE,
	address_line_1					varchar(100)	NULL,	-- for RL
	city							varchar(50)		NULL,
	business_name					varchar(100)	NULL,	
	employment_type_enum			smallint		NOT NULL CONSTRAINT FK_app_contact_employment_employment_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,	
	income_source_nontaxable_flag	bit				NULL,	-- RL doesn't have this
	income_type_enum				smallint		NULL	 CONSTRAINT FK_app_contact_employment_income_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,
	job_title						varchar(100)	NULL,
	monthly_salary					decimal(12,2)	NULL,
	months_at_job					smallint		NULL,
	other_monthly_income			decimal(12,2)	NULL,
	other_income_type_enum			smallint		NULL	 CONSTRAINT FK_app_contact_employment_other_income_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES dbo.app_enums(enum_id) ON DELETE NO ACTION,	
	other_income_source_detail		varchar(50)		NULL,
	phone							varchar(10)		NULL,	
	self_employed_flag				bit				NOT NULL CONSTRAINT DF_app_contact_employment_self_employed_flag DEFAULT (0),
	[state]							char(2)			NULL,
	street_name						varchar(50)		NULL,
	street_number					varchar(10)		NULL,
	unit							varchar(10)		NULL,
	zip								varchar(9)		NULL
	CONSTRAINT PK_app_contact_employment_con_id_employment_type_enum PRIMARY KEY CLUSTERED (con_id, employment_type_enum)
);
