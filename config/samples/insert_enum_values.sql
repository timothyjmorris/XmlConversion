DELETE FROM dbo.app_enums;


INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (600, 'product_line', 'CC');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (601, 'product_line', 'RCLI');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (602, 'product_line', 'RL');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (1, 'app_source_cc', 'INTERNET');	-- I
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (2, 'app_source_cc', 'MAILED-IN');	-- M
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (3, 'app_source_cc', 'TELEPHONE');	-- T
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (4, 'app_source_cc', 'U');			-- U
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (5, 'app_source_cc', 'CK-API');		-- C
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (6, 'app_source_cc', 'EX-API');		-- E

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (10, 'app_source_rl', 'APPONE');		-- A
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (11, 'app_source_rl', 'DEALERTRACK');	-- D
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (12, 'app_source_rl', 'FAXED-IN');		-- F
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (13, 'app_source_rl', 'S');				-- S
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (14, 'app_source_rl', 'DEALER DIRECT');	-- P
 
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (20, 'app_type_cc', 'ALL');		-- ALL
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (21, 'app_type_cc', 'CBC');		-- CBC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (22, 'app_type_cc', 'FPP');		-- FPP
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (23, 'app_type_cc', 'GEICO');	-- GEICO
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (24, 'app_type_cc', 'GPA');		-- GPA
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (25, 'app_type_cc', 'GREST');	-- GREST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (26, 'app_type_cc', 'HCOSC');	-- HCOSC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (27, 'app_type_cc', 'HT1');		-- HT1
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (28, 'app_type_cc', 'PCP');		-- PCP
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (29, 'app_type_cc', 'PCT');		-- PCT
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (30, 'app_type_cc', 'PRODB');	-- PRODB
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (31, 'app_type_cc', 'REST');	-- REST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (32, 'app_type_cc', 'SECURE');	-- SECURE
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (33, 'app_type_cc', 'DIGITAL');	-- 

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (38, 'app_type_rl', 'HT');		-- HT
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (39, 'app_type_rl', 'MARINE');	-- MARINE
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (40, 'app_type_rl', 'MC');		-- MC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (41, 'app_type_rl', 'OR');		-- OR
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (42, 'app_type_rl', 'RV');		-- RV
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (43, 'app_type_rl', 'UT');		-- UT

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (45, 'sub_type_rl', 'ATV');			-- ATV
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (46, 'sub_type_rl', 'PWC');			-- PWC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (47, 'sub_type_rl', 'SNOWMOBILE');	-- SNOWMOBILE
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (48, 'sub_type_rl', 'UTV');			-- UTV

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (50, 'decision_type_cc', 'APPROVED');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (51, 'decision_type_cc', 'DECLINED');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (52, 'decision_type_cc', 'DECLINED-NC');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (53, 'decision_type_cc', 'FAILED-DEBIT');		-- FDBIT
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (54, 'decision_type_cc', 'FAILED-GIACT');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (55, 'decision_type_cc', 'NOCHK');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (56, 'decision_type_cc', 'NO DECISION');		-- NONE
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (57, 'decision_type_cc', 'PENDING-DEPOSIT');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (58, 'decision_type_cc', 'APPROVED-PENDING-DEPOSIT'); 
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (59, 'decision_type_cc', 'PENDING NOVA'); 
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (60, 'decision_type_cc', 'WITHDRAWN');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (65, 'decision_type_rl', 'APPROVED');		-- APPRV
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (66, 'decision_type_rl', 'DECLINED');		-- DECLN
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (67, 'decision_type_rl', 'WITHDRAWN');		-- WITHD
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (68, 'decision_type_rl', 'NO DECISION');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (70, 'bank_account_type', 'CHECKING');		-- C
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (71, 'bank_account_type', 'SAVINGS');		-- S

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (80, 'priority_cc', 'Alloy Error');			-- Alloy Error
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (81, 'priority_cc', 'Offline Step-Up');		-- Offline Step-Up
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (82, 'priority_cc', 'Step-Up Received');	-- Step-Up Received
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (83, 'priority_cc', 'TU Doc R');			-- TU Document Verification - Received
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (84, 'priority_cc', 'TU Doc P');			-- TU Document Verification - Pending

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (90, 'process_cc', '00025');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (92, 'process_cc', '00050');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (94, 'process_cc', '00095');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (95, 'process_cc', '00098');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (96, 'process_cc', '00100');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (98, 'process_cc', '00500');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (100, 'process_cc', '01000');	
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (102, 'process_cc', '02000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (104, 'process_cc', '03000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (106, 'process_cc', '03010');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (107, 'process_cc', '03100');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (108, 'process_cc', '06000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (110, 'process_cc', '07000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (112, 'process_cc', '07500');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (114, 'process_cc', '08000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (116, 'process_cc', '09000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (118, 'process_cc', '10900');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (120, 'process_cc', '11000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (121, 'process_cc', '12000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (122, 'process_cc', '13000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (123, 'process_cc', '15000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (124, 'process_cc', '20000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (126, 'process_cc', '30000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (128, 'process_cc', '40000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (129, 'process_cc', '99000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (130, 'process_cc', '99500');

-- REMAP THESE AWAY ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/*
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (100, 'process_cc', '00050');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (101, 'process_cc', '00100');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (102, 'process_cc', '01000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (103, 'process_cc', '02000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (104, 'process_cc', '03000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (105, 'process_cc', '03010');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (106, 'process_cc', '06000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (107, 'process_cc', '07000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (108, 'process_cc', '07500');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (109, 'process_cc', '08000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (110, 'process_cc', '09000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (111, 'process_cc', '11000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (112, 'process_cc', '13000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (113, 'process_cc', '20000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (114, 'process_cc', '30000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (115, 'process_cc', '40000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (116, 'process_cc', '99000');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (117, 'process_cc', '99500');
*/

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (140, 'funding_source_sc', 'ACH');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (131, 'funding_source_sc', 'Check');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (132, 'funding_source_sc', 'Debit');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (133, 'funding_source_sc', 'Mail CC/MO');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (134, 'funding_source_sc', 'Money Gram ');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (135, 'funding_source_sc', 'Money Order');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (136, 'funding_source_sc', 'Online Bill Pay');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (137, 'funding_source_sc', 'Undetermined');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (138, 'funding_source_sc', 'Western Union');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (139, 'funding_source_sc', 'Wire Transfer');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (150, 'ssn_match_cc', 'CLOSE');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (151, 'ssn_match_cc', 'NO');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (152, 'ssn_match_cc', 'YES');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (160, 'status_cc', 'A');	-- A
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (161, 'status_cc', 'B');	-- B
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (162, 'status_cc', 'C');	-- C
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (163, 'status_cc', 'D');	-- D
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (164, 'status_cc', 'F');	-- F
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (165, 'status_cc', 'P');	-- P
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (166, 'status_cc', 'Q');	-- Q
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (167, 'status_cc', 'W');	-- W

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (180, 'verification_source_cc', 'CAL');					-- CAL
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (181, 'verification_source_cc', 'CF');					-- CF
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (182, 'verification_source_cc', 'CM');					-- CM
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (183, 'verification_source_cc', 'CTC');					-- CTC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (184, 'verification_source_cc', 'EXPERIAN');			-- EX
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (185, 'verification_source_cc', 'FDR');					-- FDR
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (186, 'verification_source_cc', 'FDW');					-- FDW
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (187, 'verification_source_cc', 'EX PRECISE ID KIQ');	-- EX
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (188, 'verification_source_cc', 'LEXISNEXIS');			-- LNA
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (189, 'verification_source_cc', 'LNI');					-- LNI
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (190, 'verification_source_cc', 'LNQ');					-- LNQ
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (191, 'verification_source_cc', 'MAC');					-- MAC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (192, 'verification_source_cc', 'ORG');					-- ORG
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (193, 'verification_source_cc', 'PCR');					-- PCR
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (194, 'verification_source_cc', 'PID');					-- PID
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (195, 'verification_source_cc', 'PWS');					-- PWS
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (196, 'verification_source_cc', 'SOL');					-- SOL
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (197, 'verification_source_cc', 'TU-TLO');				-- TLO
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (198, 'verification_source_cc', 'TRANSUNION');			-- TU

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (210, 'decision_model_cc', 'CLASSIC 08');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (211, 'decision_model_cc', 'EX FICO 08');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (212, 'decision_model_cc', 'EX FICO 10T');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (213, 'decision_model_cc', 'EX VANTAGE4');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (214, 'decision_model_cc', 'TU FICO 09');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (215, 'decision_model_cc', 'TU FICO 10T');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (216, 'decision_model_cc', 'TU VANTAGE');

-- Hopefully 'MISSING' value is not needed, temporarily using this as a fallback for missing data
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (229, 'population_assignment_cc', 'MISSING', 'MISSING');		-- ''
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (230, 'population_assignment_cc', '02', '02');					-- 02
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (231, 'population_assignment_cc', '1', '1');					-- 1
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (232, 'population_assignment_cc', '2', '2');					-- 2			
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (233, 'population_assignment_cc', '3', '3');					-- 3
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (234, 'population_assignment_cc', 'BL', 'BL');					-- BL
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (235, 'population_assignment_cc', 'CM', 'EX FICO 08');			-- CM
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (236, 'population_assignment_cc', 'CONTROL', 'CONTROL');		-- CONTROL
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (237, 'population_assignment_cc', 'DN', 'TU FICO 09');			-- DN
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (238, 'population_assignment_cc', 'EV', 'EX EVS');				-- EV
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (239, 'population_assignment_cc', 'HD', 'TU FICO 09');			-- HD
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (240, 'population_assignment_cc', 'HE', 'EX FICO 08');			-- HE
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (241, 'population_assignment_cc', 'HOLDOUT', 'HOLDOUT');		-- HOLDOUT
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (242, 'population_assignment_cc', 'HU', 'TU FICO 10T');		-- HU
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (243, 'population_assignment_cc', 'HV', 'TU VANTAGE');			-- HV
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (244, 'population_assignment_cc', 'HW', 'EX VANTAGE');			-- HW
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (245, 'population_assignment_cc', 'JB', 'PRECISION');			-- JB
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (246, 'population_assignment_cc', 'JH', 'JH');					-- JH
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (247, 'population_assignment_cc', 'L2', 'TU L2C');				-- L2
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (248, 'population_assignment_cc', 'LB', 'TU VANTAGE');			-- LB
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (249, 'population_assignment_cc', 'LP', 'LP');					-- LP
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (250, 'population_assignment_cc', 'SB', 'TU FICO 10T');		-- SB
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (251, 'population_assignment_cc', 'SO', 'TU FICO 10T');		-- SO
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (252, 'population_assignment_cc', 'T', 'T');					-- T
INSERT INTO dbo.app_enums (enum_id, type, value, description) VALUES (253, 'population_assignment_cc', 'VIP', 'VIP');				-- VIP


-- contact.ac_role_tp_c
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (280, 'contact_type', 'AUTHORIZED USER');			-- AUTHU
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (281, 'contact_type', 'PRIMARY');					-- PR
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (282, 'contact_type', 'SECONDARY');					-- SEC

-- contact.fraud_ind
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (290, 'fraud_type_cc', 'SUSPECTED');				-- S
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (291, 'fraud_type_cc', 'VERIFIED');					-- V

-- contact_address.address_tp_c
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (320, 'address_type', 'CURRENT');					-- CURR
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (321, 'address_type', 'PREVIOUS');					-- PREV
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (322, 'address_type', 'PATRIOT');					-- PATR (RL)
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (323, 'address_type', 'COLLATERAL');				-- COLL (RL)

-- contact_address.ownership_tp_c
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (330, 'ownership_type', 'OWN WITH MORTGAGE');		-- O
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (331, 'ownership_type', 'OWN NO	MORTGAGE');			-- F (RL)
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (332, 'ownership_type', 'RENT');					-- R
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (333, 'ownership_type', 'WITH RELATIVES');			-- L (RL)
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (334, 'ownership_type', 'OTHER');					-- T (RL - new)
-- What are these exactly?
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (324, 'ownership_type', 'W');						-- W (RL)
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (335, 'ownership_type', 'X');						-- X

-- contact_employment.employment_tp_c
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (350, 'employment_type', 'CURRENT');				-- CURR
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (351, 'employment_type', 'PREVIOUS');				-- PREV

-- contact_employment.b_primary_income_source_tp_c
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (360, 'income_type', 'ALLOWANCE');					-- ALLOW
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (361, 'income_type', 'EMPLOYMENT');					-- EMPLOY
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (362, 'income_type', 'GOVAST');						-- GOVAST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (363, 'income_type', 'INVESTMENT');					-- INVEST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (364, 'income_type', 'OTHER');						-- OTHER
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (365, 'income_type', 'RENTAL PROPERTY');			-- RENTAL

-- contact_employment.b_other_income_source_tp_c
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (380, 'other_income_type', 'ALLOWANCE');			-- ALLOW
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (381, 'other_income_type', 'ALIMONY');				-- ALMONY
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (382, 'other_income_type', 'BONUS');				-- BONUS
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (383, 'other_income_type', 'CHILD SUPPORT');		-- CHDSUP
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (384, 'other_income_type', 'COURT PAYMENT');		-- CTPYMT
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (385, 'other_income_type', 'DISABILIY');			-- DISINC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (386, 'other_income_type', 'EMPLOYMENT');			-- EMPLOY
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (387, 'other_income_type', 'INVESTMENT');			-- INVEST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (388, 'other_income_type', 'INSURANCE');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (389, 'other_income_type', 'MILITARY');				-- MILTRY
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (390, 'other_income_type', 'OTHER');				-- OTHER
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (391, 'other_income_type', 'PENSION');				-- PNSION
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (392, 'other_income_type', 'PUBLIC ASSISTANCE');	-- PUBAST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (393, 'other_income_type', 'RENTAL PROPERTY');		-- RENTAL
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (394, 'other_income_type', 'SECOND JOB');			-- 2NDJOB
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (395, 'other_income_type', 'SOCIAL SECURITY');		-- SOCSEC
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (396, 'other_income_type', 'SPOUSE');				-- SPOUSE
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (397, 'other_income_type', 'TRUST FUND');			-- TRUST
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (398, 'other_income_type', 'UNEMPLOYMENT');			-- UEMBEN, UNEMPL
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (399, 'other_income_type', 'UNKNOWN');				-- UNKN
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (400, 'other_income_type', 'VETERANS AFFAIRS');		-- VA  


INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (410, 'collateral_type_rl', 'ALL TERRAIN VEHICLE');	-- all_terrain_vehicle
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (411, 'collateral_type_rl', 'TRAILER BIN');			-- bin
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (412, 'collateral_type_rl', 'BOAT');				-- boat
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (413, 'collateral_type_rl', 'ENGINE');				-- engine
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (414, 'collateral_type_rl', 'ENGINE REPOWER');		-- engine_repower
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (415, 'collateral_type_rl', 'HORSE TRAILER');		-- horse_trailer
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (416, 'collateral_type_rl', 'MOTORCYCLE');			-- motorcycle
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (417, 'collateral_type_rl', 'OTHER TRAILER');		-- other_trailer
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (418, 'collateral_type_rl', 'PERSONAL WATERCRAFT');	-- personal_watercraft
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (419, 'collateral_type_rl', 'RV');					-- rv
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (420, 'collateral_type_rl', 'SNOWMOBILE');			-- snowmobile
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (421, 'collateral_type_rl', 'UTILITY TRAILER');		-- utility_trailer
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (422, 'collateral_type_rl', 'UTILITY VEHICLE');		-- utility_vehicle
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (423, 'collateral_type_rl', 'UNDETERMINED');		-- Could not resolve

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (610, 'decision_rl', 'APPROVED');							-- APPRV
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (611, 'decision_rl', 'DECLINED');							-- DECLN
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (612, 'decision_rl', 'PENDING');							-- 
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (613, 'decision_rl', 'WITHDRAWN');							-- WITHD

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (620, 'warranty_type_rl', 'Credit Disability');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (621, 'warranty_type_rl', 'Credit Life');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (622, 'warranty_type_rl', 'Extended Warranty');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (623, 'warranty_type_rl', 'Gap Insurance');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (624, 'warranty_type_rl', 'Other');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (625, 'warranty_type_rl', 'Road Side Assistance');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (626, 'warranty_type_rl', 'Service Contract');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (630, 'policy_exception_type_rl', 'Capacity Exception');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (631, 'policy_exception_type_rl', 'Collateral Program Exception');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (632, 'policy_exception_type_rl', 'Credit Exception');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (640, 'mrv_model_type_rl', 'MRV');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (641, 'mrv_model_type_rl', 'Vantage');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (650, 'bank_account_type_rl', 'CHECKING');					-- 22
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (651, 'bank_account_type_rl', 'SAVINGS');					-- 32

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (655, 'fund_loan_indicator_rl', 'YES');						-- Y
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (656, 'fund_loan_indicator_rl', 'NO');						-- N
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (657, 'fund_loan_indicator_rl', 'PENDING');					-- P

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (660, 'funding_validation_indicator_rl', 'YES');			-- Y
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (661, 'funding_validation_indicator_rl', 'NO');				-- N
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (662, 'funding_validation_indicator_rl', 'DOES NOT APPLY');	-- D

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (670, 'process_rl', '03800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (671, 'process_rl', '05800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (672, 'process_rl', '06800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (673, 'process_rl', '06850');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (674, 'process_rl', '08800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (675, 'process_rl', '20800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (676, 'process_rl', '30800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (677, 'process_rl', '40800');
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (678, 'process_rl', '99800');

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (690, 'status_rl', 'F');	--	F
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (691, 'status_rl', 'P');	--	P

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (700, 'supervisor_review_indicator_rl', 'COMPLETED');	--	C
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (701, 'supervisor_review_indicator_rl', 'IN-REVIEW');	--	R

INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (706, 'audit_flag_rl', 'REVIEWED');	--	R
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (707, 'audit_flag_rl', 'PENDING');	--	P


-- b_othr_inc_basis_tp_c, other_income_source_type_code, b_salary_basis_tp_c, salary_basis_type_code
/*
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (380, 'income_basis_type', 'ANNUAL');	-- ANNUM 
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (381, 'income_basis_type', 'MONTH');	-- MONTH, MONTHL
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (382, 'income_basis_type', 'OTHER');	-- OTHER (RL other type includes: child_, disabi, invest, pensio rental, second, social, vetera)
INSERT INTO dbo.app_enums (enum_id, type, value) VALUES (383, 'income_basis_type', 'WEEK');		-- WEEK
*/


-- b_job_title_tp_c, title_position


UPDATE STATISTICS dbo.app_enums;