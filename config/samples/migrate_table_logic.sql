
/*
ALTER TABLE sandbox.app_contact_base
	DROP COLUMN ssn_last_4;

ALTER TABLE sandbox.app_contact_base
	ADD ssn_last_4 AS RIGHT(ssn, 4);
	
select top 10 * from app_contact_base where len(ssn_last_4) > 1
*/
-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_enums ------------------------------------------------------------------------------------------------------------------------------------
/*
ALTER TABLE dbo.app_operational_cc NOCHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_pricing_cc NOCHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_transactional_cc NOCHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_contact_address NOCHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_contact_employment NOCHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_contact_base NOCHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_base NOCHECK CONSTRAINT ALL;

ALTER TABLE dbo.app_operational_cc CHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_pricing_cc CHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_transactional_cc CHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_contact_address CHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_contact_employment CHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_contact_base CHECK CONSTRAINT ALL;
ALTER TABLE dbo.app_base CHECK CONSTRAINT ALL;
*/

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_base -------------------------------------------------------------------------------------------------------------------------------------

SET IDENTITY_INSERT dbo.app_base ON;

	INSERT INTO dbo.app_base
		(app_id, product_line_enum, app_source_enum, app_type_enum, booked_date, decision_enum, decision_date, ip_address, receive_date, retain_until_date, sc_multran_booked_date)
		SELECT 
			a.app_id, 
			600,
			CASE
				WHEN RTRIM(app_source_ind) = 'I'		THEN 1
				WHEN RTRIM(app_source_ind) = 'M'		THEN 2
				WHEN RTRIM(app_source_ind) = 'T'		THEN 3
				WHEN RTRIM(app_source_ind) = 'U'		THEN 4
				ELSE NULL
			END, 
			CASE
				WHEN RTRIM(app_type_code) = 'ALL'		THEN 20
				WHEN RTRIM(app_type_code) = 'CBC'		THEN 21
				WHEN RTRIM(app_type_code) = 'FPP'		THEN 22
				WHEN RTRIM(app_type_code) = 'GEICO'		THEN 23
				WHEN RTRIM(app_type_code) = 'GPA'		THEN 24
				WHEN RTRIM(app_type_code) = 'GREST'		THEN 25
				WHEN RTRIM(app_type_code) = 'HCOSC'		THEN 26
				WHEN RTRIM(app_type_code) = 'HT1'		THEN 27
				WHEN RTRIM(app_type_code) = 'PCP'		THEN 28
				WHEN RTRIM(app_type_code) = 'PCT'		THEN 29
				WHEN RTRIM(app_type_code) = 'PRODB'		THEN 30
				WHEN RTRIM(app_type_code) = 'REST'		THEN 31
				WHEN RTRIM(app_type_code) = 'SECURE'	THEN 32
				WHEN RTRIM(app_type_code) = 'DIGITAL'	THEN 33
				ELSE NULL
			END, 
			p.booked_date, 
			CASE
				WHEN RTRIM(p.decision_tp_c) = 'APPRV'	THEN 50
				WHEN RTRIM(p.decision_tp_c) = 'DECLN'	THEN 51
				WHEN RTRIM(p.decision_tp_c) = 'DECNC'	THEN 52
				WHEN RTRIM(p.decision_tp_c) = 'FDBIT'	THEN 53
				WHEN RTRIM(p.decision_tp_c) = 'FGIAC'	THEN 54
				WHEN RTRIM(p.decision_tp_c) = 'NOCHK'	THEN 55
				WHEN RTRIM(p.decision_tp_c) = 'NONE'	THEN 56
				WHEN RTRIM(p.decision_tp_c) = 'PDEP'	THEN 57
				WHEN RTRIM(p.decision_tp_c) = 'PDFIN'	THEN 58
				WHEN RTRIM(p.decision_tp_c) = 'PDNVA'	THEN 59
				WHEN RTRIM(p.decision_tp_c) = 'WITHD'	THEN 60
				ELSE NULL
			END, 
			p.decision_date, 
			a.IP_address, 
			CASE 
				WHEN a.app_receive_date IS NULL THEN GETUTCDATE()
				ELSE a.app_receive_date
			END,
			a.retention_date,
			p.multran_booked_date
		FROM application AS a
		LEFT JOIN app_product AS p ON p.app_id = a.app_id;

SET IDENTITY_INSERT dbo.app_base OFF;

-- Reseed table to be next app_id
DECLARE	@max	int	= (SELECT MAX(app_id) FROM dbo.app_base);
DBCC CHECKIDENT ('dbo.app_base', RESEED, @max);

UPDATE STATISTICS dbo.app_base;


-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_operational_cc ---------------------------------------------------------------------------------------------------------------------------

