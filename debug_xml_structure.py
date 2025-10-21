#!/usr/bin/env python3

from xml_extractor.parsing.xml_parser import XMLParser

def debug_xml_structure():
    print("Debugging XML structure...")
    
    # Load the sample XML
    with open('config/samples/sample-source-xml-contact-test.xml', 'r') as f:
        xml_content = f.read()

    print(f"XML content length: {len(xml_content)}")
    print(f"XML starts with: {xml_content[:100]}")

    # Parse and extract
    parser = XMLParser()
    
    # First validate
    print(f"XML validation: {parser.validate_xml_structure(xml_content)}")
    
    try:
        root = parser.parse_xml_stream(xml_content)
        print(f"Root parsed successfully: {root is not None}")
        
        if root is not None:
            print(f"Root element tag: {root.tag}")
            print(f"Root element attributes: {root.attrib}")
            
            # Check Request element
            request_elem = root.find('Request')
            if request_elem is not None:
                print(f"Request element attributes: {request_elem.attrib}")
                print(f"Request ID: {request_elem.get('ID')}")
            else:
                print("No Request element found")
            
            xml_data = parser.extract_elements(root)
            print(f"Total keys in xml_data: {len(xml_data)}")
            
            print("\nKeys containing 'Request' or 'Provenir':")
            for key in sorted(xml_data.keys()):
                if 'Request' in key or 'Provenir' in key:
                    print(f"  {key}: {xml_data[key]}")
            
            print("\nContact-related keys:")
            for key in sorted(xml_data.keys()):
                if 'contact' in key.lower():
                    print(f"  {key}: {xml_data[key]}")
            
            print("\nAll keys (first 20):")
            for i, key in enumerate(sorted(xml_data.keys())):
                if i < 20:
                    print(f"  {key}")
                else:
                    print(f"  ... and {len(xml_data) - 20} more")
                    break
        else:
            print("Root is None - parsing failed")
            
    except Exception as e:
        print(f"Error during parsing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_xml_structure()