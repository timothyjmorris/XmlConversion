


-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_base -------------------------------------------------------------------------------------------------------------------------------------
SET IDENTITY_INSERT sandbox.app_base ON;

	INSERT INTO sandbox.app_base
		(app_id, product_line_enum, app_source_enum, app_type_enum, booked_date, decision_enum, decision_date, funding_date, ip_address, receive_date, retain_until_date, sub_type_enum)
		SELECT 
			a.app_id, 
			602 AS product_line_enum,
			CASE
				WHEN RTRIM(app_source_ind) = 'A'		THEN 10
				WHEN RTRIM(app_source_ind) = 'D'		THEN 11
				WHEN RTRIM(app_source_ind) = 'F'		THEN 12
				WHEN RTRIM(app_source_ind) = 'S'		THEN 13
				ELSE NULL
			END AS app_source_enum, 
			CASE
				WHEN RTRIM(app_type_code) = 'HT'		THEN 38
				WHEN RTRIM(app_type_code) = 'MARINE'	THEN 39
				WHEN RTRIM(app_type_code) = 'MC'		THEN 40
				WHEN RTRIM(app_type_code) = 'OR'		THEN 41
				WHEN RTRIM(app_type_code) = 'RV'		THEN 42
				WHEN RTRIM(app_type_code) = 'UT'		THEN 43
				ELSE NULL
			END AS app_type_enum, 
			CASE
				WHEN c.boarding_datetime IS NOT NULL	THEN c.boarding_datetime
				WHEN ISDATE(c.boarding_date) = 1		THEN c.boarding_date
				ELSE NULL
			END AS booked_date,
			CASE
				WHEN RTRIM(d.decision_type_code) = 'APPRV'	THEN 65
				WHEN RTRIM(d.decision_type_code) = 'DECLN'	THEN 66
				WHEN RTRIM(d.decision_type_code) = 'WITHD'	THEN 67
				ELSE NULL
			END AS decision_enum, 
			d.decision_date AS decision_date, 
			c.funding_date AS funding_date,
			NULL AS ip_address, 
			CASE 
				WHEN a.app_entry_date IS NOT NULL THEN a.app_entry_date
				ELSE a.app_receive_date
			END AS receive_date,
			-- retention_date isn't yet on IL, should we add this on based off of app_entry_date for now?
			NULL AS retain_until_date,
			CASE
				WHEN RTRIM(sub_type_code) = 'ATV'			THEN 45
				WHEN RTRIM(sub_type_code) = 'PWC'			THEN 46
				WHEN RTRIM(sub_type_code) = 'SNOWMOBILE'	THEN 47
				WHEN RTRIM(sub_type_code) = 'UTV'			THEN 48
				ELSE NULL
			END AS sub_type_enum
		FROM IL_application AS a
		LEFT JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
		LEFT JOIN IL_ITI_control AS c ON c.app_id = a.app_id;
		
SET IDENTITY_INSERT sandbox.app_base OFF;

-- Reseed table to be next app_id
DECLARE	@max	int	= (SELECT MAX(app_id) FROM sandbox.app_base);
DBCC CHECKIDENT ('sandbox.app_base', RESEED, @max);

UPDATE STATISTICS sandbox.app_base;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_operational_cc ---------------------------------------------------------------------------------------------------------------------------