INSERT INTO dbo.app_operational_cc
	(app_id, assigned_to, auth_user_spouse_flag, backend_fico_grade, backend_risk_grade, cb_score_factor_code_1, cb_score_factor_code_2, cb_score_factor_code_3, cb_score_factor_code_4, 
	 cb_score_factor_code_5, cb_score_factor_type_1, cb_score_factor_type_2, cb_score_factor_type_3, cb_score_factor_type_4, cb_score_factor_type_5,
	 sc_bank_aba, sc_bank_account_num, sc_bank_account_type_enum, housing_monthly_payment, last_bureau_pulled_type, last_updated_by, last_updated_date, meta_url, priority_enum, 
	 process_enum, regb_end_date, regb_start_date, sc_ach_amount, sc_debit_funding_source_enum, sc_debit_initial_deposit_amount, 
	 sc_debit_initial_deposit_date, sc_debit_nsf_return_date, sc_debit_refund_amount, sc_debit_refund_date, sc_funding_reference, signature_flag, 
	 ssn_match_type_enum, status_enum, verification_source_enum, payment_protection_plan,
	 risk_model_score_factor_code_1, risk_model_score_factor_code_2, risk_model_score_factor_code_3, risk_model_score_factor_code_4, 
	 risk_model_score_factor_type_1, risk_model_score_factor_type_2, risk_model_score_factor_type_3, risk_model_score_factor_type_4)
	SELECT DISTINCT
		a.app_id, 
		CASE
			WHEN LEN(a.assigned_to) > 0	THEN a.assigned_to
			ELSE NULL
		END AS assigned_to,
		CASE
			WHEN r.auth_user_is_spouse = 'Y'	THEN 1
		END AS auth_user_spouse_flag,
		CASE
			WHEN ap.backend_fico_grade <> '' AND ap.backend_fico_grade IS NOT NULL	THEN ap.backend_fico_grade
			ELSE NULL
		END AS backend_fico_grade,
		CASE
			WHEN ap.backend_risk_grade <> '' AND ap.backend_risk_grade IS NOT NULL	THEN ap.backend_risk_grade
			ELSE NULL
		END AS backend_risk_grade,
		CASE
			WHEN LEN(ap.adverse_actn1_type_cd) > 0	THEN ap.adverse_actn1_type_cd
			ELSE NULL
		END AS cb_score_factor_code_1,
		CASE
			WHEN LEN(ap.adverse_actn2_type_cd) > 0	THEN ap.adverse_actn2_type_cd
			ELSE NULL
		END AS cb_score_factor_code_2,
		CASE
			WHEN LEN(ap.adverse_actn3_type_cd) > 0	THEN ap.adverse_actn3_type_cd
			ELSE NULL
		END AS cb_score_factor_code_3,
		CASE
			WHEN LEN(ap.adverse_actn4_type_cd) > 0	THEN ap.adverse_actn4_type_cd
			ELSE NULL
		END AS cb_score_factor_code_4,
		CASE
			WHEN LEN(ap.adverse_actn5_type_cd) > 0	THEN ap.adverse_actn5_type_cd
			ELSE NULL
		END AS cb_score_factor_code_5,
		-- Derive and interpret historical types that match the corresponding codes - for the onese we are confident about
		CASE 
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.population_assignment = 'BL'	THEN '00Q88'	-- EX FICO 08
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.population_assignment = 'CV'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.population_assignment = 'EV'	THEN 'EV'		-- EX EVS
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.population_assignment = 'JB'	THEN '00227'	-- Nextgen FICO (Precision)
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.population_assignment = 'L2'	THEN '00337'	-- TU L2C
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.population_assignment = 'SO'	THEN '00A9Q'	-- TU FICO 10T			
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'CM'	THEN 'AJ'		-- EX FICO 08			
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'DN'	THEN '00W83'	-- TU FICO 09			
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HD'	THEN '00W83'	-- TU FICO 09
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HE'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HU'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HV'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HW'	THEN 'V4'		-- EX Vantage 4
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'LB'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'SB'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn1_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND ap.decision_model LIKE 'TU%'	THEN '00227'	-- Nextgen FICO catch-all
			-- Secure Card does not have population_assignment, so we set the type based on if it has an obvious V4 code or not
			WHEN ap.adverse_actn1_type_cd LIKE 'V4_%'	AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN 'V4'
			WHEN LEN(ap.adverse_actn1_type_cd) > 0		AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN '00W83'			
			ELSE NULL
		END AS cb_score_factor_type_1,
		-- Derive and interpret historical types that match the corresponding codes - for the onese we are confident about
		CASE 
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.population_assignment = 'BL'	THEN '00Q88'	-- EX FICO 08
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.population_assignment = 'CV'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.population_assignment = 'EV'	THEN 'EV'		-- EX EVS
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.population_assignment = 'JB'	THEN '00227'	-- Nextgen FICO (Precision)
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.population_assignment = 'L2'	THEN '00337'	-- TU L2C
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.population_assignment = 'SO'	THEN '00A9Q'	-- TU FICO 10T			
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'CM'	THEN 'AJ'		-- EX FICO 08			
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'DN'	THEN '00W83'	-- TU FICO 09			
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HD'	THEN '00W83'	-- TU FICO 09
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HE'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HU'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HV'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HW'	THEN 'V4'		-- EX Vantage 4
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'LB'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'SB'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn2_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND ap.decision_model LIKE 'TU%'	THEN '00227'	-- Nextgen FICO catch-all
			-- Secure Card does not have population_assignment, so we set the type based on if it has an obvious V4 code or not
			WHEN ap.adverse_actn2_type_cd LIKE 'V4_%'	AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN 'V4'
			WHEN LEN(ap.adverse_actn2_type_cd) > 0		AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN '00W83'			
			ELSE NULL
		END AS cb_score_factor_type_2,
		-- Derive and interpret historical types that match the corresponding codes - for the onese we are confident about
		CASE 
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.population_assignment = 'BL'	THEN '00Q88'	-- EX FICO 08
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.population_assignment = 'CV'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.population_assignment = 'EV'	THEN 'EV'		-- EX EVS
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.population_assignment = 'JB'	THEN '00227'	-- Nextgen FICO (Precision)
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.population_assignment = 'L2'	THEN '00337'	-- TU L2C
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.population_assignment = 'SO'	THEN '00A9Q'	-- TU FICO 10T			
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'CM'	THEN 'AJ'		-- EX FICO 08			
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'DN'	THEN '00W83'	-- TU FICO 09			
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HD'	THEN '00W83'	-- TU FICO 09
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HE'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HU'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HV'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HW'	THEN 'V4'		-- EX Vantage 4
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'LB'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'SB'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn3_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND ap.decision_model LIKE 'TU%'	THEN '00227'	-- Nextgen FICO catch-all
			-- Secure Card does not have population_assignment, so we set the type based on if it has an obvious V4 code or not
			WHEN ap.adverse_actn3_type_cd LIKE 'V4_%'	AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN 'V4'
			WHEN LEN(ap.adverse_actn3_type_cd) > 0		AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN '00W83'			
			ELSE NULL
		END AS cb_score_factor_type_3,
		-- Derive and interpret historical types that match the corresponding codes - for the onese we are confident about
		CASE 
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.population_assignment = 'BL'	THEN '00Q88'	-- EX FICO 08
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.population_assignment = 'CV'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.population_assignment = 'EV'	THEN 'EV'		-- EX EVS
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.population_assignment = 'JB'	THEN '00227'	-- Nextgen FICO (Precision)
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.population_assignment = 'L2'	THEN '00337'	-- TU L2C
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.population_assignment = 'SO'	THEN '00A9Q'	-- TU FICO 10T			
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'CM'	THEN 'AJ'		-- EX FICO 08			
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'DN'	THEN '00W83'	-- TU FICO 09			
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HD'	THEN '00W83'	-- TU FICO 09
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HE'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HU'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HV'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HW'	THEN 'V4'		-- EX Vantage 4
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'LB'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'SB'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn4_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND ap.decision_model LIKE 'TU%'	THEN '00227'	-- Nextgen FICO catch-all
			-- Secure Card does not have population_assignment, so we set the type based on if it has an obvious V4 code or not
			WHEN ap.adverse_actn4_type_cd LIKE 'V4_%'	AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN 'V4'
			WHEN LEN(ap.adverse_actn4_type_cd) > 0		AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN '00W83'			
			ELSE NULL
		END AS cb_score_factor_type_4,
		-- Derive and interpret historical types that match the corresponding codes - for the onese we are confident about
		CASE 
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.population_assignment = 'BL'	THEN '00Q88'	-- EX FICO 08
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.population_assignment = 'CV'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.population_assignment = 'EV'	THEN 'EV'		-- EX EVS
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.population_assignment = 'JB'	THEN '00227'	-- Nextgen FICO (Precision)
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.population_assignment = 'L2'	THEN '00337'	-- TU L2C
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.population_assignment = 'SO'	THEN '00A9Q'	-- TU FICO 10T			
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'CM'	THEN 'AJ'		-- EX FICO 08			
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'DN'	THEN '00W83'	-- TU FICO 09			
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HD'	THEN '00W83'	-- TU FICO 09
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HE'	THEN 'AJ'		-- EX FICO 08
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HU'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HV'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'HW'	THEN 'V4'		-- EX Vantage 4
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'LB'	THEN '00V60'	-- TU Vantage 4
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND a.population_assignment = 'SB'	THEN 'FT'		-- EX FICO 10T
			WHEN LEN(ap.adverse_actn5_type_cd) > 0 AND a.app_receive_date > '2023-10-11' AND ap.decision_model LIKE 'TU%'	THEN '00227'	-- Nextgen FICO catch-all
			-- Secure Card does not have population_assignment, so we set the type based on if it has an obvious V4 code or not
			WHEN ap.adverse_actn5_type_cd LIKE 'V4_%'	AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN 'V4'
			WHEN LEN(ap.adverse_actn5_type_cd) > 0		AND a.app_receive_date > '2023-10-11'	AND a.app_type_code = 'SECURE'	THEN '00W83'			
			ELSE NULL
		END AS cb_score_factor_type_5,
		CASE
			WHEN LEN(c.banking_aba) > 0	THEN c.banking_aba
			ELSE NULL
		END AS sc_bank_aba,
		CASE
			WHEN LEN(c.banking_account_number) > 0	THEN c.banking_account_number
			ELSE NULL
		END AS sc_bank_account_num,
		CASE
			WHEN RTRIM(c.banking_account_type) = 'C'	THEN 70
			WHEN RTRIM(c.banking_account_type) = 'S'	THEN 71
			ELSE NULL
		END AS sc_bank_account_type_enum,
		CASE
			WHEN ca.residence_monthly_pymnt > 0	THEN ca.residence_monthly_pymnt
			ELSE NULL
		END AS housing_monthly_payment,
		-- Lookup last bureau pulled
		(SELECT TOP (1) [source] 
		FROM reports 
		WHERE 
			[source] IN ('EX', 'TU')
			AND app_id = a.app_id
			GROUP BY id, [source]
			ORDER BY MAX(id) DESC) AS last_bureau_pulled_type,
		a.updated_by,
		a.last_update_time,
		CASE
			WHEN LEN(a.Partner_URL_ID) > 0	THEN a.Partner_URL_ID
			ELSE NULL
		END AS meta_url,
		CASE
			WHEN RTRIM(a.priority) = 'Alloy Error'		THEN 80
			WHEN RTRIM(a.priority) = 'Offline Step-Up'	THEN 81
			WHEN RTRIM(a.priority) = 'Step-Up Received'	THEN 82
			ELSE NULL
		END AS priority_enum,
		CASE
			WHEN RTRIM(a.process) = '00025' THEN 90 
			WHEN RTRIM(a.process) = '00050' THEN 92 
			WHEN RTRIM(a.process) = '00095' THEN 94 
			WHEN RTRIM(a.process) = '00098' THEN 95 
			WHEN RTRIM(a.process) = '00100' THEN 96 
			WHEN RTRIM(a.process) = '00500' THEN 98 
			WHEN RTRIM(a.process) = '01000' THEN 100
			WHEN RTRIM(a.process) = '02000' THEN 102
			WHEN RTRIM(a.process) = '03000' THEN 104
			WHEN RTRIM(a.process) = '03010' THEN 106
			WHEN RTRIM(a.process) = '03100' THEN 107
			WHEN RTRIM(a.process) = '06000' THEN 108
			WHEN RTRIM(a.process) = '07000' THEN 110
			WHEN RTRIM(a.process) = '07500' THEN 112
			WHEN RTRIM(a.process) = '08000' THEN 114
			WHEN RTRIM(a.process) = '09000' THEN 116
			WHEN RTRIM(a.process) = '10900' THEN 118
			WHEN RTRIM(a.process) = '11000' THEN 120
			WHEN RTRIM(a.process) = '12000' THEN 121
			WHEN RTRIM(a.process) = '13000' THEN 122
			WHEN RTRIM(a.process) = '15000' THEN 123
			WHEN RTRIM(a.process) = '20000' THEN 124
			WHEN RTRIM(a.process) = '30000' THEN 126
			WHEN RTRIM(a.process) = '40000' THEN 128
			WHEN RTRIM(a.process) = '99000' THEN 129
			WHEN RTRIM(a.process) = '99500' THEN 130
			ELSE NULL
		END AS process_enum,
		ap.regb_end_date,
		CASE
			WHEN ap.regb_start_date IS NULL OR ap.regb_start_date = '' THEN a.app_receive_date
			ELSE ap.regb_start_date
		END AS regb_start_date,
		CASE
			WHEN a.secure_ach_amount <> '0' AND a.secure_ach_amount <> '' THEN a.secure_ach_amount
			ELSE NULL
		END AS sc_ach_amount,
		CASE
			WHEN RTRIM(a.Debit_Funding_Source) = 'ACH'						THEN 140
			WHEN RTRIM(a.Debit_Funding_Source) = 'Check'					THEN 131
			WHEN RTRIM(a.Debit_Funding_Source) = 'Debit'					THEN 132
			WHEN RTRIM(a.Debit_Funding_Source) = 'Mail CC/MO'				THEN 133
			WHEN RTRIM(a.Debit_Funding_Source) = 'Money Gram'				THEN 134
			WHEN RTRIM(a.Debit_Funding_Source) = 'Money Order'				THEN 135
			WHEN RTRIM(a.Debit_Funding_Source) = 'Online Bill Pay'			THEN 136
			WHEN RTRIM(a.Debit_Funding_Source) = 'Undetermined'				THEN 137
			WHEN RTRIM(a.Debit_Funding_Source) IN ('Western Union', 'WU')	THEN 138
			WHEN RTRIM(a.Debit_Funding_Source) = 'Wire Transfer'			THEN 139
			ELSE NULL
		END AS sc_debit_funding_source_enum,
		CASE
			WHEN a.Debit_Initial_Deposit_amount <> '0' AND a.Debit_Initial_Deposit_amount <> '' THEN a.Debit_Initial_Deposit_amount
			ELSE NULL
		END AS sc_debit_initial_deposit_amount,
		a.Debit_Initial_Deposit_date AS sc_debit_initial_deposit_date,
		a.Debit_NSF_Return_date AS sc_debit_nsf_return_date,
		CASE
			WHEN a.Debit_Refund_amount <> '0' AND a.Debit_Refund_amount <> '' THEN a.Debit_Refund_amount
			ELSE NULL
		END AS sc_debit_refund_amount,
		a.Debit_Refund_date AS sc_debit_refund_date,
		CASE
			WHEN LEN(a.swiftpay_num) > 0 THEN a.swiftpay_num
			ELSE NULL
		END AS sc_funding_reference,
		CASE
			WHEN RTRIM(a.signature_ind) = 'Y' THEN 1
			ELSE 0
		END AS signature_flag,
		CASE
			WHEN RTRIM(a.ssn_match_flag) = 'R' THEN 150
			WHEN RTRIM(a.ssn_match_flag) = 'N' THEN 151
			WHEN RTRIM(a.ssn_match_flag) = 'Y' THEN 152
			ELSE NULL
		END AS ssn_match_type_enum,
		CASE
			WHEN RTRIM(a.status) = 'A' THEN 160
			WHEN RTRIM(a.status) = 'B' THEN 161
			WHEN RTRIM(a.status) = 'C' THEN 162
			WHEN RTRIM(a.status) = 'D' THEN 163
			WHEN RTRIM(a.status) = 'F' THEN 164
			WHEN RTRIM(a.status) = 'P' THEN 165
			WHEN RTRIM(a.status) = 'Q' THEN 166
			WHEN RTRIM(a.status) = 'W' THEN 167
			ELSE NULL
		END AS status_enum,
		CASE
			WHEN RTRIM(a.verification_source) = 'CAL'	THEN 180
			WHEN RTRIM(a.verification_source) = 'CF'	THEN 181
			WHEN RTRIM(a.verification_source) = 'CM'	THEN 182
			WHEN RTRIM(a.verification_source) = 'CTC'	THEN 183
			WHEN RTRIM(a.verification_source) = 'EX'	THEN 184
			WHEN RTRIM(a.verification_source) = 'FDR'	THEN 185
			WHEN RTRIM(a.verification_source) = 'FDW'	THEN 186
			WHEN RTRIM(a.verification_source) = 'KIQ'	THEN 187
			WHEN RTRIM(a.verification_source) = 'LNA'	THEN 188
			WHEN RTRIM(a.verification_source) = 'LNI'	THEN 189
			WHEN RTRIM(a.verification_source) = 'LNQ'	THEN 190
			WHEN RTRIM(a.verification_source) = 'MAC'	THEN 191
			WHEN RTRIM(a.verification_source) = 'ORG'	THEN 192
			WHEN RTRIM(a.verification_source) = 'PCR'	THEN 193
			WHEN RTRIM(a.verification_source) = 'PID'	THEN 194
			WHEN RTRIM(a.verification_source) = 'PWS'	THEN 195
			WHEN RTRIM(a.verification_source) = 'SOL'	THEN 196
			WHEN RTRIM(a.verification_source) = 'TLO'	THEN 197
			WHEN RTRIM(a.verification_source) = 'TU'	THEN 198
			ELSE NULL
		END AS verification_source_enum,
		a.credit_life_ind AS payment_protection_plan,
		CASE
			WHEN LEN(ap.Risk_Model_reason1_tp_c) > 0	THEN ap.Risk_Model_reason1_tp_c
			ELSE NULL
		END AS risk_model_score_factor_code_1, 
		CASE
			WHEN LEN(ap.Risk_Model_reason2_tp_c) > 0	THEN ap.Risk_Model_reason2_tp_c
			ELSE NULL
		END AS risk_model_score_factor_code_2, 
		CASE
			WHEN LEN(ap.Risk_Model_reason3_tp_c) > 0	THEN ap.Risk_Model_reason3_tp_c
			ELSE NULL
		END AS risk_model_score_factor_code_3, 
		CASE
			WHEN LEN(ap.Risk_Model_reason4_tp_c) > 0	THEN ap.Risk_Model_reason4_tp_c
			ELSE NULL
		END AS risk_model_score_factor_code_4,
		CASE 
			WHEN LEN(ap.Risk_Model_reason1_tp_c) > 0 AND a.population_assignment = 'BL'	THEN 'ben_lomond'
			WHEN LEN(ap.Risk_Model_reason1_tp_c) > 0 AND a.population_assignment = 'JB'	THEN 'jupiter_bowl'
			WHEN LEN(ap.Risk_Model_reason1_tp_c) > 0 AND a.population_assignment = 'LB'	THEN 'lightbox'
			WHEN LEN(ap.Risk_Model_reason1_tp_c) > 0 AND a.population_assignment = 'SB'	THEN 'snowbird'
			WHEN LEN(ap.Risk_Model_reason1_tp_c) > 0 AND a.population_assignment = 'SO'	THEN 'solitude'
			ELSE NULL
		END AS risk_model_score_factor_type_1,
		CASE 
			WHEN LEN(ap.Risk_Model_reason2_tp_c) > 0 AND a.population_assignment = 'BL'	THEN 'ben_lomond'
			WHEN LEN(ap.Risk_Model_reason2_tp_c) > 0 AND a.population_assignment = 'JB'	THEN 'jupiter_bowl'
			WHEN LEN(ap.Risk_Model_reason2_tp_c) > 0 AND a.population_assignment = 'LB'	THEN 'lightbox'
			WHEN LEN(ap.Risk_Model_reason2_tp_c) > 0 AND a.population_assignment = 'SB'	THEN 'snowbird'
			WHEN LEN(ap.Risk_Model_reason2_tp_c) > 0 AND a.population_assignment = 'SO'	THEN 'solitude'
			ELSE NULL
		END AS risk_model_score_factor_type_2,
		CASE 
			WHEN LEN(ap.Risk_Model_reason3_tp_c) > 0 AND a.population_assignment = 'BL'	THEN 'ben_lomond'
			WHEN LEN(ap.Risk_Model_reason3_tp_c) > 0 AND a.population_assignment = 'JB'	THEN 'jupiter_bowl'
			WHEN LEN(ap.Risk_Model_reason3_tp_c) > 0 AND a.population_assignment = 'LB'	THEN 'lightbox'
			WHEN LEN(ap.Risk_Model_reason3_tp_c) > 0 AND a.population_assignment = 'SB'	THEN 'snowbird'
			WHEN LEN(ap.Risk_Model_reason3_tp_c) > 0 AND a.population_assignment = 'SO'	THEN 'solitude'
			ELSE NULL
		END AS risk_model_score_factor_type_3,
		CASE 
			WHEN LEN(ap.Risk_Model_reason4_tp_c) > 0 AND a.population_assignment = 'BL'	THEN 'ben_lomond'
			WHEN LEN(ap.Risk_Model_reason4_tp_c) > 0 AND a.population_assignment = 'JB'	THEN 'jupiter_bowl'
			WHEN LEN(ap.Risk_Model_reason4_tp_c) > 0 AND a.population_assignment = 'LB'	THEN 'lightbox'
			WHEN LEN(ap.Risk_Model_reason4_tp_c) > 0 AND a.population_assignment = 'SB'	THEN 'snowbird'
			WHEN LEN(ap.Risk_Model_reason4_tp_c) > 0 AND a.population_assignment = 'SO'	THEN 'solitude'
			ELSE NULL
		END AS risk_model_score_factor_type_4
	FROM application AS a
	LEFT JOIN app_product AS ap ON ap.app_id = a.app_id
	LEFT JOIN rmts_info AS r ON r.app_id = a.app_id
	--LEFT JOIN contact AS c ON c.app_id = a.app_id AND c.ac_role_tp_c = 'PR'	
	-- SLOW way of de-duping contacts from super bad data in QA (use CTE for serious query)
	LEFT JOIN (
				select app_id, max(con_id) as con_id, coalesce(banking_aba, '') as banking_aba, coalesce(banking_account_number, '') as banking_account_number, coalesce(banking_account_type, '') as banking_account_type from contact where ac_role_tp_c = 'PR' and app_id = 446330 group by app_id, coalesce(banking_aba, ''), coalesce(banking_account_number, ''), coalesce(banking_account_type, '')
	) AS c ON c.app_id = a.app_id
	LEFT JOIN contact_address AS ca ON ca.con_id = c.con_id AND ca.address_tp_c = 'CURR'
	
	-- Should we ALLOW BAD DATA and violate the PK? -- NO DATA LIKE THIS EXIST IN PROD
	WHERE a.app_id NOT IN (7357);	
	/*  -- source of badness:
		select app_id, count(*) as howmany
		from contact
		where ac_role_tp_c = 'PR'
		group by app_id
		having count(*) > 1
	*/

