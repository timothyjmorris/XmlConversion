/* --------------------------------------------------------------------------------------------------------------------
-- File: create_tables.sql
-------------------------------------------------------------------------------------------------------------------- */

-- Source table
CREATE TABLE app_xml (
	app_id		int				NOT NULL CONSTRAINT PK_app_xml_app_id PRIMARY KEY IDENTITY(1, 1),
	[xml]       text            NOT NULL
);



-- Groups of static descriptions organized by type
CREATE TABLE app_enums (
	enum_id							smallint		NOT NULL CONSTRAINT PK_app_enums_enum_id PRIMARY KEY,
	[type]							varchar(50)		NOT NULL,	-- purely for human readability, also to create a list if needed
	[value]							varchar(100)	NOT NULL
);

-- Parent table for all application types with general-use columns: these values should be static
CREATE TABLE app_base (
	app_id							int				NOT NULL CONSTRAINT PK_app_base_app_id PRIMARY KEY IDENTITY(1, 1),
	app_source_enum					smallint		NULL	 CONSTRAINT FK_app_base_app_source_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	app_type_enum					smallint		NULL	 CONSTRAINT FK_app_base_app_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	booked_date						datetime		NULL,
	decision_enum					smallint		NULL	 CONSTRAINT FK_app_base_decision_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	decision_date					datetime		NULL,
	funding_date					datetime		NULL,
	ip_address						varchar(39)		NULL,
	product_line_enum				smallint		NOT NULL DEFAULT (600) CONSTRAINT FK_app_base_product_line_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	receive_date					datetime		NOT NULL CONSTRAINT DF_app_base_receive_date DEFAULT GETUTCDATE(),
	retain_until_date				datetime		NULL,
	sc_multran_booked_date			datetime		NULL,
	sub_type_enum					smallint		NULL	 CONSTRAINT FK_app_base_sub_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION
);

-- Extended child application fields are specific to application type, persists, and may be changed
-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table)
CREATE TABLE app_operational_cc (
	app_id							int				NOT NULL CONSTRAINT FK_app_operational_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,
	assigned_to						varchar(80)		NULL,
	auth_user_spouse_flag			bit				NOT NULL CONSTRAINT DF_app_operational_cc_auth_user_spouse_flag DEFAULT (0),
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
	priority_enum					smallint		NULL	 CONSTRAINT FK_app_operational_cc_priority_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	process_enum					smallint		NULL	 CONSTRAINT FK_app_operational_cc_process_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
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
	sc_bank_aba						char(9)			NULL,
	sc_bank_account_num				varchar(17)		NULL,
	sc_bank_account_type_enum		smallint		NULL	 CONSTRAINT FK_app_operational_cc_sc_bank_account_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,	
	sc_debit_funding_source_enum	smallint		NULL	 CONSTRAINT FK_app_operational_cc_sc_debit_funding_source_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	sc_debit_initial_deposit_amount	decimal(12,2)	NULL,
	sc_debit_initial_deposit_date	datetime		NULL,	
	sc_debit_nsf_return_date		datetime		NULL,
	sc_debit_refund_amount			decimal(12,2)	NULL,
	sc_debit_refund_date			datetime		NULL,
	sc_funding_reference			int				NULL,
	signature_flag					bit				NOT NULL CONSTRAINT DF_app_operational_cc_signature_flag DEFAULT (0),
	ssn_match_type_enum				smallint		NULL	 CONSTRAINT FK_app_operational_cc_ssn_match_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	status_enum						smallint		NULL	 CONSTRAINT FK_app_operational_cc_status_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	verification_source_enum		smallint		NULL	 CONSTRAINT FK_app_operational_cc_verification_source_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	CONSTRAINT PK_app_operational_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- "Transactional" values only exist until loan is decisioned (cleaned out by a separate job)
-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table)
CREATE TABLE app_transactional_cc (
	app_id							int				NOT NULL CONSTRAINT FK_app_transactional_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,	
	analyst_review_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_analyst_review_flag DEFAULT (0),
	booking_paused_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_booking_paused_flag DEFAULT (0),
	disclosures_read_flag			bit				NULL	 CONSTRAINT DF_app_transactional_cc_disclosures_read_flag DEFAULT (0),
	duplicate_ssn_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_duplicate_ssn_flag DEFAULT (0),
	[error_message]					varchar(255)	NULL,
	fraud_review_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_fraud_review_flag DEFAULT (0),
	locked_by_user					varchar(80)		NULL,
	pending_verification_flag		bit				NULL	 CONSTRAINT DF_app_transactional_cc_pending_verification_flag DEFAULT (0),
	sc_ach_sent_flag				bit				NULL	 CONSTRAINT DF_app_transactional_cc_sc_ach_sent_flag DEFAULT (0),
	sc_debit_refund_failed_flag		bit				NULL	 CONSTRAINT DF_app_transactional_cc_sc_debit_refund_failed_flag DEFAULT (0),
	supervisor_review_flag			bit				NULL	 CONSTRAINT DF_app_transactional_cc_supervisor_review_flag DEFAULT (0),
	CONSTRAINT PK_app_transactional_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table)
