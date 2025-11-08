
import unittest
import sys
import os

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)



class TestPreProcessingValidator(unittest.TestCase):
    def setUp(self):
        self.validator = PreProcessingValidator()
        with open('config/samples/sample-source-xml-contact-test.xml', 'r') as f:
            self.credit_card_xml = f.read()
        with open('config/samples/sample-source-xml-reclending-schema.xml', 'r') as f:
            self.rec_lending_xml = f.read()

    def test_valid_credit_card_application(self):
        result = self.validator.validate_xml_for_processing(self.credit_card_xml)
        self.assertTrue(result.is_valid, "Should accept valid Credit Card application XML")
        self.assertEqual(result.validation_errors, [], "Should have no validation errors for valid Credit Card XML")
        self.assertIsNotNone(result.app_id, "Should extract app_id from valid Credit Card XML")

    def test_rec_lending_application_rejected(self):
        result = self.validator.validate_xml_for_processing(self.rec_lending_xml)
        self.assertFalse(result.is_valid, "Should reject Rec Lending application XML")
        self.assertTrue(any('Rec Lending' in err for err in result.validation_errors), "Should report Rec Lending as unsupported")

    def test_rec_lending_application_structure(self):
        # Inspect the parsed structure for Rec Lending XML
        xml_data = self.validator._convert_elements_to_data_structure(
            self.validator.parser.extract_elements(
                self.validator.parser.parse_xml_stream(self.rec_lending_xml)
            )
        )
        # print("Rec Lending xml_data keys:", list(xml_data.keys()))
        # print("Rec Lending xml_data:", xml_data)
        # Optionally, inspect nested structure
        # import pprint
        # pprint.pprint(xml_data)

if __name__ == '__main__':
    unittest.main()