UPDATE STATISTICS dbo.app_operational_cc;


-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_transactional_cc -------------------------------------------------------------------------------------------------------------------------

INSERT INTO dbo.app_transactional_cc
	(app_id, sc_ach_sent_flag, sc_debit_refund_failed_flag, analyst_review_flag, booking_paused_flag, disclosures_read_flag, duplicate_ssn_flag, 
	 fraud_review_flag, pending_verification_flag, supervisor_review_flag)
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN a.secure_ach_sent_flag = 'Y' THEN 1
			ELSE 0
		END,
		CASE
			WHEN a.Debit_Refund_Failed = 'Y' THEN 1
			ELSE 0
		END,
		CASE
			WHEN ap.analyst_rev_ind = 'Y' THEN 1
			ELSE 0
		END,
		CASE
			WHEN ap.booking_paused = 'Y' THEN 1
			ELSE 0
		END,
		CASE
			WHEN ap.disclosures = 'R' THEN 1
			ELSE 0
		END,
		CASE
			WHEN ap.duplicate_app_ind = 'Y' THEN 1
			ELSE 0
		END AS duplicate_ssn_flag,
		CASE
			WHEN ap.fraud_rev_ind = 'Y' THEN 1
			ELSE 0
		END,
		CASE
			WHEN ap.pending_verif_ind = 'Y' THEN 1
			ELSE 0
		END,
		CASE
			WHEN ap.supervisor_rev_ind = 'Y' THEN 1
			ELSE 0
		END
	FROM application AS a
	LEFT JOIN app_product AS ap ON ap.app_id = a.app_id
	WHERE
		LEN(a.secure_ach_sent_flag) > 0 OR
		LEN(a.Debit_Refund_Failed) > 0 OR
		LEN(ap.analyst_rev_ind) > 0 OR
		LEN(ap.booking_paused) > 0 OR
		LEN(ap.disclosures) > 0 OR
		LEN(ap.duplicate_app_ind) > 0 OR
		LEN(ap.fraud_rev_ind) > 0 OR
		LEN(ap.pending_verif_ind) > 0 OR
		LEN(ap.supervisor_rev_ind) > 0;