INSERT INTO sandbox.app_operational_rl
	(app_id, assigned_credit_analyst, assigned_funding_analyst, cb_score_factor_code_pr_1, cb_score_factor_code_pr_2, cb_score_factor_code_pr_3, cb_score_factor_code_pr_4, 
	 cb_score_factor_code_pr_5, cb_score_factor_type_pr_1, cb_score_factor_type_pr_2, cb_score_factor_type_pr_3, cb_score_factor_type_pr_4, cb_score_factor_type_pr_5, 
	 cb_score_factor_code_sec_1, cb_score_factor_code_sec_2, cb_score_factor_code_sec_3, cb_score_factor_code_sec_4, cb_score_factor_code_sec_5, cb_score_factor_type_sec_1, 
	 cb_score_factor_type_sec_2, cb_score_factor_type_sec_3, cb_score_factor_type_sec_4, cb_score_factor_type_sec_5, joint_app_flag, last_updated_by, last_updated_date,  
	 mrv_lead_indicator_pr_enum, mrv_lead_indicator_sec_enum, priority_enum, process_enum, regb_end_date, regb_start_date, status_enum)
	SELECT 
		a.app_id,
		CASE
			WHEN assigned_analyst <> '' THEN UPPER(assigned_analyst) 
			ELSE NULL
		END AS assigned_credit_analyst,
		(SELECT TOP (1) UPPER(RTRIM(email_address)) FROM g_user_profile WHERE CAST(g_user_profile.loan_officer_code AS int) = funding_contact_code AND g_user_profile.loan_officer_code <> '') AS assigned_funding_analyst,
		CASE
			WHEN LEN(d.score_factor_code_1_PR) > 0			THEN d.score_factor_code_1_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_1)) > 0		THEN RTRIM(d.MRVP_Decline_Code_1)
			WHEN LEN(RTRIM(d.Vantage4P_decline_code1)) > 0	THEN RTRIM(d.Vantage4P_decline_code1)
			ELSE NULL
		END AS score_factor_code_1_PR, 
		CASE
			WHEN LEN(d.score_factor_code_2_PR) > 0			THEN d.score_factor_code_2_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_2)) > 0		THEN RTRIM(d.MRVP_Decline_Code_2)
			WHEN LEN(RTRIM(d.Vantage4P_decline_code2)) > 0	THEN RTRIM(d.Vantage4P_decline_code2)
			ELSE NULL
		END AS score_factor_code_2_PR, 
		CASE
			WHEN LEN(d.score_factor_code_3_PR) > 0			THEN d.score_factor_code_3_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_3)) > 0		THEN RTRIM(d.MRVP_Decline_Code_3)
			WHEN LEN(RTRIM(d.Vantage4P_decline_code3)) > 0	THEN RTRIM(d.Vantage4P_decline_code3)
			ELSE NULL
		END AS score_factor_code_3_PR, 
		CASE
			WHEN LEN(d.score_factor_code_4_PR) > 0			THEN d.score_factor_code_4_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_4)) > 0		THEN RTRIM(d.MRVP_Decline_Code_4)
			WHEN LEN(RTRIM(d.Vantage4P_decline_code4)) > 0	THEN RTRIM(d.Vantage4P_decline_code4)
			ELSE NULL
		END AS score_factor_code_4_PR, 
		CASE
			WHEN LEN(d.score_factor_code_5_PR) > 0			THEN d.score_factor_code_5_PR
			WHEN LEN(RTRIM(d.Vantage4P_decline_code5)) > 0	THEN RTRIM(d.Vantage4P_decline_code5)
			ELSE NULL
		END AS score_factor_code_5_PR,
		CASE
			WHEN LEN(d.score_factor_code_1_SEC) > 0			THEN d.score_factor_code_1_SEC
			WHEN LEN(RTRIM(d.MRVS_Decline_Code_1)) > 0		THEN RTRIM(d.MRVS_Decline_Code_1)
			WHEN LEN(RTRIM(d.Vantage4S_decline_code1)) > 0	THEN RTRIM(d.Vantage4S_decline_code1)
			ELSE NULL
		END AS score_factor_code_1_SEC, 
		CASE
			WHEN LEN(d.score_factor_code_2_SEC) > 0			THEN d.score_factor_code_2_SEC
			WHEN LEN(RTRIM(d.MRVS_Decline_Code_2)) > 0		THEN RTRIM(d.MRVS_Decline_Code_2)
			WHEN LEN(RTRIM(d.Vantage4S_decline_code2)) > 0	THEN RTRIM(d.Vantage4S_decline_code2)
			ELSE NULL
		END AS score_factor_code_2_SEC, 
		CASE
			WHEN LEN(d.score_factor_code_3_SEC) > 0			THEN d.score_factor_code_3_SEC
			WHEN LEN(RTRIM(d.MRVS_Decline_Code_3)) > 0		THEN RTRIM(d.MRVS_Decline_Code_3)
			WHEN LEN(RTRIM(d.Vantage4S_decline_code3)) > 0	THEN RTRIM(d.Vantage4S_decline_code3)
			ELSE NULL
		END AS score_factor_code_3_SEC, 
		CASE
			WHEN LEN(d.score_factor_code_4_SEC) > 0			THEN d.score_factor_code_4_SEC
			WHEN LEN(RTRIM(d.MRVS_Decline_Code_4)) > 0		THEN RTRIM(d.MRVS_Decline_Code_4)
			WHEN LEN(RTRIM(d.Vantage4S_decline_code4)) > 0	THEN RTRIM(d.Vantage4S_decline_code4)
			ELSE NULL
		END AS score_factor_code_4_SEC, 
		CASE
			WHEN LEN(d.score_factor_code_5_SEC) > 0			THEN d.score_factor_code_5_SEC
			WHEN LEN(RTRIM(d.Vantage4S_decline_code5)) > 0	THEN RTRIM(d.Vantage4S_decline_code5)
			ELSE NULL
		END AS score_factor_code_5_SEC,
		CASE
			WHEN LEN(d.score_factor_type_1_PR) > 0			THEN d.score_factor_type_1_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_1)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code1)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_1_PR,
		CASE
			WHEN LEN(d.score_factor_type_2_PR) > 0			THEN d.score_factor_type_1_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_2)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code2)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_2_PR, 
		CASE
			WHEN LEN(d.score_factor_type_3_PR) > 0			THEN d.score_factor_type_1_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_3)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code3)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_3_PR, 
		CASE
			WHEN LEN(d.score_factor_type_4_PR) > 0			THEN d.score_factor_type_1_PR
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_4)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code4)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_4_PR, 
		CASE
			WHEN LEN(d.score_factor_type_5_PR) > 0			THEN d.score_factor_type_1_PR
			WHEN LEN(RTRIM(d.Vantage4P_decline_code5)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_5_PR, 
		CASE
			WHEN LEN(d.score_factor_type_1_SEC) > 0			THEN d.score_factor_type_1_SEC
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_1)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code1)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_1_SEC,
		CASE
			WHEN LEN(d.score_factor_type_2_SEC) > 0			THEN d.score_factor_type_1_SEC
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_2)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code2)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_2_SEC, 
		CASE
			WHEN LEN(d.score_factor_type_3_SEC) > 0			THEN d.score_factor_type_1_SEC
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_3)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code3)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_3_SEC, 
		CASE
			WHEN LEN(d.score_factor_type_4_SEC) > 0			THEN d.score_factor_type_1_SEC
			WHEN LEN(RTRIM(d.MRVP_Decline_Code_4)) > 0		THEN 'MRV1'
			WHEN LEN(RTRIM(d.Vantage4P_decline_code4)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_4_SEC, 
		CASE
			WHEN LEN(d.score_factor_type_5_SEC) > 0			THEN d.score_factor_type_1_SEC
			WHEN LEN(RTRIM(d.Vantage4P_decline_code5)) > 0 AND a.app_receive_date > '2020-01-01'	THEN 'V4'
			ELSE NULL
		END AS score_factor_type_5_SEC, 
		CASE
			WHEN a.individual_joint_app_ind = 'J'	THEN	1
			ELSE 0
		END AS joint_app_flag,
		CASE
			WHEN LEN(a.updated_by) > 0 THEN a.updated_by
			WHEN a.[user_id] <> '' THEN a.[user_id]
			ELSE NULL
		END AS last_updated_by,
		a.last_update_time,
		CASE
			WHEN RTRIM(d.MRV_Lead_Indicator_P) = 'MRV'		THEN 640
			WHEN RTRIM(d.MRV_Lead_Indicator_P) = 'Vantage'	THEN 641
			ELSE NULL
		END AS mrv_lead_indicator_pr_enum,
		CASE
			WHEN RTRIM(d.MRV_Lead_Indicator_S) = 'MRV'		THEN 640
			WHEN RTRIM(d.MRV_Lead_Indicator_S) = 'Vantage'	THEN 641
			ELSE NULL
		END AS mrv_lead_indicator_sec_enum,
		NULL AS [priority],	-- currently no values in priority column
		CASE
			WHEN RTRIM(a.process) = '03800'	THEN 670
			WHEN RTRIM(a.process) = '05800'	THEN 671
			WHEN RTRIM(a.process) = '06800'	THEN 672
			WHEN RTRIM(a.process) = '06850'	THEN 673
			WHEN RTRIM(a.process) = '08800'	THEN 674
			WHEN RTRIM(a.process) = '20800'	THEN 675
			WHEN RTRIM(a.process) = '30800'	THEN 676
			WHEN RTRIM(a.process) = '40800'	THEN 677
			WHEN RTRIM(a.process) = '99800'	THEN 678
			ELSE NULL
		END AS process,
		CASE 
			WHEN d.regb_closed_days_num > 0	AND a.app_entry_date IS NOT NULL THEN DATEADD(day, d.regb_closed_days_num, a.app_entry_date)
			WHEN d.regb_closed_days_num > 0	AND a.app_receive_date IS NOT NULL THEN DATEADD(day, d.regb_closed_days_num, a.app_receive_date)
			ELSE NULL
		END AS regb_end_date,
		CASE 
			WHEN a.app_entry_date IS NOT NULL THEN a.app_entry_date
			ELSE a.app_receive_date
		END AS regb_start_date,
		CASE
			WHEN RTRIM(a.[status]) = 'F'	THEN 690
			WHEN RTRIM(a.[status]) = 'P'	THEN 691
			ELSE NULL
		END AS [status]
	FROM IL_application AS a
	LEFT JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	LEFT JOIN IL_ITI_control AS c ON c.app_id = a.app_id
	LEFT JOIN IL_fund_checklist AS f ON f.app_id = a.app_id;

	-- Add monthly housing payments here to avoid dupes & weirdness from having it all in one query above
	UPDATE sandbox.app_operational_rl
		SET housing_monthly_payment_pr = residence_monthly_pymnt
		FROM sandbox.app_operational_rl
		INNER JOIN 
			(SELECT a.app_id, residence_monthly_pymnt
			FROM IL_application AS a
			INNER JOIN IL_contact AS c ON c.app_id = a.app_id
			INNER JOIN IL_contact_address AS ca ON ca.con_id = c.con_id
			WHERE
				c.ac_role_tp_c = 'PR' AND 
				ca.address_type_code = 'CURR' AND
				ca.residence_monthly_pymnt > 0) AS subquery
			ON sandbox.app_operational_rl.app_id = subquery.app_id;
	
	UPDATE sandbox.app_operational_rl
		SET housing_monthly_payment_pr = residence_monthly_pymnt
		FROM sandbox.app_operational_rl
		INNER JOIN 
			(SELECT a.app_id, residence_monthly_pymnt
			FROM IL_application AS a
			INNER JOIN IL_contact AS c ON c.app_id = a.app_id
			INNER JOIN IL_contact_address AS ca ON ca.con_id = c.con_id
			WHERE
				c.ac_role_tp_c = 'SEC' AND 
				ca.address_type_code = 'CURR' AND
				ca.residence_monthly_pymnt > 0) AS subquery
			ON sandbox.app_operational_rl.app_id = subquery.app_id;

UPDATE STATISTICS sandbox.app_operational_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_transactional_rl -------------------------------------------------------------------------------------------------------------------------

INSERT INTO sandbox.app_transactional_rl
	(app_id, audit_type_enum, duplicate_app_flag, fund_loan_indicator_enum, pending_verification_flag, supervisor_review_indicator_enum, suppress_ach_funding_flag)
	SELECT DISTINCT
		a.app_id,
		(SELECT 
			CASE 
				WHEN RTRIM([value]) = 'R'	THEN 706
				WHEN RTRIM([value]) = 'P'	THEN 707
			ELSE NULL
			END
		FROM Indicators WHERE indicator = 'RLAudit' AND app_id = a.app_id) AS audit_type_enum,
		CASE
			WHEN a.duplicate_app_ind = 'Y' THEN 1
			ELSE 0
		END AS duplicate_app_flag,
		CASE
			WHEN f.fund_this_loan_indicator = 'Y' THEN 655
			WHEN f.fund_this_loan_indicator = 'N' THEN 656
			WHEN f.fund_this_loan_indicator = 'P' THEN 657
			ELSE NULL
		END AS fund_loan_indicator_enum,
		CASE
			WHEN i.pending_verif_ind = 'Y' THEN 1
			WHEN i.pending_verif_ind = 'N' THEN 0
			ELSE NULL
		END AS pending_verification_flag,
		
		CASE
			WHEN a.supervisor_rev_ind = 'C' THEN 700
			WHEN a.supervisor_rev_ind = 'R' THEN 701
			ELSE NULL
		END AS supervisor_review_indicator_enum,
		CASE
			WHEN d.suppress_ach = 'Y' THEN 1
			ELSE 0
		END AS suppress_ach_funding_flag
	FROM IL_application AS a
	INNER JOIN IL_fund_checklist AS f ON f.app_id = a.app_id
	INNER JOIN IL_fund_dlr_ach AS d ON d.app_id = a.app_id
	LEFT JOIN IL_app_decision_info AS i ON i.app_id = a.app_id
	WHERE
		-- Don't populate this table unless there's at least one column with a value!
		LEN(a.duplicate_app_ind) > 0 OR
		LEN(f.fund_this_loan_indicator) > 0 OR
		LEN(i.pending_verif_ind) > 0 OR 
		LEN(a.supervisor_rev_ind) > 0 OR
		LEN(d.suppress_ach) > 0;
		
UPDATE STATISTICS sandbox.app_transactional_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_pricing_rl -------------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_pricing_rl
	(app_id, add_total_to_financed_flag, cash_down_payment_amount, debt_to_income_ratio, invoice_amount, loan_amount, loan_term_months, manual_adj_dti_ratio, 
	 manual_adj_monthly_debt, manual_adj_monthly_income, military_apr, monthly_debt, monthly_income, mrv_grade_pr, mrv_grade_sec, regular_payment_amount, 
	 selling_price, tradein_allowance, tradein_down_payment_amount, tradein_payoff_amount)
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN a.add_TTL_to_amt_fin = 'Y'	THEN 1
			WHEN a.add_TTL_to_amt_fin = 'N'	THEN 0
			ELSE NULL
		END AS add_total_to_financed_flag,
		app_cash_down_payment AS cash_down_payment_amount,
		debt_to_income_ratio AS debt_to_income_ratio, 		
		app_invoice_amount AS invoice_amount,
		loan_amount_requested AS loan_amount, 
		requested_term_months AS loan_term_months, 
		CASE
			WHEN manual_adj_DTI_ratio > 0 THEN manual_adj_DTI_ratio
			ELSE NULL
		END AS manual_adj_dti_ratio,
		CASE
			WHEN manual_adj_monthly_debt > 0 THEN manual_adj_monthly_debt
			ELSE NULL
		END AS manual_adj_monthly_debt, 
		manual_adj_monthly_income AS manual_adj_monthly_income, 
		mapr AS military_apr, 
		monthly_debt AS monthly_debt, 
		monthly_income AS monthly_income, 
		CASE
			WHEN MRV_Grade_P <> '' THEN MRV_Grade_P
			ELSE NULL
		END AS mrv_grade_pr, 
		CASE
			WHEN MRV_Grade_S <> '' THEN MRV_Grade_S
			ELSE NULL
		END AS mrv_grade_sec, 
		regular_pymt_amount1 AS regular_payment_amount, 
		app_sale_price AS selling_price, 
		CASE 
			WHEN trade_allowance > 0 THEN trade_allowance
			ELSE NULL
		END AS tradein_allowance, 
		CASE
			WHEN trade_net_tradein_amount > 0 THEN trade_net_tradein_amount
			ELSE NULL
		END AS tradein_down_payment_amount, 
		CASE
			WHEN trade_payoff_amount > 0 THEN trade_payoff_amount
		END AS tradein_payoff_amount
	FROM IL_application AS a
	LEFT JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	LEFT JOIN IL_ITI_control AS c ON c.app_id = a.app_id
	LEFT JOIN IL_fund_checklist AS f ON f.app_id = a.app_id;
	
UPDATE STATISTICS sandbox.app_pricing_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_funding_rl -------------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_funding_rl
	(app_id, amount_financed_within_policy_flag, collateral_ages_within_policy_flag, credit_bureau_expire_date, credit_pulled_within_30_days_flag, 
	 creditscore_within_policy_flag, dealer_proceeds_amount, down_payment_within_policy_flag, dti_within_policy_flag, first_payment_not_in_7_days_flag, 
	 loan_amount_approved_flag, loan_amount_within_policy_flag, loanpro_loan_id, ltv_within_policy_flag, 
	 note_date_in_range_flag, participation_percentage, participation_proceeds, paystub_within_30days_pr_flag, paystub_within_30days_sec_flag, 
	 product_number, subtotal, term_within_policy_flag, total_of_payments_amount, validated_finance_charge)
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN ct_amt_financed_within_policy = 'Y'	THEN 1
			WHEN ct_amt_financed_within_policy = 'N'	THEN 0
			ELSE NULL
		END AS amount_financed_within_policy_flag,
		CASE
			WHEN collateral_ages_within_policy = 'Y'	THEN 1
			WHEN collateral_ages_within_policy = 'N'	THEN 0 
			ELSE NULL
		END AS collateral_ages_within_policy_flag,
		credit_bureau_expire AS credit_bureau_expire_date,
		CASE
			WHEN loan_Credit_pulled_within_30days = 'Y'	THEN 1
			WHEN loan_Credit_pulled_within_30days = 'N'	THEN 0 
			ELSE NULL
		END AS credit_pulled_within_30_days_flag,
		CASE
			WHEN loan_FICO_within_policy = 'Y'	THEN 1
			WHEN loan_FICO_within_policy = 'N'	THEN 0 
			ELSE NULL
		END AS creditscore_within_policy_flag,
		ct_total_dealer_proceeds AS dealer_proceeds_amount,
		CASE
			WHEN loan_down_pymt_within_policy = 'Y'	THEN 1
			WHEN loan_down_pymt_within_policy = 'N'	THEN 0 
			ELSE NULL
		END AS down_payment_within_policy_flag,
		CASE
			WHEN loan_DTI_ratio_within_policy = 'Y'	THEN 1
			WHEN loan_DTI_ratio_within_policy = 'N'	THEN 0 
			ELSE NULL		
		END AS dti_within_policy_flag,
		CASE
			WHEN loan_1st_pymt_not7days = 'Y'	THEN 1
			WHEN loan_1st_pymt_not7days = 'N'	THEN 0 
			ELSE NULL
		END AS first_payment_not_in_7_days_flag,
		CASE
			WHEN loan_amount_approved = 'Y'	THEN 1
			WHEN loan_amount_approved = 'N'	THEN 0 
			ELSE NULL
		END AS loan_amount_approved_flag,
		CASE
			WHEN loan_amount_within_policy = 'Y'	THEN 1
			WHEN loan_amount_within_policy = 'N'	THEN 0 
			ELSE NULL
		END AS loan_amount_within_policy_flag,
		a.loanpro_loan_id,
		CASE
			WHEN loan_LTV_within_policy = 'Y'	THEN 1
			WHEN loan_LTV_within_policy = 'N'	THEN 0
			ELSE NULL
		END AS ltv_within_policy_flag,
		CASE
			WHEN loan_note_date_in_range = 'Y'	THEN 1
			WHEN loan_note_date_in_range = 'N'	THEN 0
			ELSE NULL
		END AS note_date_in_range_flag,
		ct_participation_percentage AS participation_percentage,
		ct_participation_proceeds AS participation_proceeds,
		CASE
			WHEN loan_Paystub_within_30days = 'Y'	THEN 1
			WHEN loan_Paystub_within_30days = 'N'	THEN 0
			ELSE NULL
		END AS paystub_within_30days_pr_flag,
		CASE
			WHEN loan_Paystub2_within_30days = 'Y'	THEN 1
			WHEN loan_Paystub2_within_30days = 'N'	THEN 0
			ELSE NULL
		END AS paystub_within_30days_sec_flag,
		CASE
			WHEN LEN(n.product_number) > 1	THEN RTRIM(n.product_number)
		END AS product_number,
		subtotal,
		CASE
			WHEN loan_term_within_policy = 'Y'	THEN 1
			WHEN loan_term_within_policy = 'N'	THEN 0
			ELSE NULL
		END AS term_within_policy_flag,
		total_of_payments AS total_of_payments_amount,
		-- DOES THIS COLUMN BELONG? not reconciling it to anything (is it the same as "finance_charge" in Fund Checklist?)
		NULL AS validated_finance_charge
	FROM IL_application AS a
	LEFT JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	LEFT JOIN IL_ITI_control AS c ON c.app_id = a.app_id
	LEFT JOIN IL_fund_checklist AS f ON f.app_id = a.app_id
	LEFT JOIN IL_ITI_note AS n ON n.app_id = a.app_id
	WHERE
		-- **** ONLY POPULATED FUNDED APPS HERE???? OTHERWISE WE'RE TRACKOING 98% BLANK FIELDS!!!! ***
		-- Make sure we're not just populating this with blank data
		LEN(f.ct_pymt_schedule_confirmed) > 0 OR LEN(f.chk_requested_by) > 0 OR LEN(f.ct_signed_borrower1) > 0 OR 
		LEN(f.loan_down_pymt_approved) > 0 OR LEN(f.ct_address_confirmed) > 0 OR LEN(f.loan_unit_confirmed) > 0


	-- Add funding LoanPro customer id's here to avoid dupes & weirdness from having it all in one query above
	UPDATE sandbox.app_funding_rl
		SET loanpro_customer_id_pr = loanpro_customer_id
		FROM sandbox.app_funding_rl
		INNER JOIN 
			(SELECT a.app_id, loanpro_customer_id
			FROM IL_application AS a
			INNER JOIN IL_contact AS c ON c.app_id = a.app_id
			WHERE
				c.ac_role_tp_c = 'PR' AND 
				c.loanpro_customer_id > 0) AS subquery
			ON sandbox.app_funding_rl.app_id = subquery.app_id;

	UPDATE sandbox.app_funding_rl
		SET loanpro_customer_id_sec = loanpro_customer_id
		FROM sandbox.app_funding_rl
		INNER JOIN 
			(SELECT a.app_id, loanpro_customer_id
			FROM IL_application AS a
			INNER JOIN IL_contact AS c ON c.app_id = a.app_id
			WHERE
				c.ac_role_tp_c = 'SEC' AND 
				c.loanpro_customer_id > 0) AS subquery
			ON sandbox.app_funding_rl.app_id = subquery.app_id;
			
UPDATE STATISTICS sandbox.app_funding_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_funding_checklist_rl ---------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_funding_checklist_rl
	(app_id, addendum_signed_pr_enum, addendum_signed_sec_enum, address_confirmed_flag, applicant_references_checked_flag, apr_within_guidelines_flag, 
	 check_requested_by_user, collateral_percent_used_confirmed_enum, collateral_worksheet_unit_confirmed_enum, contract_signed_pr_flag, 
	 contract_signed_sec_flag, correct_contract_state_flag, credit_app_signed_pr_enum, credit_app_signed_sec_enum, down_payment_approved_flag, 
	 drivers_license_confirmed_pr_enum, drivers_license_confirmed_sec_enum, drivers_license_dob_confirmed_pr_enum, drivers_license_dob_confirmed_sec_enum, 
	 guarantee_of_lien_enum, initials_presented_flag, insurance_deductible_within_policy_enum, insurance_mb_lienholder_enum, insurance_motor_vin_confirm_enum, 
	 insurance_rv_boat_vin_confirm_enum, insurance_trailer_vin_confirm_enum, itemization_confirmed_flag, motor_title_mb_lienholder_enum, 
	 motor_title_vin_confirmed_enum, motor_ucc_mb_lienholder_enum, motor_ucc_vin_enum, new_motor_1_invoice_confirmed_enum, 
	 new_motor_2_invoice_confirmed_enum, new_rv_boat_invoice_confirmed_enum, new_trailer_invoice_confirmed_enum, payment_schedule_confirmed_flag, 
	 payoff_mb_loan_verified_enum, paystub_expire_date_pr, paystub_expire_date_sec, rv_boat_title_mb_lienholder_enum, rv_boat_title_vin_confirmed_enum, 
	 rv_boat_ucc_mb_lienholder_enum, rv_boat_ucc_vin_confirmed_enum, unit_confirmed_flag, trailer_title_mb_lienholder_enum, trailer_title_vin_confirmed_enum, 
	 trailer_ucc_mb_lienholder_enum, trailer_ucc_vin_confirmed_enum, ucc_filed_by_mb_enum, verified_against_program_flag)
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN f.ct_addendum_signed_borr1 = 'Y' THEN 660
			WHEN f.ct_addendum_signed_borr1 = 'N' THEN 661
			WHEN f.ct_addendum_signed_borr1 = 'D' THEN 662
			ELSE NULL
		END AS addendum_signed_pr_enum,
		CASE
			WHEN f.ct_addendum_signed_borr2 = 'Y' THEN 660
			WHEN f.ct_addendum_signed_borr2 = 'N' THEN 661
			WHEN f.ct_addendum_signed_borr2 = 'D' THEN 662
			ELSE NULL
		END AS addendum_signed_sec_enum,
		CASE
			WHEN f.ct_address_confirmed = 'Y' THEN 1
			WHEN f.ct_address_confirmed = 'N' THEN 0
			ELSE NULL
		END AS address_confirmed_flag,
		CASE
			WHEN f.loan_reference1 = 'Y' THEN 1
			WHEN f.loan_reference1 = 'N' THEN 0
			ELSE NULL
		END AS applicant_references_checked_flag,
		CASE
			WHEN f.ct_apr_within_guidelines = 'Y' THEN 1
			WHEN f.ct_apr_within_guidelines = 'N' THEN 0
			ELSE NULL
		END AS apr_within_guidelines_flag,		
		CASE
			WHEN f.chk_requested_by LIKE '%WENDY%' OR f.chk_requested_by LIKE '%DOTSON%'	THEN 'WENDY.DOTSON@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%POTEZ%'											THEN 'ALYSSA.RAPOTEZ@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%ANGIE%'											THEN 'ANGIE.HAYS@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%ASHLEY%' OR f.chk_requested_by LIKE '%HAASE%'	THEN 'ASHLEY.HAASE@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%SIPLINGER%'										THEN 'BRIANN.SIPLINGER@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%CHARISSA%'										THEN 'CHARISSA.GREEN@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%CINDY%' OR f.chk_requested_by LIKE '%BEASON%'	THEN 'CINDY.BEASON@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%DIANA%' OR f.chk_requested_by LIKE '%JOHNS%'		THEN 'DIANA.JOHNS@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%JONA%'											THEN 'JONA.KELLER@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%KATIE%' OR f.chk_requested_by LIKE '%VANCE%'		THEN 'KATIE.VANCE@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%KARISSA%'										THEN 'KARISSA.WHITE@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%KRISTY%'											THEN 'KRISTY.LOTTE@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%MARIA%' OR f.chk_requested_by LIKE '%CAMPOS%'	THEN 'MARIA.CAMPOS@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%HDYE%' OR f.chk_requested_by LIKE '%HYDE%'		THEN 'MIA.HYDE@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%PRESTON%'										THEN 'MICHELLE.PRESTON@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE 'PAM%' OR f.chk_requested_by LIKE '%MIETCHEN%'		THEN 'PAM.MIETCHEN@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%BITTLE%'											THEN 'SHERRY.BITTLE@MERRICKBANK.COM'
			WHEN f.chk_requested_by LIKE '%CARTER%'											THEN 'SHAUNA.CARTER@MERRICKBANK.COM'
			ELSE (SELECT TOP (1) UPPER(RTRIM(email_address)) FROM g_user_profile WHERE g_user_profile.loan_officer_code = chk_requested_by AND g_user_profile.loan_officer_code <> '')
		END AS check_requested_by_user,
		CASE
			WHEN f.ct_addendum_signed_borr2 = 'Y' THEN 660
			WHEN f.ct_addendum_signed_borr2 = 'N' THEN 661
			WHEN f.ct_addendum_signed_borr2 = 'D' THEN 662
			ELSE NULL
		END AS collateral_percent_used_confirmed_enum,
		CASE
			WHEN f.collateral_ws_unit_confirmation = 'Y' THEN 660
			WHEN f.collateral_ws_unit_confirmation = 'N' THEN 661
			WHEN f.collateral_ws_unit_confirmation = 'D' THEN 662
			ELSE NULL
		END AS collateral_worksheet_unit_confirmed_enum,
		CASE
			WHEN f.ct_signed_borrower1 = 'Y' THEN 1
			WHEN f.ct_signed_borrower1 = 'N' THEN 0
			ELSE NULL
		END AS contract_signed_pr_flag,
		CASE
			WHEN f.ct_signed_borrower2 = 'Y' THEN 1
			WHEN f.ct_signed_borrower2 = 'N' THEN 0
			ELSE NULL
		END AS contract_signed_sec_flag,
		CASE
			WHEN f.ct_signed_borrower2 = 'Y' THEN 1
			WHEN f.ct_signed_borrower2 = 'N' THEN 0
			ELSE NULL
		END AS correct_contract_state_flag,
		CASE
			WHEN f.app_signed_borrower1 = 'Y' THEN 660
			WHEN f.app_signed_borrower1 = 'N' THEN 661
			WHEN f.app_signed_borrower1 = 'D' THEN 662
			ELSE NULL
		END AS credit_app_signed_pr_enum,
		CASE
			WHEN f.app_signed_borrower2 = 'Y' THEN 660
			WHEN f.app_signed_borrower2 = 'N' THEN 661
			WHEN f.app_signed_borrower2 = 'D' THEN 662
			ELSE NULL
		END AS credit_app_signed_sec_enum,
		CASE
			WHEN f.loan_down_pymt_approved = 'Y' THEN 1
			WHEN f.loan_down_pymt_approved = 'N' THEN 0
			ELSE NULL
		END AS down_payment_approved_flag,		
		CASE
			WHEN f.dl_borrower1 = 'Y' THEN 660
			WHEN f.dl_borrower1 = 'N' THEN 661
			WHEN f.dl_borrower1 = 'D' THEN 662
			ELSE NULL
		END AS drivers_license_confirmed_pr_enum,
		CASE
			WHEN f.dl_borrower2 = 'Y' THEN 660
			WHEN f.dl_borrower2 = 'N' THEN 661
			WHEN f.dl_borrower2 = 'D' THEN 662
			ELSE NULL
		END AS drivers_license_confirmed_sec_enum,
		CASE
			WHEN f.dl_borrower1_dob_confirmed = 'Y' THEN 660
			WHEN f.dl_borrower1_dob_confirmed = 'N' THEN 661
			WHEN f.dl_borrower1_dob_confirmed = 'D' THEN 662
			ELSE NULL
		END AS drivers_license_dob_confirmed_pr_enum,
		CASE
			WHEN f.dl_borrower2_dob_confirmed = 'Y' THEN 660
			WHEN f.dl_borrower2_dob_confirmed = 'N' THEN 661
			WHEN f.dl_borrower2_dob_confirmed = 'D' THEN 662
			ELSE NULL
		END AS drivers_license_dob_confirmed_sec_enum,
		CASE
			WHEN f.guarantee_of_lien = 'Y' THEN 660
			WHEN f.guarantee_of_lien = 'N' THEN 661
			WHEN f.guarantee_of_lien = 'D' THEN 662
			ELSE NULL
		END AS guarantee_of_lien_enum,
		CASE
			WHEN f.ct_initials_presented = 'Y' THEN 1
			WHEN f.ct_initials_presented = 'N' THEN 0
			ELSE NULL
		END AS initials_presented_flag,
		CASE
			WHEN f.ins_deductible_within_policy = 'Y' THEN 660
			WHEN f.ins_deductible_within_policy = 'N' THEN 661
			WHEN f.ins_deductible_within_policy = 'D' THEN 662
			ELSE NULL
		END AS insurance_deductible_within_policy_enum,
		CASE
			WHEN f.ins_mb_lienholder = 'Y' THEN 660
			WHEN f.ins_mb_lienholder = 'N' THEN 661
			WHEN f.ins_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS insurance_mb_lienholder_enum, 
		CASE
			WHEN f.ins_motor_vin_confirm = 'Y' THEN 660
			WHEN f.ins_motor_vin_confirm = 'N' THEN 661
			WHEN f.ins_motor_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS insurance_motor_vin_confirm_enum,
		CASE
			WHEN f.ins_rv_boat_vin_confirm = 'Y' THEN 660
			WHEN f.ins_rv_boat_vin_confirm = 'N' THEN 661
			WHEN f.ins_rv_boat_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS insurance_rv_boat_vin_confirm_enum, 
		CASE
			WHEN f.ins_trailer_vin_confirm = 'Y' THEN 660
			WHEN f.ins_trailer_vin_confirm = 'N' THEN 661
			WHEN f.ins_trailer_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS insurance_trailer_vin_confirm_enum, 
		CASE
			WHEN f.ct_itemization_confirmed = 'Y' THEN 1
			WHEN f.ct_itemization_confirmed = 'N' THEN 0
			ELSE NULL
		END AS itemization_confirmed_flag, 
		CASE
			WHEN f.motor_title_mb_lienholder = 'Y' THEN 660
			WHEN f.motor_title_mb_lienholder = 'N' THEN 661
			WHEN f.motor_title_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS motor_title_mb_lienholder_enum,
		CASE
			WHEN f.motor_title_vin_confirm = 'Y' THEN 660
			WHEN f.motor_title_vin_confirm = 'N' THEN 661
			WHEN f.motor_title_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS motor_title_vin_confirmed_enum, 
		CASE
			WHEN f.motor_ucc1_mb_lienholder = 'Y' THEN 660
			WHEN f.motor_ucc1_mb_lienholder = 'N' THEN 661
			WHEN f.motor_ucc1_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS motor_ucc_mb_lienholder_enum, 
		CASE
			WHEN f.motor_ucc1_vin_confirm = 'Y' THEN 660
			WHEN f.motor_ucc1_vin_confirm = 'N' THEN 661
			WHEN f.motor_ucc1_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS motor_ucc_vin_enum, 
		CASE
			WHEN f.new_motor_invoice_confirmed = 'Y' THEN 660
			WHEN f.new_motor_invoice_confirmed = 'N' THEN 661
			WHEN f.new_motor_invoice_confirmed = 'D' THEN 662
			ELSE NULL
		END AS new_motor_1_invoice_confirmed_enum, 
		CASE
			WHEN f.new_motor2_invoice_confirmed = 'Y' THEN 660
			WHEN f.new_motor2_invoice_confirmed = 'N' THEN 661
			WHEN f.new_motor2_invoice_confirmed = 'D' THEN 662
			ELSE NULL
		END AS new_motor_2_invoice_confirmed_enum, 
		CASE
			WHEN f.new_rv_boat_invoice_confirmed = 'Y' THEN 660
			WHEN f.new_rv_boat_invoice_confirmed = 'N' THEN 661
			WHEN f.new_rv_boat_invoice_confirmed = 'D' THEN 662
			ELSE NULL
		END AS new_rv_boat_invoice_confirmed_enum, 
		CASE
			WHEN f.new_trailer_invoice_confirmed = 'Y' THEN 660
			WHEN f.new_trailer_invoice_confirmed = 'N' THEN 661
			WHEN f.new_trailer_invoice_confirmed = 'D' THEN 662
			ELSE NULL
		END AS new_trailer_invoice_confirmed_enum, 
		CASE
			WHEN f.ct_pymt_schedule_confirmed = 'Y' THEN 1
			WHEN f.ct_pymt_schedule_confirmed = 'N' THEN 0
			ELSE NULL
		END AS payment_schedule_confirmed_flag,
		CASE
			WHEN f.payoff_loan_verified = 'Y' THEN 660
			WHEN f.payoff_loan_verified = 'N' THEN 661
			WHEN f.payoff_loan_verified = 'D' THEN 662
			ELSE NULL
		END AS payoff_mb_loan_verified_enum, 
		CASE WHEN
			ISDATE(applicant_paystub_expire) = 1 THEN applicant_paystub_expire
			ELSE NULL
		END AS paystub_expire_date_pr, 
		CASE WHEN
			ISDATE(coapplicant_paystub_expire) = 1 THEN coapplicant_paystub_expire
			ELSE NULL
		END AS paystub_expire_date_sec, 
		CASE
			WHEN f.rv_boat_title_mb_lienholder = 'Y' THEN 660
			WHEN f.rv_boat_title_mb_lienholder = 'N' THEN 661
			WHEN f.rv_boat_title_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS rv_boat_title_mb_lienholder_enum, 
		CASE
			WHEN f.rv_boat_title_vin_confirm = 'Y' THEN 660
			WHEN f.rv_boat_title_vin_confirm = 'N' THEN 661
			WHEN f.rv_boat_title_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS rv_boat_title_vin_confirmed_enum, 
		CASE
			WHEN f.rv_boat_ucc1_mb_lienholder = 'Y' THEN 660
			WHEN f.rv_boat_ucc1_mb_lienholder = 'N' THEN 661
			WHEN f.rv_boat_ucc1_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS rv_boat_ucc_mb_lienholder_enum, 
		CASE
			WHEN f.rv_boat_ucc1_mb_lienholder = 'Y' THEN 660
			WHEN f.rv_boat_ucc1_mb_lienholder = 'N' THEN 661
			WHEN f.rv_boat_ucc1_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS rv_boat_ucc_vin_confirmed_enum, 
		CASE
			WHEN f.loan_unit_confirmed = 'Y' THEN 1
			WHEN f.loan_unit_confirmed = 'N' THEN 0
			ELSE NULL
		END AS unit_confirmed_flag, 		
		CASE
			WHEN f.trailer_title_mb_lienholder = 'Y' THEN 660
			WHEN f.trailer_title_mb_lienholder = 'N' THEN 661
			WHEN f.trailer_title_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS trailer_title_mb_lienholder_enum, 
		CASE
			WHEN f.trailer_title_vin_confirm = 'Y' THEN 660
			WHEN f.trailer_title_vin_confirm = 'N' THEN 661
			WHEN f.trailer_title_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS trailer_title_vin_confirmed_enum, 
		CASE
			WHEN f.trailer_ucc1_mb_lienholder = 'Y' THEN 660
			WHEN f.trailer_ucc1_mb_lienholder = 'N' THEN 661
			WHEN f.trailer_ucc1_mb_lienholder = 'D' THEN 662
			ELSE NULL
		END AS trailer_ucc_mb_lienholder_enum, 
		CASE
			WHEN f.trailer_ucc1_vin_confirm = 'Y' THEN 660
			WHEN f.trailer_ucc1_vin_confirm = 'N' THEN 661
			WHEN f.trailer_ucc1_vin_confirm = 'D' THEN 662
			ELSE NULL
		END AS trailer_ucc_vin_confirmed_enum, 
		CASE
			WHEN f.ucc1_filed_by_Merrick = 'Y' THEN 660
			WHEN f.ucc1_filed_by_Merrick = 'N' THEN 661
			WHEN f.ucc1_filed_by_Merrick = 'D' THEN 662
			ELSE NULL
		END AS ucc_filed_by_mb_enum, 
		CASE
			WHEN f.ct_verified_against_program = 'Y' THEN 1
			WHEN f.ct_verified_against_program = 'N' THEN 0
			ELSE NULL
		END	AS verified_against_program_flag
	FROM IL_application AS a
	LEFT JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	LEFT JOIN IL_ITI_control AS c ON c.app_id = a.app_id
	LEFT JOIN IL_fund_checklist AS f ON f.app_id = a.app_id
	WHERE
		-- Make sure we're not just populating this with blank data
		LEN(f.ct_pymt_schedule_confirmed) > 0 OR LEN(f.chk_requested_by) > 0 OR LEN(f.ct_signed_borrower1) > 0 OR 
		LEN(f.loan_down_pymt_approved) > 0 OR LEN(f.ct_address_confirmed) > 0 OR LEN(f.loan_unit_confirmed) > 0;

UPDATE STATISTICS sandbox.app_funding_checklist_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_funding_contract_rl ----------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_funding_contract_rl
	(app_id, apr, cash_down_payment, cash_proceeds, contract_state, down_payment_percentage, document_tax_fee, document_prep_fee, finance_charge, 
	 first_payment_date, first_payment_by_dealer, income_expiration_date, license_fee, loan_to_value_percentage, loan_to_value_percentage_with_fees, 
	 net_tradein_allowance, note_signed_date, note_payment_amount, other_dealer_fee_1, other_dealer_fee_2, other_dealer_fee_3, 
	 other_dealer_fee_4, other_dealer_fee_5, other_dealer_fee_6, other_public_official_fee_1, other_public_official_fee_2, other_public_official_fee_3, 
	 payoff_mb_loan_amount, payoff_mb_loan_number, registration_fee, sale_price, taxes, title_fee, titled_in_state, total_amount_financed, 
	 total_dealer_proceeds, ucc_fee, ucc_principal_refund)
	SELECT DISTINCT
		a.app_id,
		f.ct_rate_over_split AS apr,
		f.ct_cash_down_payment AS cash_down_payment,
		f.ct_cash_proceeds AS cash_proceeds,
		f.ct_contract_state AS contract_state,
		f.ct_down_pymt_percentage AS down_payment_percentage,
		CASE
			WHEN f.ct_fee_Florida_doc_stamp_tax > 0 THEN f.ct_fee_Florida_doc_stamp_tax
			ELSE NULL
		END AS document_tax_fee,
		CASE
			WHEN f.document_prep_fee > 0 THEN f.document_prep_fee
			ELSE NULL
		END AS document_prep_fee,
		f.finance_charge AS finance_charge,
		n.payment_date AS first_payment_date,
		CASE
			WHEN f.ct_first_pymnt_by_dlr > 0 THEN f.ct_first_pymnt_by_dlr
			ELSE NULL
		END AS first_payment_by_dealer,
		f.inc_fund_expiration_date AS income_expiration_date,
		CASE
			WHEN f.license_fee > 0 THEN f.license_fee
			ELSE NULL
		END AS license_fee,
		f.ct_loan_to_value_percentage AS loan_to_value_percentage,
		f.ct_loan_to_value_percentage_with_fees AS loan_to_value_percentage_with_fees,
		CASE
			WHEN f.ct_net_tradein_allowance > 0 THEN f.ct_net_tradein_allowance
			ELSE NULL
		END AS net_tradein_allowance,
		f.ct_note_date AS note_signed_date,
		f.ct_note_pymt_amount AS note_payment_amount,
		CASE
			WHEN f.other_dealer_fees_1 > 0 THEN f.other_dealer_fees_1
			ELSE NULL
		END AS other_dealer_fee_1,
		CASE
			WHEN f.other_dealer_fees_2 > 0 THEN f.other_dealer_fees_2
			ELSE NULL
		END AS other_dealer_fee_2,
		CASE
			WHEN f.other_dealer_fees_3 > 0 THEN f.other_dealer_fees_3
			ELSE NULL
		END AS other_dealer_fee_3,
		CASE
			WHEN f.other_dealer_fees_4 > 0 THEN f.other_dealer_fees_4
			ELSE NULL
		END AS other_dealer_fee_4,
		CASE
			WHEN f.other_dealer_fees_5 > 0 THEN f.other_dealer_fees_5
			ELSE NULL
		END AS other_dealer_fee_5,
		CASE
			WHEN f.other_dealer_fees_6 > 0 THEN f.other_dealer_fees_6
			ELSE NULL
		END AS other_dealer_fee_6,
		CASE
			WHEN f.other_public_official_fee_1 > 0 THEN f.other_public_official_fee_1
			ELSE NULL
		END AS other_public_official_fee_1,
		CASE
			WHEN f.other_public_official_fee_2 > 0 THEN f.other_public_official_fee_2
			ELSE NULL
		END AS other_public_official_fee_2,
		CASE
			WHEN f.other_public_official_fee_3 > 0 THEN f.other_public_official_fee_3
			ELSE NULL
		END AS other_public_official_fee_3,
		CASE
			WHEN f.payoff_amount > 0 THEN f.payoff_amount
			ELSE NULL
		END AS payoff_mb_loan_amount,
		f.payoff_loan_number AS payoff_mb_loan_number,
		CASE
			WHEN f.registration_fee > 0 THEN f.registration_fee
			ELSE NULL
		END AS registration_fee,
		f.ct_sale_price AS sale_price,
		CASE
			WHEN f.taxes > 0 THEN f.taxes
			ELSE NULL
		END AS taxes,
		CASE
			WHEN f.title_fee > 0 THEN f.title_fee
			ELSE NULL
		END AS title_fee,
		f.ct_titled_in_state AS titled_in_state,
		f.total_amount_finances AS total_amount_financed,
		f.ct_total_dealer_proceeds AS total_dealer_proceeds,
		CASE
			WHEN f.ct_fee_ucc1 > 0 THEN f.ct_fee_ucc1
			ELSE NULL
		END AS ucc_fee,
		CASE
			WHEN f.ct_UCC_prin_refund > 0 THEN f.ct_UCC_prin_refund
			ELSE NULL
		END AS ucc_principal_refund		
	FROM IL_application AS a
	LEFT JOIN IL_ITI_note AS n ON n.app_id = a.app_id
	LEFT JOIN IL_ITI_payment_sched AS p ON p.app_id = a.app_id
	LEFT JOIN IL_fund_checklist AS f ON f.app_id = a.app_id
	WHERE
		-- Make sure we're not just populating this with blank data
		-- MAYBE THIS PARTICULAR TABLE SHOULD ONLY HAVE process > 40800 ??
		LEN(f.ct_pymt_schedule_confirmed) > 0 OR LEN(f.chk_requested_by) > 0 OR LEN(f.ct_signed_borrower1) > 0 OR 
		LEN(f.loan_down_pymt_approved) > 0 OR LEN(f.ct_address_confirmed) > 0 OR LEN(f.loan_unit_confirmed) > 0;

UPDATE STATISTICS sandbox.app_funding_contract_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_warranties_rl: credit disability ---------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.credit_disability_amount,
		p.credit_disability_company,
		CASE
			WHEN p.credit_disability_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.credit_disability_term IS NULL THEN 0
			ELSE p.credit_disability_term
		END AS credit_disability_term,
		p.credit_disability_policy,
		620
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.credit_disability_company <> '' AND p.credit_disability_amount > 0;

-- app_warranties_rl: credit life ---------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.credit_life_amount,
		p.credit_life_company,
		CASE
			WHEN p.credit_life_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.credit_life_term IS NULL THEN 0
			ELSE p.credit_life_term
		END AS credit_life_term,
		p.credit_life_policy,
		621
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.credit_life_company <> '' AND p.credit_life_amount > 0;

-- app_warranties_rl: extended warranty --------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.ext_warranty_amount,
		p.ext_warranty_company,
		CASE
			WHEN p.ext_warranty_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.ext_warranty_term IS NULL THEN 0
			ELSE p.ext_warranty_term
		END AS ext_warranty_term,
		p.ext_warranty_policy,
		622
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.ext_warranty_company <> '' AND p.ext_warranty_amount > 0;

-- app_warranties_rl: gap insurance ---------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.gap_amount,
		p.gap_company,
		CASE
			WHEN p.gap_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.gap_term IS NULL THEN 0
			ELSE p.gap_term
		END AS gap_term,
		p.gap_policy,
		623
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.gap_company <> '' AND p.gap_amount > 0;

-- app_warranties_rl: other ------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.other_amount,
		p.other_company,
		CASE
			WHEN p.other_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.other_term IS NULL THEN 0
			ELSE p.other_term
		END AS other_term,
		p.other_policy,
		624
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.other_company <> '' AND p.other_amount > 0;

-- app_warranties_rl: road side assistance ------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.road_side_amount,
		p.road_side_company,
		CASE
			WHEN p.road_side_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.road_side_term IS NULL THEN 0
			ELSE p.road_side_term
		END AS road_side_term,
		p.road_side_policy,
		625
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.road_side_company <> '' AND p.road_side_amount > 0;

-- app_warranties_rl: service contract ---------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_warranties_rl
	(app_id, amount, company_name, merrick_lienholder_flag, term_months, policy_number, warranty_type_enum)
	SELECT DISTINCT
		a.app_id,
		p.service_contract_amount,
		p.service_contract_company,
		CASE
			WHEN p.service_contract_lien = 'Y'	THEN 1
			ELSE 0
		END,
		CASE
			WHEN p.service_contract_term IS NULL THEN 0
			ELSE p.service_contract_term
		END AS service_contract_term,
		p.service_contract_policy,
		626
	FROM IL_application AS a
	INNER JOIN IL_backend_policies AS p ON p.app_id = a.app_id
	WHERE p.service_contract_company <> '' AND p.service_contract_amount > 0;

UPDATE STATISTICS sandbox.app_warranties_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_policy_exceptions_rl: capacity -----------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_policy_exceptions_rl
	(app_id, notes, policy_exception_type_enum, reason_code)
	SELECT 
		a.app_id,
		d.capacity_exception_notes,
		630,
		d.override_capacity
	FROM IL_application AS a
	INNER JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	WHERE LEN(d.override_capacity) > 0;

-- app_policy_exceptions_rl: collateral ----------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_policy_exceptions_rl
	(app_id, notes, policy_exception_type_enum, reason_code)
	SELECT 
		a.app_id,
		d.collateral_program_exception_notes,
		631,
		d.override_collateral_program
	FROM IL_application AS a
	INNER JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	WHERE LEN(d.override_collateral_program) > 0;

-- app_policy_exceptions_rl: credit --------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_policy_exceptions_rl
	(app_id, notes, policy_exception_type_enum, reason_code)
	SELECT 
		a.app_id,
		d.credit_exception_notes,
		632,
		d.override_credit
	FROM IL_application AS a
	INNER JOIN IL_app_decision_info AS d ON d.app_id = a.app_id
	WHERE LEN(d.override_credit) > 0;

UPDATE STATISTICS sandbox.app_policy_exceptions_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_collateral_rl: #1 ------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_collateral_rl
	(app_id, collateral_type_enum, [length], make, mileage, model, motor_size, used_flag, option_1_description, 
	 option_1_value, option_2_description, option_2_value, sort_order, vin, wholesale_value, [year])
	SELECT
		a.app_id,
		-- This collateral type sniffing is just handy for the near-future implementation, but lets try to categorize it correctly
		CASE
			WHEN RTRIM(a.app_type_code) = 'MARINE'	THEN	411	-- BOAT (MARINE)
			WHEN RTRIM(a.app_type_code) = 'RV'		THEN	418	-- RV
			WHEN RTRIM(a.app_type_code) = 'HT'		THEN	415	-- HORSE TRAILER
			WHEN RTRIM(a.app_type_code) = 'UT'		THEN	421	-- MOTORCYCLE
			WHEN RTRIM(a.app_type_code) = 'MC'		THEN	416	-- UTILITY TRAILER
			-- sub-types for OR's
			WHEN RTRIM(a.app_type_code) = 'OR' AND a.sub_type_code = 'ATV'			THEN	410	-- ATV
			WHEN RTRIM(a.app_type_code) = 'OR' AND a.sub_type_code = 'UTV'			THEN	422	-- UTV
			WHEN RTRIM(a.app_type_code) = 'OR' AND a.sub_type_code = 'PWC'			THEN	417	-- PWC
			WHEN RTRIM(a.app_type_code) = 'OR' AND a.sub_type_code = 'SNOWMOBILE'	THEN	419	-- SNOWMOBILE
			ELSE 423 -- UNDETERMINED
		END AS collateral_type_enum,
		NULL AS [length],
		c.coll1_make AS make,
		NULL AS mileage,
		c.coll1_model AS model,
		NULL AS motor_size,
		CASE
			WHEN c.coll1_new_used_demo IN ('U', 'D') THEN 1
			ELSE 0
		END AS used_flag,
		CASE
			WHEN c.coll_option1_desc <> ''	THEN c.coll_option1_desc
			ELSE NULL
		END AS option_1_description, 
		CASE
			WHEN c.coll_option1 > 0	THEN c.coll_option1
			ELSE NULL
		END AS option_1_value, 
		CASE
			WHEN c.coll_option2_desc <> ''	THEN c.coll_option2_desc
			ELSE NULL
		END AS option_2_description, 
		CASE
			WHEN c.coll_option2 > 0	THEN c.coll_option2
			ELSE NULL
		END AS option_2_value,
		1 AS sort_order,
		CASE
			WHEN c.coll1_VIN <> ''	THEN RTRIM(c.coll1_VIN) 
		END AS vin,
		CASE
			WHEN c.coll1_value > 0 THEN c.coll1_value
			ELSE NULL
		END AS wholesale_value,
		c.coll1_year
	FROM IL_application AS a
	INNER JOIN IL_collateral AS c ON c.app_id = a.app_id
	WHERE c.coll1_year > 0 AND c.coll1_make <> '';
	
-- app_collateral_rl: #2 ------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_collateral_rl
	(app_id, collateral_type_enum, [length], make, mileage, model, motor_size, used_flag, option_1_description, 
	 option_1_value, option_2_description, option_2_value, sort_order, vin, wholesale_value, [year])
	SELECT
		a.app_id,
		-- This collateral type sniffing is just handy for the near-future implementation, but lets try to categorize it correctly
		CASE
			WHEN RTRIM(a.app_type_code) = 'MARINE' OR coll2_HP_Marine > 0	THEN	412	-- ENGINE-1 (MARINE)
			ELSE 423 -- UNDETERMINED
		END AS collateral_type_enum,
		NULL AS [length],
		c.coll2_make,
		NULL AS mileage,
		c.coll2_model AS model,
		coll2_HP_Marine AS motor_size,
		CASE
			WHEN c.coll2_new_used_demo IN ('U', 'D') THEN 1
			ELSE 0
		END AS used_flag,
		CASE
			WHEN c.coll_option3_desc <> ''	THEN c.coll_option3_desc
			ELSE NULL
		END AS option_1_description, 
		CASE
			WHEN c.coll_option3 > 0	THEN c.coll_option3
			ELSE NULL
		END AS option_1_value,
		CASE
			WHEN c.coll_option4_desc <> ''	THEN c.coll_option4_desc
			ELSE NULL
		END AS option_2_description, 
		CASE
			WHEN c.coll_option4 > 0	THEN c.coll_option4
			ELSE NULL
		END AS option_2_value,
		2 AS sort_order,
		CASE
			WHEN c.coll2_VIN <> ''	THEN RTRIM(c.coll2_VIN) 
		END AS vin,
		CASE
			WHEN c.coll2_value > 0 THEN c.coll2_value
			ELSE NULL
		END AS wholesale_value,
		c.coll2_year
	FROM IL_application AS a
	INNER JOIN IL_collateral AS c ON c.app_id = a.app_id
	WHERE c.coll2_year > 0 AND c.coll2_make <> '';
	
-- app_collateral_rl: #3 ------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_collateral_rl
	(app_id, collateral_type_enum, [length], make, mileage, model, motor_size, used_flag, option_1_description, 
	 option_1_value, option_2_description, option_2_value, sort_order, vin, wholesale_value, [year])
	SELECT
		a.app_id,
		-- This collateral type sniffing is just handy for the near-future implementation, but lets try to categorize it correctly
		-- with position 3, it could be a boat motor or a boat trailer really
		CASE
			-- Obvious popular trailer companies
			WHEN RTRIM(a.app_type_code) = 'MARINE' AND c.coll3_make IN ('BT', 'BEAR', 'BOATMATE', 'BACKTRACK', 'TRAILSTAR', 'MAGIC TILT', 'MARINE MASTER', 'SHORELANDER', 'SHORELANDR', 'EZ LOADER', 'KARAVAN', 'MCCLAIN', 
				'ESCORT', 'ROAD RUNNER', 'LOAD RITE', 'LOADRITE', 'MAGIC LOADER', 'MALIBU', 'ZIEMAN', 'TRACKER', 'DIAMOND CITY', 'RANGER', 'WESCO', 'TRAILER') THEN 420 -- TRAILER
			-- Super good chance if it's not a trailer and there's some horsepower, it's an engine
			WHEN coll3_HP_Marine > 0	THEN	413	-- ENGINE-2 (MARINE)
			-- Obvious popular engines
			WHEN RTRIM(a.app_type_code) = 'MARINE' AND c.coll3_make IN ('MERCURY', 'YAMAHA', 'MERCRUISER')	THEN 412
			ELSE 423 -- UNDETERMINED
		END AS collateral_type_enum,
		NULL AS [length],
		c.coll3_make,
		NULL AS mileage,
		c.coll3_model AS model,
		coll3_HP_Marine AS motor_size,
		CASE
			WHEN c.coll3_new_used_demo IN ('U', 'D') THEN 1
			ELSE 0
		END AS used_flag,
		CASE
			WHEN c.coll_option5_desc <> ''	THEN c.coll_option5_desc
			ELSE NULL
		END AS option_1_description, 
		CASE
			WHEN c.coll_option5 > 0	THEN c.coll_option5
			ELSE NULL
		END AS option_1_value,
		CASE
			WHEN c.coll_option6_desc <> ''	THEN c.coll_option6_desc
			ELSE NULL
		END AS option_2_description, 
		CASE
			WHEN c.coll_option6 > 0	THEN c.coll_option6
			ELSE NULL
		END AS option_2_value,
		3 AS sort_order,
		CASE
			WHEN c.coll3_VIN <> ''	THEN RTRIM(c.coll3_VIN) 
		END AS vin,
		CASE
			WHEN c.coll3_value > 0 THEN c.coll3_value
			ELSE NULL
		END AS wholesale_value,
		c.coll3_year
	FROM IL_application AS a
	INNER JOIN IL_collateral AS c ON c.app_id = a.app_id
	WHERE c.coll3_year > 0 AND c.coll3_make <> '';
	

-- app_collateral_rl: #4 ------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_collateral_rl
	(app_id, collateral_type_enum, [length], make, mileage, model, motor_size, used_flag, option_1_description, 
	 option_1_value, option_2_description, option_2_value, sort_order, vin, wholesale_value, [year])
	SELECT
		a.app_id,
		-- This collateral type sniffing is just handy for the near-future implementation, but lets try to categorize it correctly
		-- with position 4, it should be a boat trailer really (but there are a few 3rd motors)
		CASE
			-- Exclue some obvious popular engines
			WHEN RTRIM(a.app_type_code) = 'MARINE' AND c.coll4_make IN ('MERCURY', 'YAMAHA', 'MERCRUISER')	THEN 414	-- ENGINE-3 (MARINE)
			WHEN RTRIM(a.app_type_code) = 'MARINE' THEN 420	-- TRAILER
			ELSE 423 -- UNDETERMINED
		END AS collateral_type_enum,
		NULL AS [length],
		c.coll4_make,
		NULL AS mileage,
		c.coll4_model AS model,
		NULL AS motor_size,
		CASE
			WHEN c.coll4_new_used_demo IN ('U', 'D') THEN 1
			ELSE 0
		END AS used_flag,
		CASE
			WHEN c.coll_option7_desc <> ''	THEN c.coll_option7_desc
			ELSE NULL
		END AS option_1_description, 
		CASE
			WHEN c.coll_option7 > 0	THEN c.coll_option7
			ELSE NULL
		END AS option_1_value,
		CASE
			WHEN c.coll_option8_desc <> ''	THEN c.coll_option8_desc
			ELSE NULL
		END AS option_2_description, 
		CASE
			WHEN c.coll_option8 > 0	THEN c.coll_option8
			ELSE NULL
		END AS option_2_value,
		4 AS sort_order,
		CASE
			WHEN c.coll4_VIN <> ''	THEN RTRIM(c.coll4_VIN) 
		END AS vin,
		CASE
			WHEN c.coll4_value > 0 THEN c.coll4_value
			ELSE NULL
		END AS wholesale_value,
		c.coll4_year
	FROM IL_application AS a
	INNER JOIN IL_collateral AS c ON c.app_id = a.app_id
	WHERE c.coll4_year > 0 AND c.coll4_make <> '';
	

UPDATE STATISTICS sandbox.app_collateral_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- app_dealer_rl --------------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.app_dealer_rl
	(app_id, broker_flag, bank_account_num, bank_account_type_enum, bank_routing_num, bank_phone, bank_name, dealer_address_line_1, 
 	 dealer_city, dealer_email, dealer_fax, dealer_name, dealer_num_child, dealer_num_parent, dealer_phone, dealer_state, dealer_zip, 
	 fsp_email, fsp_fax, fsp_name, fsp_num, fsp_phone)
	SELECT DISTINCT
		a.app_id,
		CASE
			WHEN a.dlr_broker = 'Y'	THEN 1
			ELSE 0
		END AS broker_flag,
		CASE
			WHEN ISNUMERIC(RTRIM(LEFT(d.dlr_account_num, 20))) = 1	THEN RTRIM(LEFT(d.dlr_account_num, 20)) 
			ELSE NULL
		END AS bank_account_num,
		CASE
			WHEN d.dlr_check_or_sav = '22'	THEN 650
			WHEN d.dlr_check_or_sav = '32'	THEN 651
			ELSE NULL
		END AS bank_account_type_enum,
		CASE
			WHEN ISNUMERIC(RTRIM(LEFT(d.dlr_aba, 9))) = 1	THEN RTRIM(LEFT(d.dlr_aba, 9)) 
			ELSE NULL
		END AS bank_routing_num,
		CASE
			WHEN LEN(RTRIM(d.dlr_bank_phone)) > 0 THEN RTRIM(REPLACE(REPLACE(REPLACE(d.dlr_bank_phone, '-', ''), ')', ''), '(', ''))
			ELSE NULL
		END AS bank_phone,
		CASE
			WHEN LEN(RTRIM(d.dlr_bank_name)) > 0 THEN RTRIM(d.dlr_bank_name)
			ELSE NULL
		END AS bank_name,
		a.dlr_address_line1 AS dealer_address_line_1,
		RTRIM(a.dlr_city) AS dealer_city,
		CASE
			WHEN LEN(RTRIM(a.fsp_name)) = 0 AND LEN(RTRIM(a.dlr_email)) > 0 THEN a.dlr_email
			ELSE NULL
		END AS dealer_email,
		CASE
			WHEN LEN(RTRIM(a.fsp_name)) = 0 AND LEN(RTRIM(a.dlr_fax)) > 0 THEN RTRIM(REPLACE(REPLACE(REPLACE(a.dlr_fax, '-', ''), ')', ''), '(', ''))
			ELSE NULL
		END AS dealer_fax,
		RTRIM(a.dlr_name) AS dealer_name,
		CASE
			WHEN LEN(a.dlr_num_marine) > 0	THEN	a.dlr_num_marine
			WHEN LEN(a.dlr_num_rv) > 0		THEN	a.dlr_num_rv
			WHEN LEN(a.dlr_num_trailer) > 0 THEN	a.dlr_num_trailer
			WHEN LEN(a.dlr_num_or) > 0		THEN	a.dlr_num_or
			WHEN LEN(a.dlr_num_ht) > 0		THEN	a.dlr_num_ht
			WHEN LEN(a.dlr_num_mc) > 0		THEN	a.dlr_num_mc
			-- ok, there are a few applications with no dlr_num, but we're going to keep the NOT NULL constraint because... c'mon
			ELSE 0
		END AS dealer_num_child,
		CASE
			-- ok, there are a few applications with no dlr_num, but we're going to keep the NOT NULL constraint because... c'mon
			WHEN d.dlr_num IS NULL THEN 0
			ELSE d.dlr_num
		END AS dealer_num_parent,
		RTRIM(REPLACE(REPLACE(REPLACE(a.dlr_phone, '-', ''), ')', ''), '(', '')) AS dealer_phone,
		a.dlr_state AS dealer_state,
		a.dlr_zipcode AS dealer_zip,
		CASE
			WHEN LEN(RTRIM(a.fsp_name)) > 0 AND LEN(RTRIM(a.dlr_email)) > 0 THEN a.dlr_email
			ELSE NULL
		END AS fsp_email,
		CASE
			WHEN LEN(RTRIM(a.fsp_name)) > 0 AND LEN(RTRIM(a.dlr_fax)) > 0 THEN RTRIM(REPLACE(REPLACE(REPLACE(a.dlr_fax, '-', ''), ')', ''), '(', ''))
			ELSE NULL
		END AS fsp_fax,
		CASE
			WHEN LEN(RTRIM(a.fsp_name)) > 0 THEN RTRIM(a.fsp_name)
			ELSE NULL
		END AS fsp_name,
		CASE
			WHEN LEN(RTRIM(d.dlr_fsp_num)) > 0 THEN RTRIM(d.dlr_fsp_num)
			ELSE NULL
		END AS fsp_num,
		CASE
			WHEN LEN(RTRIM(a.fsp_phone)) > 0 THEN RTRIM(REPLACE(REPLACE(REPLACE(a.fsp_phone, '-', ''), ')', ''), '(', ''))
			ELSE NULL
		END AS fsp_phone
	FROM IL_application AS a
	LEFT JOIN IL_fund_dlr_ach AS d ON d.app_id = a.app_id;

UPDATE STATISTICS sandbox.app_dealer_rl;

-------------------------------------------------------------------------------------------------------------------------------------------------
-- contact_base ---------------------------------------------------------------------------------------------------------------------------------
SET IDENTITY_INSERT sandbox.contact_base ON;

	INSERT INTO sandbox.contact_base
		(con_id, app_id, birth_date, cell_phone, contact_type_enum, email, esign_consent_flag, first_name, fraud_type_enum, home_phone, last_name, 
		 middle_initial, mother_maiden_name, paperless_flag, sms_consent_flag, ssn, suffix)
		SELECT 
			c.con_id,
			a.app_id,
			-- Set NULL dates so we can preserve NOT NULL constraint (these exist in PRD for AUTHU from 2008 and past)
			CASE
				WHEN c.birth_date IS NULL THEN '1900-01-01'
				ELSE c.birth_date
			END AS birth_date,
			CASE
				WHEN LEN(c.cell_phone) > 0	THEN RTRIM(REPLACE(REPLACE(REPLACE(c.cell_phone, '-', ''), ')', ''), '(', ''))
				ELSE NULL
			END AS cell_phone,
			CASE
				WHEN RTRIM(c.ac_role_tp_c) = 'PR'	THEN 281
				WHEN RTRIM(c.ac_role_tp_c) = 'SEC'	THEN 282
			END AS contact_type_enum,
			CASE
				WHEN LEN(c.email) > 0 THEN RTRIM(c.email) 
				-- *** TEMP WORKAROUND, REMOVE ONCE [contact_base] HAS BEEN RECREATED TO ALLOW NULLS ***
				ELSE 'workaround.email.for.constraints.is.temporary.com'--NULL
			END AS email,
			0 AS esign_consent_flag,
			RTRIM(c.first_name) AS first_name,
			NULL AS fraud_ind,
			CASE
				WHEN LEN(c.home_phone) > 0	THEN RTRIM(REPLACE(REPLACE(REPLACE(c.home_phone, '-', ''), ')', ''), '(', ''))
				ELSE NULL
			END AS home_phone,
			RTRIM(c.last_name) AS last_name,
			CASE
				WHEN c.middle_initial <> '' THEN c.middle_initial
				ELSE NULL
			END AS middle_initial,
			NULL AS mother_maiden_name,
			0 AS paperless_flag,
			0 AS sms_consent_flag,
			-- Set NULL ssn's so we can preserve NOT NULL constraint (these exist in PROD for AUTHU from 2008 and past)
			CASE
				WHEN c.ssn IS NULL THEN '000000000'
				ELSE RTRIM(c.ssn)
			END AS ssn,
			CASE
				WHEN c.suffix <> '' THEN RTRIM(c.suffix) 
				ELSE NULL
			END AS suffix
		FROM IL_contact AS c
		INNER JOIN IL_application AS a ON a.app_id = c.app_id
		WHERE
			-- Have to filter out all the blank SEC rows somehow
			LEN(c.ssn) > 0;

SET IDENTITY_INSERT sandbox.contact_base OFF;

-- Reseed table to be next app_id
DECLARE	@max2	int	= (SELECT MAX(con_id) FROM sandbox.contact_base);
DBCC CHECKIDENT ('sandbox.contact_base', RESEED, @max2);

UPDATE STATISTICS sandbox.contact_base;

-------------------------------------------------------------------------------------------------------------------------------------------------

-- contact_address ------------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.contact_address
	(con_id, address_type_enum, city, months_at_address, ownership_type_enum, po_box, rural_route, [state], street_name, street_number, unit, zip)
	SELECT 
		ca.con_id,
	CASE
		WHEN RTRIM(ca.address_type_code) = 'CURR'	THEN 320
		WHEN RTRIM(ca.address_type_code) = 'PREV'	THEN 321
		WHEN RTRIM(ca.address_type_code) = 'PATR'	THEN 322
		WHEN RTRIM(ca.address_type_code) = 'COLL'	THEN 323
	END AS address_type_enum,
	ca.city,
	CASE
		WHEN ca.months_at_residence > 0 OR ca.years_at_residence > 0	THEN CAST(ca.months_at_residence + (ca.years_at_residence * 12) AS smallint) 
		ELSE NULL
	END AS months_at_address,
	CASE
		WHEN RTRIM(ca.ownership_type_code) = 'O'	THEN 330
		WHEN RTRIM(ca.ownership_type_code) = 'F'	THEN 331
		WHEN RTRIM(ca.ownership_type_code) = 'R'	THEN 332
		WHEN RTRIM(ca.ownership_type_code) = 'L'	THEN 333
		WHEN RTRIM(ca.ownership_type_code) = 'W'	THEN 334
		WHEN RTRIM(ca.ownership_type_code) = 'X'	THEN 335
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
		WHEN ca.apartment_unit_number <> '' THEN ca.apartment_unit_number
		ELSE NULL
	END AS unit,
	ca.zip_code AS zip
	FROM IL_contact AS c
	INNER JOIN IL_application AS a ON a.app_id = c.app_id
	INNER JOIN IL_contact_address AS ca ON ca.con_id = c.con_id
		WHERE
			ca.address_type_code <> '' AND
			-- Have to filter out all the blank SEC contact rows somehow
			LEN(c.ssn) > 0 AND
			-- Have to filter out all of the blank PREV contact_address rows;
			LEN(ca.zip_code) > 0;

UPDATE STATISTICS sandbox.contact_address;

-------------------------------------------------------------------------------------------------------------------------------------------------

-- contact_employment ----------------------------------------------------------------------------------------------------------------------------
INSERT INTO sandbox.contact_employment
	(con_id, address_line_1, city, business_name, employment_type_enum, income_type_enum, job_title, monthly_salary, months_at_job, 
	 other_monthly_income, other_income_type_enum, other_income_source_detail, phone, self_employed_flag, [state], street_name, street_number, unit, zip)
	SELECT 
		e.con_id,
		CASE
			WHEN e.address_line1 <> ''	THEN RTRIM(e.address_line1)
		END AS address_line_1,
		e.city,
		e.business_name,
		CASE
			WHEN RTRIM(e.employment_type_code) = 'CURR'	THEN 350
			WHEN RTRIM(e.employment_type_code) = 'PREV'	THEN 351
		END AS employment_type_enum,
		--NULL AS income_source_nontaxable_flag,
		-- WEIRD, RL doesn't have a primary income type
		NULL AS income_type_enum,
		CASE
			WHEN e.title_position <> '' THEN e.title_position
			ELSE NULL
		END AS job_title,
		CASE
			WHEN RTRIM(e.salary_basis_type_code) = 'ANNUM' THEN e.salary / 12
			WHEN RTRIM(e.salary_basis_type_code) = 'MONTH' THEN e.salary
			ELSE e.salary
		END AS monthly_salary,
		CASE
			WHEN e.months_at_job > 0 OR e.years_at_job > 0	THEN CAST(e.months_at_job + (e.years_at_job * 12) AS smallint) 
			ELSE NULL
		END AS months_at_job,
		CASE
			-- NOTE: other_income_basis_type_code values are jacked up and can't be used to calculate the other_income_amt, assume it's all monthly
			--WHEN RTRIM(e.other_income_basis_type_code) = 'ANNUM'		THEN e.other_income_amt / 12
			--WHEN RTRIM(e.other_income_basis_type_code) LIKE 'MONTH%'	THEN e.other_income_amt
			WHEN e.other_income_amt > 0	THEN e.other_income_amt
			ELSE NULL
		END AS other_monthly_income,
		CASE
			WHEN RTRIM(e.other_income_source_type_code) = 'ALLOW'					THEN 380
			WHEN RTRIM(e.other_income_source_type_code) = 'ALMONY'					THEN 381
			WHEN RTRIM(e.other_income_source_type_code) = 'BONUS'					THEN 382
			WHEN RTRIM(e.other_income_source_type_code) = 'CHDSUP'					THEN 383
			WHEN RTRIM(e.other_income_source_type_code) = 'CTPYMT'					THEN 384
			WHEN RTRIM(e.other_income_source_type_code) = 'DISINC'					THEN 385
			WHEN RTRIM(e.other_income_source_type_code) = 'EMPLOY'					THEN 386
			WHEN RTRIM(e.other_income_source_type_code) = 'INVEST'					THEN 387
			WHEN RTRIM(e.other_income_source_type_code) = 'MILTRY'					THEN 388
			WHEN RTRIM(e.other_income_source_type_code) = 'OTHER'					THEN 389
			WHEN RTRIM(e.other_income_source_type_code) = 'PNSION'					THEN 390
			WHEN RTRIM(e.other_income_source_type_code) = 'PUBAST'					THEN 391
			WHEN RTRIM(e.other_income_source_type_code) = 'RENTAL'					THEN 392
			WHEN RTRIM(e.other_income_source_type_code) = '2NDJOB'					THEN 393
			WHEN RTRIM(e.other_income_source_type_code) = 'SOCSEC'					THEN 394
			WHEN RTRIM(e.other_income_source_type_code) = 'SPOUSE'					THEN 395
			WHEN RTRIM(e.other_income_source_type_code) = 'TRUST'					THEN 396
			WHEN RTRIM(e.other_income_source_type_code) IN ('UEMBEN', 'UNEMPL')		THEN 397
			WHEN RTRIM(e.other_income_source_type_code) ='UNKN'						THEN 398
			WHEN RTRIM(e.other_income_source_type_code) = 'VA'						THEN 399
			ELSE NULL
		END AS other_income_type_enum,
		NULL AS other_income_source_detail,
		CASE
			WHEN business_phone <> ''	THEN RTRIM(REPLACE(REPLACE(REPLACE(business_phone, '-', ''), ')', ''), '(', '')) 
		END AS phone,
		CASE
			WHEN e.self_employed_ind = 'Y' THEN 1
			ELSE 0
		END AS self_employed_flag,
		[state],
		NULL AS street_name,
		NULL AS street_number,
		NULL AS unit,
		RTRIM(zip_code) AS zip
	FROM IL_contact AS c
	INNER JOIN IL_application AS a ON a.app_id = c.app_id
	INNER JOIN IL_contact_employment AS e ON e.con_id = c.con_id
		WHERE
			e.employment_type_code <> '' AND
			-- Have to filter out all the blank SEC contact rows somehow
			LEN(c.ssn) > 0 AND
			-- Have to filter out all of the blank PREV contact_address rows;
			LEN(e.zip_code) > 0;

UPDATE STATISTICS sandbox.contact_employment;

-------------------------------------------------------------------------------------------------------------------------------------------------