/* --------------------------------------------------------------------------------------------------------------------
-- File: insert_enum_values.sql
-- Purpose: Insert enum values for credit application XML extraction
-- Source: Extracted from migrate_table_logic.sql lines 5-298
-- 
-- NOTE: This file may not be needed in production since enum data is already set up.
--       This is provided for reference and testing environments only.
-------------------------------------------------------------------------------------------------------------------- */

DELETE FROM  sandbox.app_enums;

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (1, 'app_source_cc', 'INTERNET');	-- I
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (2, 'app_source_cc', 'MAILED-IN');	-- M
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (3, 'app_source_cc', 'T');			-- T
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (4, 'app_source_cc', 'U');			-- U

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (10, 'app_source_rl', 'APPONE');		-- A
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (11, 'app_source_rl', 'DEALERTRACK');	-- D
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (12, 'app_source_rl', 'FAXED-IN');		-- F
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (13, 'app_source_rl', 'S');				-- S
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (14, 'app_source_rl', 'DEALER DIRECT');	-- (new)
 
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (20, 'app_type_cc', 'ALL');		-- ALL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (21, 'app_type_cc', 'CBC');		-- CBC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (22, 'app_type_cc', 'FPP');		-- FPP
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (23, 'app_type_cc', 'GEICO');	-- GEICO
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (24, 'app_type_cc', 'GPA');		-- GPA
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (25, 'app_type_cc', 'GREST');	-- GREST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (26, 'app_type_cc', 'HCOSC');	-- HCOSC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (27, 'app_type_cc', 'HT1');		-- HT1
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (28, 'app_type_cc', 'PCP');		-- PCP
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (29, 'app_type_cc', 'PCT');		-- PCT
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (30, 'app_type_cc', 'PRODB');	-- PRODB
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (31, 'app_type_cc', 'REST');	-- REST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (32, 'app_type_cc', 'SECURE');	-- SECURE

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (38, 'app_type_rl', 'HT');		-- HT
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (39, 'app_type_rl', 'MARINE');	-- MARINE
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (40, 'app_type_rl', 'MC');		-- MC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (41, 'app_type_rl', 'OR');		-- OR
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (42, 'app_type_rl', 'RV');		-- RV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (43, 'app_type_rl', 'UT');		-- UT

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (45, 'sub_type_rl', 'ATV');			-- ATV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (46, 'sub_type_rl', 'PWC');			-- PWC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (47, 'sub_type_rl', 'SNOWMOBILE');	-- SNOWMOBILE
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (48, 'sub_type_rl', 'UTV');			-- UTV

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (50, 'decision_type_cc', 'APPROVED');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (51, 'decision_type_cc', 'DECLINED');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (52, 'decision_type_cc', 'DECLINED-NC');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (53, 'decision_type_cc', 'FAILED-BIT');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (54, 'decision_type_cc', 'FAILED-GIACT');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (55, 'decision_type_cc', 'NOCHK');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (56, 'decision_type_cc', 'NO DECISION');		-- NONE
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (57, 'decision_type_cc', 'PENDING-DEPOSIT');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (58, 'decision_type_cc', 'PENDING-FINICITY');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (59, 'decision_type_cc', 'PENDING-NOVA');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (60, 'decision_type_cc', 'WITHDRAWN');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (65, 'decision_type_rl', 'APPROVED');		-- APPRV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (66, 'decision_type_rl', 'DECLINED');		-- DECLN
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (67, 'decision_type_rl', 'WITHDRAWN');		-- WITHD
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (68, 'decision_type_rl', 'NO DECISION');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (70, 'bank_account_type', 'CHECKING');		-- C
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (71, 'bank_account_type', 'SAVINGS');		-- S

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (80, 'priority_cc', 'Alloy Error');			-- Alloy Error
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (81, 'priority_cc', 'Offline Step-Up');		-- Offline Step-Up
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (82, 'priority_cc', 'Step-Up Received');	-- Step-Up Received

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (100, 'process_cc', '00050');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (101, 'process_cc', '00100');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (102, 'process_cc', '01000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (103, 'process_cc', '02000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (104, 'process_cc', '03000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (105, 'process_cc', '03010');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (106, 'process_cc', '06000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (107, 'process_cc', '07000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (108, 'process_cc', '07500');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (109, 'process_cc', '08000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (110, 'process_cc', '09000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (111, 'process_cc', '11000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (112, 'process_cc', '13000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (113, 'process_cc', '20000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (114, 'process_cc', '30000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (115, 'process_cc', '40000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (116, 'process_cc', '99000');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (117, 'process_cc', '99500');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (130, 'funding_source_sc', 'ACH');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (131, 'funding_source_sc', 'Check');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (132, 'funding_source_sc', 'Debit');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (133, 'funding_source_sc', 'Mail CC/MO');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (134, 'funding_source_sc', 'Money Gram ');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (135, 'funding_source_sc', 'Money Order');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (136, 'funding_source_sc', 'Online Bill Pay');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (137, 'funding_source_sc', 'Undetermined');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (138, 'funding_source_sc', 'Western Union');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (139, 'funding_source_sc', 'Wire Transfer');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (150, 'ssn_match_cc', 'CLOSE');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (151, 'ssn_match_cc', 'NO');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (152, 'ssn_match_cc', 'YES');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (160, 'status_cc', 'A');	-- A
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (161, 'status_cc', 'B');	-- B
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (162, 'status_cc', 'C');	-- C
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (163, 'status_cc', 'D');	-- D
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (164, 'status_cc', 'F');	-- F
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (165, 'status_cc', 'P');	-- P
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (166, 'status_cc', 'Q');	-- Q
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (167, 'status_cc', 'W');	-- W

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (180, 'verification_source_cc', 'CAL');					-- CAL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (181, 'verification_source_cc', 'CF');					-- CF
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (182, 'verification_source_cc', 'CM');					-- CM
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (183, 'verification_source_cc', 'CTC');					-- CTC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (184, 'verification_source_cc', 'EXPERIAN');			-- EX
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (185, 'verification_source_cc', 'FDR');					-- FDR
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (186, 'verification_source_cc', 'FDW');					-- FDW
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (187, 'verification_source_cc', 'EX PRECISE ID KIQ');	-- EX
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (188, 'verification_source_cc', 'LEXISNEXIS');			-- LNA
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (189, 'verification_source_cc', 'LNI');					-- LNI
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (190, 'verification_source_cc', 'LNQ');					-- LNQ
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (191, 'verification_source_cc', 'MAC');					-- MAC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (192, 'verification_source_cc', 'ORG');					-- ORG
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (193, 'verification_source_cc', 'PCR');					-- PCR
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (194, 'verification_source_cc', 'PID');					-- PID
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (195, 'verification_source_cc', 'PWS');					-- PWS
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (196, 'verification_source_cc', 'SOL');					-- SOL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (197, 'verification_source_cc', 'TU-TLO');				-- TLO
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (198, 'verification_source_cc', 'TRANSUNION');			-- TU

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (210, 'decision_model_cc', 'CLASSIC 08');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (211, 'decision_model_cc', 'EX FICO 08');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (212, 'decision_model_cc', 'EX FICO 10T');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (213, 'decision_model_cc', 'EX VANTAGE4');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (214, 'decision_model_cc', 'TU FICO 09');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (215, 'decision_model_cc', 'TU FICO 10T');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (216, 'decision_model_cc', 'TU VANTAGE');

-- Hopefully 'MISSING' value is not needed, temporarily using this as a fallback for missing data
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (229, 'population_assignment_cc', 'MISSING');		-- ''
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (230, 'population_assignment_cc', '02');			-- 02
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (231, 'population_assignment_cc', '1');				-- 1
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (232, 'population_assignment_cc', '2');				-- 2			
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (233, 'population_assignment_cc', '3');				-- 3
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (234, 'population_assignment_cc', 'BL');			-- BL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (235, 'population_assignment_cc', 'EX FICO 08');	-- CM
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (236, 'population_assignment_cc', 'CONTROL');		-- CONTROL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (237, 'population_assignment_cc', 'TU FICO 09');	-- DN
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (238, 'population_assignment_cc', 'EX EVS');		-- EV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (239, 'population_assignment_cc', 'TU FICO 09');	-- HD
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (240, 'population_assignment_cc', 'EX FICO 08');	-- HE
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (241, 'population_assignment_cc', 'HOLDOUT');		-- HOLDOUT
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (242, 'population_assignment_cc', 'TU FICO 10T');	-- HU
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (243, 'population_assignment_cc', 'TU VANTAGE');	-- HV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (244, 'population_assignment_cc', 'EX VANTAGE');	-- HW
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (245, 'population_assignment_cc', 'PRECISION');		-- JB
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (246, 'population_assignment_cc', 'JH');			-- JH
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (247, 'population_assignment_cc', 'TU L2C');		-- L2
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (248, 'population_assignment_cc', 'TU VANTAGE');	-- LB
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (249, 'population_assignment_cc', 'LP');			-- LP
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (250, 'population_assignment_cc', 'TU FICO 10T');	-- SB
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (251, 'population_assignment_cc', 'TU FICO 10T');	-- SO
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (252, 'population_assignment_cc', 'T');				-- T
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (253, 'population_assignment_cc', 'VIP');			-- VIP

-- contact.ac_role_tp_c
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (280, 'contact_type', 'AUTHORIZED USER');			-- AUTHU
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (281, 'contact_type', 'PRIMARY');					-- PR
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (282, 'contact_type', 'SECONDARY');					-- SEC

-- contact.fraud_ind
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (290, 'fraud_type_cc', 'SUSPECTED');				-- S
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (291, 'fraud_type_cc', 'VERIFIED');					-- V

-- contact_address.address_tp_c
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (320, 'address_type', 'CURRENT');					-- CURR
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (321, 'address_type', 'PREVIOUS');					-- PREV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (322, 'address_type', 'PATRIOT');					-- PATR (RL)
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (323, 'address_type', 'COLLATERAL');				-- COLL (RL)

-- contact_address.ownership_tp_c
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (330, 'ownership_type', 'OWN WITH MORTGAGE');		-- O
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (331, 'ownership_type', 'OWN NO	MORTGAGE');			-- F (RL)
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (332, 'ownership_type', 'RENT');					-- R
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (333, 'ownership_type', 'WITH RELATIVES');			-- L (RL)
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (334, 'ownership_type', 'OTHER');
-- What are these exactly?
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (324, 'ownership_type', 'W');						-- W (RL)
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (335, 'ownership_type', 'X');						-- X

-- contact_employment.employment_tp_c
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (350, 'employment_type', 'CURRENT');				-- CURR
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (351, 'employment_type', 'PREVIOUS');				-- PREV

-- contact_employment.b_primary_income_source_tp_c
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (360, 'income_type', 'ALLOWANCE');					-- ALLOW
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (361, 'income_type', 'EMPLOYMENT');					-- EMPLOY
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (362, 'income_type', 'GOVAST');						-- GOVAST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (363, 'income_type', 'INVESTMENT');					-- INVEST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (364, 'income_type', 'OTHER');						-- OTHER
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (365, 'income_type', 'RENTAL PROPERTY');			-- RENTAL

-- contact_employment.b_other_income_source_tp_c
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (380, 'other_income_type', 'ALLOWANCE');			-- ALLOW
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (381, 'other_income_type', 'ALIMONY');				-- ALMONY
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (382, 'other_income_type', 'BONUS');				-- BONUS
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (383, 'other_income_type', 'CHILD SUPPORT');		-- CHDSUP
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (384, 'other_income_type', 'COURT PAYMENT');		-- CTPYMT
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (385, 'other_income_type', 'DISABILIY');			-- DISINC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (386, 'other_income_type', 'EMPLOYMENT');			-- EMPLOY
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (387, 'other_income_type', 'INVESTMENT');			-- INVEST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (388, 'other_income_type', 'INSURANCE');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (389, 'other_income_type', 'MILITARY');				-- MILTRY
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (390, 'other_income_type', 'OTHER');				-- OTHER
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (391, 'other_income_type', 'PENSION');				-- PNSION
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (392, 'other_income_type', 'PUBLIC ASSISTANCE');	-- PUBAST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (393, 'other_income_type', 'RENTAL PROPERTY');		-- RENTAL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (394, 'other_income_type', 'SECOND JOB');			-- 2NDJOB
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (395, 'other_income_type', 'SOCIAL SECURITY');		-- SOCSEC
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (396, 'other_income_type', 'SPOUSE');				-- SPOUSE
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (397, 'other_income_type', 'TRUST FUND');			-- TRUST
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (398, 'other_income_type', 'UNEMPLOYMENT');			-- UEMBEN, UNEMPL
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (399, 'other_income_type', 'UNKNOWN');				-- UNKN
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (400, 'other_income_type', 'VETERANS AFFAIRS');		-- VA  

--
-- Does this make sense being similar to app_sub_types?
--
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (410, 'collateral_type_rl', 'ALL TERRAIN VEHICLE');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (411, 'collateral_type_rl', 'BOAT');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (412, 'collateral_type_rl', 'ENGINE-1');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (413, 'collateral_type_rl', 'ENGINE-2');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (414, 'collateral_type_rl', 'ENGINE-3');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (415, 'collateral_type_rl', 'HORSE TRAILER');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (416, 'collateral_type_rl', 'MOTORCYCLE');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (417, 'collateral_type_rl', 'PERSONAL WATERCRAFT');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (418, 'collateral_type_rl', 'RV');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (419, 'collateral_type_rl', 'SNOWMOBILE');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (420, 'collateral_type_rl', 'TRAILER');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (421, 'collateral_type_rl', 'UTILITY TRAILER');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (422, 'collateral_type_rl', 'UTILITY TASK VEHICLE');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (423, 'collateral_type_rl', 'UNDETERMINED');				-- Could not resolve

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (600, 'product_line', 'CC');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (601, 'product_line', 'RCLI');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (602, 'product_line', 'RL');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (610, 'decision_rl', 'APPROVED');							-- APPRV
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (611, 'decision_rl', 'DECLINED');							-- DECLN
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (612, 'decision_rl', 'WITHDRAWN');							-- WITHD

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (620, 'warranty_type_rl', 'Credit Disability');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (621, 'warranty_type_rl', 'Credit Life');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (622, 'warranty_type_rl', 'Extended Warranty');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (623, 'warranty_type_rl', 'Gap Insurance');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (624, 'warranty_type_rl', 'Other');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (625, 'warranty_type_rl', 'Road Side Assistance');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (626, 'warranty_type_rl', 'Service Contract');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (630, 'policy_exception_type_rl', 'Capacity Exception');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (631, 'policy_exception_type_rl', 'Collateral Program Exception');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (632, 'policy_exception_type_rl', 'Credit Exception');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (640, 'mrv_model_type_rl', 'MRV');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (641, 'mrv_model_type_rl', 'Vantage');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (650, 'bank_account_type_rl', 'CHECKING');					-- 22
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (651, 'bank_account_type_rl', 'SAVINGS');					-- 32

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (655, 'fund_loan_indicator_rl', 'YES');						-- Y
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (656, 'fund_loan_indicator_rl', 'NO');						-- N
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (657, 'fund_loan_indicator_rl', 'PENDING');					-- P

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (660, 'funding_validation_indicator_rl', 'YES');			-- Y
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (661, 'funding_validation_indicator_rl', 'NO');				-- N
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (662, 'funding_validation_indicator_rl', 'DOES NOT APPLY');	-- D

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (670, 'process_rl', '03800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (671, 'process_rl', '05800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (672, 'process_rl', '06800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (673, 'process_rl', '06850');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (674, 'process_rl', '08800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (675, 'process_rl', '20800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (676, 'process_rl', '30800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (677, 'process_rl', '40800');
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (678, 'process_rl', '99800');

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (690, 'status_rl', 'F');	--	F
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (691, 'status_rl', 'P');	--	P

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (700, 'supervisor_review_indicator_rl', 'COMPLETED');	--	C
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (701, 'supervisor_review_indicator_rl', 'IN-REVIEW');	--	R

INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (706, 'audit_flag_rl', 'REVIEWED');	--	R
INSERT INTO  sandbox.app_enums (enum_id, type, value) VALUES (707, 'audit_flag_rl', 'PENDING');	--	P

UPDATE STATISTICS  sandbox.app_enums;