UPDATE STATISTICS dbo.app_transactional_cc;


-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_pricing_cc -------------------------------------------------------------------------------------------------------------------------------

INSERT INTO dbo.app_pricing_cc
	(app_id, account_number, campaign_num, card_art_code, clear_card_flag, credit_line, credit_line_max, credit_line_possible, debt_to_income_ratio,  
	 decision_model_enum, marketing_segment, monthly_debt, monthly_income, min_payment_due, population_assignment_enum, pricing_tier, solicitation_num, 
	 card_account_setup_fee, card_additional_card_fee, card_annual_fee, card_cash_advance_apr, card_cash_advance_fee, card_cash_advance_percent, card_cash_advance_margin_apr, 
	 card_foreign_percent, card_intro_cash_advance_apr, card_intro_purchase_apr, card_late_payment_fee, card_min_payment_fee, card_min_payment_percent, 
	 card_min_interest_charge, card_over_limit_fee, card_purchase_apr, card_purchase_apr_margin, card_returned_payment_fee, sc_multran_account_num, segment_plan_version,
	 special_flag_5, special_flag_6, special_flag_7, special_flag_8)	
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN ISNUMERIC(pb.account_number) = 1 THEN pb.account_number
			ELSE NULL
		END AS account_number,
		CASE
			WHEN a.campaign_num IS NOT NULL THEN RTRIM(a.campaign_num)
			ELSE 'SC1'
		END AS campaign_num,

		RTRIM(a.special_offer) AS card_art_code,
		-- Need to populate this from XML or infer from other data (marketing segment / special_flag)
		NULL AS clear_card_flag,
		CASE
			WHEN pb.allocated_credit_line > 0 THEN pb.allocated_credit_line
			ELSE NULL
		END AS credit_line,
		CASE
			WHEN pb.max_line > 0 THEN pb.max_line
			ELSE NULL
		END AS credit_line_max,
		CASE
			WHEN pb.credit_line2 > 0 THEN pb.credit_line2
			ELSE NULL
		END AS credit_line_possible,
		CASE
			WHEN p.debt_to_income_ratio > 0 THEN p.debt_to_income_ratio
			ELSE NULL
		END AS debt_to_income_ratio,
		CASE
			WHEN RTRIM(p.decision_model) = 'Classic 08'		THEN 210
			WHEN RTRIM(p.decision_model) = 'EX FICO 08'		THEN 211
			WHEN RTRIM(p.decision_model) = 'EX FICO 10T'	THEN 212
			WHEN RTRIM(p.decision_model) = 'EXVantage4'		THEN 213
			WHEN RTRIM(p.decision_model) = 'TU FICO 09'		THEN 214
			WHEN RTRIM(p.decision_model) = 'TU FICO 10T'	THEN 215
			WHEN RTRIM(p.decision_model) = 'TU Vantage'		THEN 216
			ELSE NULL
		END AS decision_model_enum,
		RTRIM(a.mail_cell_pricing) AS marketing_segment,		
		CASE
			WHEN p.monthly_debt > 0 THEN p.monthly_debt
			ELSE NULL
		END AS monthly_debt,
		CASE
			WHEN p.monthly_income > 0 THEN p.monthly_income
			ELSE NULL
		END AS monthly_income,
		CASE
			WHEN pb.min_pay_due > 0 THEN pb.min_pay_due
			ELSE NULL
		END AS min_payment_due,
		CASE
			WHEN RTRIM(a.population_assignment) = '02'		THEN 230
			WHEN RTRIM(a.population_assignment) = '1'		THEN 231
			WHEN RTRIM(a.population_assignment) = '2'		THEN 232
			WHEN RTRIM(a.population_assignment) = '3'		THEN 233
			WHEN RTRIM(a.population_assignment) = 'BL'		THEN 234
			WHEN RTRIM(a.population_assignment) = 'CM'		THEN 235
			WHEN RTRIM(a.population_assignment) = 'CONTROL'	THEN 236
			WHEN RTRIM(a.population_assignment) = 'DN'		THEN 237
			WHEN RTRIM(a.population_assignment) = 'EV'		THEN 238
			WHEN RTRIM(a.population_assignment) = 'HD'		THEN 239
			WHEN RTRIM(a.population_assignment) = 'HE'		THEN 240
			WHEN RTRIM(a.population_assignment) = 'HOLDOUT' THEN 241
			WHEN RTRIM(a.population_assignment) = 'HU'		THEN 242
			WHEN RTRIM(a.population_assignment) = 'HV'		THEN 243
			WHEN RTRIM(a.population_assignment) = 'HW'		THEN 244
			WHEN RTRIM(a.population_assignment) = 'JB'		THEN 245
			WHEN RTRIM(a.population_assignment) = 'JH'		THEN 246
			WHEN RTRIM(a.population_assignment) = 'L2'		THEN 247
			WHEN RTRIM(a.population_assignment) = 'LB'		THEN 248
			WHEN RTRIM(a.population_assignment) = 'LP'		THEN 249
			WHEN RTRIM(a.population_assignment) = 'SB'		THEN 250
			WHEN RTRIM(a.population_assignment) = 'SO'		THEN 251
			WHEN RTRIM(a.population_assignment) = 'T'		THEN 252
			WHEN RTRIM(a.population_assignment) = 'VIP'		THEN 253
			-- Fallback for missing data so we can preserve 'NOT NULL' for the column
			ELSE 229
		END AS population_assignment_enum,
		RTRIM(a.pricing_tier) AS pricing_tier,
		RTRIM(a.solicitation_num) AS solicitation_num,
		CASE
			WHEN rm.account_setup_fee > 0 THEN rm.account_setup_fee
			ELSE NULL
		END AS card_account_setup_fee,
		CASE
			WHEN rm.additional_card_fee > 0 THEN rm.additional_card_fee
			ELSE NULL
		END AS card_additional_card_fee,
		CASE
			WHEN rm.annual_fee > 0 THEN rm.annual_fee
			ELSE NULL
		END AS card_annual_fee,
		CASE
			WHEN rm.cash_advance_apr > 0 THEN rm.cash_advance_apr
			ELSE NULL
		END AS card_cash_advance_apr,
		CASE
			WHEN rm.cash_advance_fee > 0 THEN rm.cash_advance_apr
			ELSE NULL
		END AS card_cash_advance_fee,
		CASE
			WHEN rm.cash_advance_percent > 0 THEN rm.cash_advance_percent
			ELSE NULL
		END AS card_cash_advance_percent,
		CASE
			WHEN rm.cash_apr_margin > 0 THEN rm.cash_apr_margin
			ELSE NULL
		END AS card_cash_advance_margin_apr,
		CASE
			WHEN rm.foreign_percent > 0 THEN rm.foreign_percent
			ELSE NULL
		END AS card_foreign_percent,
		CASE
			WHEN rm.intro_cash_advance_apr > 0 THEN rm.intro_cash_advance_apr
			ELSE NULL
		END AS card_intro_cash_advance_apr,
		CASE
			WHEN rm.intro_purchase_apr > 0 THEN rm.intro_purchase_apr
			ELSE NULL
		END AS card_intro_purchase_apr,
		CASE
			WHEN rm.late_payment_fee > 0 THEN rm.late_payment_fee
			ELSE NULL
		END AS card_late_payment_fee,
		CASE
			WHEN rm.min_payment_fee > 0 THEN rm.min_payment_fee
			ELSE NULL
		END AS card_min_payment_fee,
		CASE
			WHEN rm.min_payment_percent > 0 THEN rm.min_payment_percent
			ELSE NULL
		END AS card_min_payment_percent,
		CASE
			WHEN rm.minimum_interest_charge > 0 THEN rm.minimum_interest_charge
			ELSE NULL
		END AS card_min_interest_charge,
		CASE
			WHEN rm.over_limit_fee > 0 THEN rm.over_limit_fee
			ELSE NULL
		END AS card_over_limit_fee,
		CASE
			WHEN rm.purchase_apr > 0 THEN rm.purchase_apr
			ELSE NULL
		END AS card_purchase_apr,
		CASE
			WHEN rm.purchase_apr_margin > 0 THEN rm.purchase_apr_margin
			ELSE NULL
		END AS card_purchase_apr_margin,
		CASE
			WHEN rm.returned_payment_fee > 0 THEN rm.returned_payment_fee
			ELSE NULL
		END AS card_returned_payment_fee,
		CASE
			WHEN LEN(pb.multran_account_number) > 0 THEN pb.multran_account_number
			ELSE NULL
		END AS sc_multran_account_num,
		CASE
			WHEN LEN(rm.seg_plan_version) > 0 THEN rm.seg_plan_version
			ELSE NULL
		END AS segment_plan_version,
		rm.special_flag_5,
		rm.special_flag_6,
		rm.special_flag_7,
		rm.special_flag_8
	FROM application AS a
	LEFT JOIN app_product AS p ON p.app_id = a.app_id
	--LEFT JOIN contact AS c ON c.app_id = a.app_id AND c.ac_role_tp_c = 'PR'
	-- SLOW way of de-duping contacts from super bad data in QA (use CTE for serious query)
	LEFT JOIN (
				select app_id, max(con_id) as con_id from contact where ac_role_tp_c = 'PR' and app_id = 446330 group by app_id
			  ) AS c ON c.app_id = a.app_id
	LEFT JOIN app_prod_bcard AS pb ON pb.con_id = c.con_id
	LEFT JOIN rmts_info AS rm ON rm.app_id = a.app_id
	
	-- BAD QA DATA from campaign, so join
	INNER JOIN app_campaign_cc AS ac ON ac.campaign_num = a.campaign_num

	-- Should we ALLOW BAD DATA and violate the PK? -- NO DATA LIKE THIS EXIST IN PROD
	WHERE a.app_id NOT IN (7357);