CREATE TABLE app_pricing_cc (
	app_id								int				NOT NULL CONSTRAINT FK_app_pricing_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,	
	account_number						char(16)		NULL,
	campaign_num						varchar(6)		NOT NULL, --CONSTRAINT FK_app_pricing_cc_campaign_num__campaign_campaign_num FOREIGN KEY REFERENCES campaign(campaign_num) ON DELETE NO ACTION,
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
	-- Will have to get this from XML for pop -- and start populating it
	clear_card_flag						bit				NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_clear_card_flag DEFAULT (0),
	credit_line							smallint		NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_credit_line DEFAULT (0),
	credit_line_max						smallint		NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_credit_line_max DEFAULT (0),
	credit_line_possible				smallint		NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_credit_line_possible DEFAULT (0),
	debt_to_income_ratio				decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_debt_to_income_ratio DEFAULT (0),
	decision_model_enum					smallint		NULL	 CONSTRAINT FK_app_pricing_cc_decision_model_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	marketing_segment					varchar(10)		NOT NULL,	
	min_payment_due						decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_min_payment_due DEFAULT (0),
	monthly_debt						decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_monthly_debt DEFAULT (0),
	monthly_income						decimal(12,2)	NULL, --NOT NULL CONSTRAINT DF_app_pricing_cc_monthly_income DEFAULT (0),
	-- Will have to rely on XML for pop -- and maybe a fall-back to have this be 'NOT NULL', because the data is missing this value
	population_assignment_enum			smallint		NOT NULL CONSTRAINT FK_app_pricing_cc_population_assignment_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	pricing_tier						varchar(2)		NOT NULL,
	sc_multran_account_num				varchar(16)		NULL,
	segment_plan_version				varchar(3)		NULL,
	solicitation_num					varchar(15)		NULL,
	special_flag_5						char(1)			NULL,
	special_flag_6						char(1)			NULL,
	special_flag_7						char(1)			NULL,
	special_flag_8						char(1)			NULL,
	CONSTRAINT PK_app_pricing_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- NOTE: app_id is both the FK & PK (not expecting JOINs to this table)
CREATE TABLE app_solicited_cc (
	app_id						int				NOT NULL CONSTRAINT FK_app_solicited_cc_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,	
	birth_date					smalldatetime	NOT NULL,
	city						varchar(50)		NOT NULL,
	first_name					varchar(50)		NOT NULL,
	last_name					varchar(50)		NOT NULL,
	middle_initial				varchar(1)		NULL,
	po_box						varchar(10)		NULL,
	prescreen_fico_grade		char(1)			NULL,
	prescreen_risk_grade		char(1)			NULL,
	rural_route					varchar(10)		NULL,
	ssn							char(9)			NOT NULL,
	[state]						char(2)			NOT NULL,
	street_name					varchar(50)		NULL,
	street_number				varchar(10)		NULL,
	suffix						varchar(10)		NULL,
	unit						varchar(10)		NULL,
	zip							varchar(9)		NOT NULL,	
	CONSTRAINT PK_app_solicited_cc_app_id PRIMARY KEY CLUSTERED (app_id)
);

-- Used as a convenient method to store and retrieve key/value pairs from a report w/o parsing it again 
--	(when it doesn't fit in neatly to a score or an indicator or part of every app)
--	e.g. GIACT_Response, InstantID_Score, VeridQA_Result
CREATE TABLE report_results_lookup (
	app_id						int				NOT NULL CONSTRAINT FK_report_results_lookup_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,	
	[name]						varchar(100)	NOT NULL,
	[value]						varchar(250)	NULL,
	CONSTRAINT PK_report_results_lookup_app_id PRIMARY KEY CLUSTERED (app_id, [name])	-- composite unique PK
);

-- MAC doesn't join on this, it's retained for "old" applications with "retired" fields
CREATE TABLE historical_lookup (
	app_id						int				NOT NULL CONSTRAINT FK_historical_lookup_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,	
	[name]						varchar(100)	NOT NULL,
	-- e.g. original table name
	[source]					varchar(50)		NULL,
	[value]						varchar(250)	NULL,
	CONSTRAINT PK_historical_lookup_app_id PRIMARY KEY CLUSTERED (app_id, [name])	-- composite unique PK
);

-- UC is on con_id & contact_type_enum to prevent duplicates
CREATE TABLE contact_base (
	con_id						int				NOT NULL CONSTRAINT PK_contact_base_con_id PRIMARY KEY IDENTITY(1, 1),
	app_id						int				NOT NULL CONSTRAINT FK_contact_base_app_id__app_base_app_id FOREIGN KEY REFERENCES app_base(app_id) ON DELETE CASCADE,
	birth_date					smalldatetime	NOT NULL,	-- PROBLEM, we have a bunch of NULL AUTHU accounts, before 2008: suggest migrating this to 1900-01-01
	cell_phone					char(10)		NULL,
	contact_type_enum			smallint		NOT NULL CONSTRAINT FK_contact_base_con_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	email						varchar(100)	NULL,
	esign_consent_flag			bit				NOT NULL CONSTRAINT DF_contact_base_esign_consent_flag DEFAULT (0),
	first_name					varchar(50)		NOT NULL,
	fraud_type_enum				smallint		NULL	 CONSTRAINT FK_contact_base_fraud_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	home_phone					char(10)		NULL,
	last_name					varchar(50)		NOT NULL,
	middle_initial				varchar(1)		NULL,
	mother_maiden_name			varchar(50)		NULL,
	paperless_flag				bit				NOT NULL CONSTRAINT DF_contact_base_paperless_flag DEFAULT (0),
	sms_consent_flag			bit				NOT NULL CONSTRAINT DF_contact_base_sms_consent_flag DEFAULT (0),
	ssn							char(9)			NOT NULL,	-- PROBLEM, we have a bunch of NULL AUTHU accounts, before 2008: suggest migrating this to 000000000
	ssn_last_4					AS RIGHT(4, ssn) PERSISTED,	-- Greatly improves SSN_4 searching
	suffix						varchar(10)		NULL,
	CONSTRAINT UC_contact_base_con_id_contact_type_enum UNIQUE (con_id, contact_type_enum)
);

-- NOTE: con_id is both the FK & PK, PK is on con_id & address_type_enum to prevent duplicates
CREATE TABLE contact_address (
	con_id						int				NOT NULL CONSTRAINT FK_contact_address_con_id__contact_base_con_id FOREIGN KEY REFERENCES contact_base(con_id) ON DELETE CASCADE,
	address_line_1				varchar(100)	NULL,
	address_type_enum			smallint		NOT NULL CONSTRAINT FK_contact_address_address_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	city						varchar(50)		NOT NULL,
	months_at_address			smallint		NULL,
	ownership_type_enum			smallint		NULL CONSTRAINT FK_contact_address_ownership_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	po_box						varchar(10)		NULL,
	rural_route					varchar(10)		NULL,
	[state]						char(2)			NOT NULL,
	street_name					varchar(50)		NULL,
	street_number				varchar(10)		NULL,
	unit						varchar(10)		NULL,
	zip							varchar(9)		NOT NULL,
	CONSTRAINT PK_contact_address_con_id_address_type_enum PRIMARY KEY CLUSTERED (con_id, address_type_enum)
);

-- NOTE: con_id is both the FK & PK, PK is on con_id & employment_type_enum to prevent duplicates
CREATE TABLE contact_employment (
	con_id							int				NOT NULL CONSTRAINT FK_contact_employment_con_id__contact_base_con_id FOREIGN KEY REFERENCES contact_base(con_id) ON DELETE CASCADE,
	address_line_1					varchar(100)	NULL,	-- for RL
	city							varchar(50)		NULL,
	business_name					varchar(100)	NULL,	
	employment_type_enum			smallint		NOT NULL CONSTRAINT FK_contact_employment_employment_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,	
	income_source_nontaxable_flag	bit				NULL,	-- RL doesn't have this
	income_type_enum				smallint		NULL	 CONSTRAINT FK_contact_employment_income_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,
	job_title						varchar(100)	NULL,
	monthly_salary					decimal(12,2)	NULL,
	months_at_job					smallint		NULL,
	other_monthly_income			decimal(12,2)	NULL,
	other_income_type_enum			smallint		NULL	 CONSTRAINT FK_contact_employment_other_income_type_enum__app_enums_enum_id FOREIGN KEY REFERENCES app_enums(enum_id) ON DELETE NO ACTION,	
	other_income_source_detail		varchar(50)		NULL,
	phone							char(10)		NULL,	
	self_employed_flag				bit				NOT NULL CONSTRAINT DF_contact_employment_self_employed_flag DEFAULT (0),
	[state]							char(2)			NULL,
	street_name						varchar(50)		NULL,
	street_number					varchar(10)		NULL,
	unit							varchar(10)		NULL,
	zip								varchar(9)		NULL
	CONSTRAINT PK_contact_employment_con_id_employment_type_enum PRIMARY KEY CLUSTERED (con_id, employment_type_enum)
);