UPDATE STATISTICS dbo.app_pricing_cc;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_solicited_cc -----------------------------------------------------------------------------------------------------------------------------

INSERT INTO dbo.app_solicited_cc
	(app_id, birth_date, city, first_name, last_name, middle_initial, po_box, prescreen_fico_grade, prescreen_risk_grade, rural_route, ssn, [state], 
	 street_name, street_number, suffix, unit, zip)
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN ISDATE(rm.CB_prescreen_birth_date) = 1 THEN rm.CB_prescreen_birth_date
			ELSE NULL
		END AS birth_date,
		RTRIM(rm.pri_city),
		RTRIM(rm.primary_first_name),
		RTRIM(rm.primary_last_name),
		CASE
			WHEN LEN(rm.primary_middle_name) > 0 THEN RTRIM(rm.primary_middle_name)
		END AS middle_initial,
		CASE
			WHEN LEN(rm.pri_po_box_num) > 0 THEN RTRIM(rm.pri_po_box_num)
		END AS po_box,		
		CASE
			WHEN ap.prescreen_fico_grade <> '' AND ap.prescreen_fico_grade IS NOT NULL	THEN ap.prescreen_fico_grade
		END AS prescreen_fico_grade,
		CASE
			WHEN ap.prescreen_risk_grade <> '' AND ap.prescreen_risk_grade IS NOT NULL	THEN ap.prescreen_risk_grade
		END AS prescreen_risk_grade,
		CASE
			WHEN LEN(rm.pri_rural_rt_num) > 0 THEN RTRIM(rm.pri_rural_rt_num)
		END AS rural_route,
		RTRIM(rm.primary_ssn),
		RTRIM(rm.pri_state),
		RTRIM(rm.pri_cur_street_name),
		RTRIM(rm.pri_cur_street_num),
		CASE
			WHEN LEN(rm.primary_suffix) > 0 THEN RTRIM(rm.primary_suffix)
		END AS suffix,
		CASE
			WHEN LEN(rm.pri_apt_number) > 0 THEN RTRIM(rm.pri_apt_number)
		END AS unit,
		RTRIM(rm.pri_zip_code)
	FROM application AS a
	INNER JOIN rmts_info AS rm ON rm.app_id = a.app_id
	LEFT JOIN app_product AS ap ON ap.app_id = a.app_id
	WHERE rm.CB_prescreen_birth_date <> '';

UPDATE STATISTICS dbo.app_solicited_cc;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- contact_base ---------------------------------------------------------------------------------------------------------------------------------

SET IDENTITY_INSERT dbo.app_contact_base ON;

	INSERT INTO dbo.app_contact_base
		(con_id, app_id, birth_date, cell_phone, contact_type_enum, email, esign_consent_flag, first_name, fraud_type_enum, home_phone, last_name, 
		 middle_initial, mother_maiden_name, paperless_flag, sms_consent_flag, ssn, suffix)
		SELECT 
			c.con_id,
			a.app_id,
			-- Set NULL dates so we can preserve NOT NULL constraint (these exist in PRD for AUTHU from 2008 and past)
			CASE
				WHEN c.birth_date IS NULL THEN '1900-01-01'
				WHEN ISDATE(c.birth_date) = 1 THEN c.birth_date
				ELSE '1900-01-01'
			END AS birth_date,
			CASE
				WHEN ca.cell_phone = '27675910166' THEN '2767591016'	-- there's one PRD entry that is 11 characters
				ELSE LEFT(RTRIM(REPLACE(REPLACE(REPLACE(ca.cell_phone, '-', ''), ')', ''), '(', '')), 9)
			END AS cell_phone,
			CASE
				WHEN RTRIM(c.ac_role_tp_c) = 'AUTHU'	THEN 280
				WHEN RTRIM(c.ac_role_tp_c) = 'PR'		THEN 281
			END AS contact_type_enum,
			CASE
				WHEN LEN(c.email) > 0 THEN RTRIM(c.email) 
				ELSE NULL
			END AS email,
			a.esign_consent_flag,
			RTRIM(c.first_name) AS first_name,
			CASE
				WHEN RTRIM(c.fraud_ind) = 'S'		THEN 290
				WHEN RTRIM(c.fraud_ind) = 'V'		THEN 291
			END AS fraud_type_enum,
			CASE
				WHEN LEN(ca.home_phone) > 0	THEN LEFT(RTRIM(REPLACE(REPLACE(REPLACE(ca.home_phone, '-', ''), ')', ''), '(', '')), 9)
				ELSE NULL
			END AS home_phone,
			RTRIM(c.last_name) AS last_name,
			CASE
				WHEN c.initials <> '' THEN c.initials
				ELSE NULL
			END AS middle_initial,
			RTRIM(c.mother_maiden_name) AS mother_maiden_name,
			a.paperless_flag,
			a.sms_consent_flag,
			-- Set NULL ssn's so we can preserve NOT NULL constraint (these exist in PROD for AUTHU from 2008 and past)
			CASE
				WHEN c.ssn IS NULL THEN '000000000'
				ELSE RTRIM(c.ssn)
			END AS ssn,
			CASE
				WHEN LEN(c.suffix) > 0 THEN RTRIM(c.suffix) 
				ELSE NULL
			END AS suffix
		FROM contact AS c
		INNER JOIN application AS a ON a.app_id = c.app_id
		LEFT JOIN contact_address AS ca ON ca.con_id = c.con_id AND ca.address_tp_c = 'CURR'	-- We just need a few values from the first row
		
		-- Should we ALLOW BAD DATA and violate the PK? -- NO DATA LIKE THIS EXIST IN PROD
		WHERE 
			a.app_id NOT IN (7357)
			and first_name is not null
			and birth_date <> ''
			and birth_date is not null;
		

SET IDENTITY_INSERT dbo.app_contact_base OFF;

-- Reseed table to be next app_id
DECLARE	@max2	int	= (SELECT MAX(con_id) FROM dbo.app_contact_base);
DBCC CHECKIDENT ('dbo.app_contact_base', RESEED, @max2);

UPDATE STATISTICS dbo.app_contact_base;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- contact_address ------------------------------------------------------------------------------------------------------------------------------

INSERT INTO dbo.app_contact_address
	(con_id, address_type_enum, city, months_at_address, ownership_type_enum, po_box, rural_route, [state], street_name, street_number, unit, zip)
	SELECT 
		ca.con_id,
	CASE
		WHEN RTRIM(ca.address_tp_c) = 'CURR'	THEN 320
		WHEN RTRIM(ca.address_tp_c) = 'PREV'	THEN 321
	END AS address_type_enum,
	ca.city,
	CASE
		WHEN ca.months_at_residence > 0 OR ca.years_at_residence > 0	THEN CAST(ca.months_at_residence + (ca.years_at_residence * 12) AS smallint) 
		ELSE NULL
	END AS months_at_address,
	CASE
		WHEN RTRIM(ca.ownership_tp_c) = 'O'		THEN 330
		WHEN RTRIM(ca.ownership_tp_c) = 'R'		THEN 332
		WHEN RTRIM(ca.ownership_tp_c) = 'X'		THEN 335
		ELSE NULL
	END AS ownership_type_enum,
	CASE
		WHEN ca.po_box <> '' THEN ca.po_box
		ELSE NULL
	END AS po_box,
	CASE
		WHEN ca.rural_route <> '' THEN ca.rural_route
		ELSE NULL
	END AS rural_route,
	ca.state,
	CASE
		WHEN ca.street_name <> ''	THEN ca.street_name
		ELSE NULL
	END AS street_name,
	CASE
		WHEN ca.street_number <> ''	THEN ca.street_number
		ELSE NULL
	END AS street_number,
	CASE
		WHEN ca.unit <> '' THEN ca.unit
		ELSE NULL
	END AS unit,
	REPLACE(ca.zip, '-', '')
	FROM contact_address AS ca
	INNER JOIN dbo.app_contact_base AS c ON c.con_id = ca.con_id	-- make sure we don't have any orphans that would violate our FK for con_id
	-- ****
	--INNER JOIN contact AS c ON c.con_id = ca.con_id		-- make sure we don't have any orphans that would violate our FK for con_id
	
	-- REVIEW: we have almost a MILLION rows in PROD that have no data except for sometimes a unit number. REMOVE THESE.
	WHERE 
		ca.address_tp_c IS NOT NULL AND ca.address_tp_c <> ''
		AND c.app_id NOT IN (7357);

UPDATE STATISTICS dbo.app_contact_address;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- contact_address ------------------------------------------------------------------------------------------------------------------------------

INSERT INTO dbo.app_contact_employment
	(con_id, city, business_name, employment_type_enum, income_source_nontaxable_flag, income_type_enum, job_title, monthly_salary, months_at_job, 
	 other_monthly_income, other_income_type_enum, other_income_source_detail, phone, self_employed_flag, [state], 
	 street_name, street_number, unit, zip)
	SELECT 
		e.con_id,
		e.b_city,
		e.b_name AS business_name,
	CASE
		WHEN RTRIM(e.employment_tp_c) = 'CURR'	THEN 350
		WHEN RTRIM(e.employment_tp_c) = 'PREV'	THEN 351
	END AS employment_type_enum,
	CASE
		WHEN b_income_source_nontaxable = 'Y' THEN 1
		ELSE 0
	END AS income_source_nontaxable_flag,
	CASE
		WHEN RTRIM(e.b_primary_income_source_tp_c) = 'ALLOW'	THEN 360
		WHEN RTRIM(e.b_primary_income_source_tp_c) = 'EMPLOY'	THEN 361
		WHEN RTRIM(e.b_primary_income_source_tp_c) = 'GOVAST'	THEN 362
		WHEN RTRIM(e.b_primary_income_source_tp_c) = 'INVEST'	THEN 363
		WHEN RTRIM(e.b_primary_income_source_tp_c) = 'OTHER'	THEN 364
		WHEN RTRIM(e.b_primary_income_source_tp_c) = 'RENTAL'	THEN 365
		ELSE NULL
	END AS b_primary_income_source_tp_c,
	e.b_job_title_tp_c,
	CASE
		WHEN RTRIM(e.b_salary_basis_tp_c) = 'ANNUM' THEN e.b_salary / 12
		WHEN RTRIM(e.b_salary_basis_tp_c) = 'WEEK' THEN e.b_salary * 52
		WHEN RTRIM(e.b_salary_basis_tp_c) = 'MONTH' THEN e.b_salary
		ELSE e.b_salary
	END AS b_salary,
	CAST(b_months_at_job + (b_years_at_job * 12) AS smallint) AS b_months_at_job,
	CASE
		WHEN RTRIM(e.b_othr_inc_basis_tp_c) = 'ANNUM' THEN e.b_other_income_amt / 12
		WHEN RTRIM(e.b_othr_inc_basis_tp_c) = 'MONTH' THEN e.b_other_income_amt
		ELSE e.b_other_income_amt
	END AS b_other_income_amt,
	CASE
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'ALLOW'					THEN 380
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'ALMONY'					THEN 381
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'BONUS'					THEN 382
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'CHDSUP'					THEN 383
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'CTPYMT'					THEN 384
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'DISINC'					THEN 385
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'EMPLOY'					THEN 386
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'INVEST'					THEN 387
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'MILTRY'					THEN 388
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'OTHER'					THEN 389
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'PNSION'					THEN 390
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'PUBAST'					THEN 391
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'RENTAL'					THEN 392
		WHEN RTRIM(e.b_other_income_source_tp_c) = '2NDJOB'					THEN 393
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'SOCSEC'					THEN 394
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'SPOUSE'					THEN 395
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'TRUST'					THEN 396
		WHEN RTRIM(e.b_other_income_source_tp_c) IN ('UEMBEN', 'UNEMPL')	THEN 397
		WHEN RTRIM(e.b_other_income_source_tp_c) ='UNKN'					THEN 398
		WHEN RTRIM(e.b_other_income_source_tp_c) = 'VA'						THEN 399
		ELSE NULL
	END AS b_other_income_source_tp_c,
	e.b_other_income_source_detail,
	RTRIM(REPLACE(REPLACE(REPLACE(b_phone_no, '-', ''), ')', ''), '(', '')) AS b_phone_no,
	CASE
		WHEN e.b_self_employed_ind = 'Y' THEN 1
		ELSE 0
	END AS b_self_employed_ind,
	b_state,
	b_street_name,
	CASE
		WHEN b_street_number <> ''	THEN b_street_number
		ELSE NULL
	END AS street_number,
	CASE
		WHEN b_unit <> ''	THEN b_unit
		ELSE NULL
	END AS unit,
	REPLACE(b_zip, '-', '')
	FROM contact_employment AS e
	INNER JOIN dbo.app_contact_base AS c ON c.con_id = e.con_id	-- make sure we don't have any orphans that would violate our FK for con_id
	WHERE 
		e.employment_tp_c IN ('CURR', 'PREV')
		AND c.app_id NOT IN (7357);

UPDATE STATISTICS dbo.app_contact_employment;

-----------------------------------------------------------------------------------------------------------------------------------------------------
-- app_report_results_lookup ------------------------------------------------------------------------------------------------------------------------
-- Used as a convenient method to store and retrieve key/value pairs from a report w/o parsing it again 
--	(when it doesn't fit in neatly to a score or an indicator or part of every app)	e.g. GIACT_Response, InstantID_Score, VeridQA_Result

-- GIACT
INSERT INTO dbo.app_report_results_lookup
	(app_id, [name], [value])
	SELECT DISTINCT
		a.app_id,
		'GIACT_Response',
		p.GIACT_Response
	FROM app_base AS a
	INNER JOIN app_product AS p ON p.app_id = a.app_id
	WHERE LEN(p.GIACT_Response) > 0 AND p.GIACT_Response <> 'Null';

-- InstantID
INSERT INTO dbo.app_report_results_lookup
	(app_id, [name], [value], [source_report_key])
	SELECT DISTINCT
		a.app_id,
		'InstantID_Score',
		p.InstantID_Score,
		'IDV'
	FROM app_base AS a
	INNER JOIN app_product AS p ON p.app_id = a.app_id
	WHERE LEN(p.InstantID_Score) > 0;

-- VeridQA
INSERT INTO dbo.app_report_results_lookup
	(app_id, [name], [value])
	SELECT DISTINCT
		a.app_id,
		'VeridQA_Result',
		p.VeridQA_Result
	FROM app_base AS a
	INNER JOIN app_product AS p ON p.app_id = a.app_id
	WHERE LEN(p.VeridQA_Result) > 0;

UPDATE STATISTICS dbo.app_report_results_lookup;

-------------------------------------------------------------------------------------------------------------------------------------------------
