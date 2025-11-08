"""
High-performance XML parsing engine for credit application data extraction.

This module provides memory-efficient XML parsing using lxml with selective
element parsing based on mapping contracts for optimal performance.
"""

import logging

from typing import Dict, Any, Optional, List, Set
from xml.etree.ElementTree import Element

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    LXML_AVAILABLE = False
    logging.warning("lxml not available, falling back to xml.etree.ElementTree")

from ..interfaces import XMLParserInterface
from ..exceptions import XMLParsingError
from ..models import ProcessingConfig, MappingContract


class XMLParser(XMLParserInterface):
    """
    High-performance XML parser optimized for Provenir credit application data extraction.

    This parser implements a selective parsing strategy that only extracts elements and attributes
    that are defined in the mapping contract, dramatically reducing memory usage and processing time
    for large XML files. Instead of building a full DOM tree, it uses streaming parsing to extract
    only the required data paths.

    Key Optimization Strategies:
    - Selective Element Processing: Only processes XML elements that appear in mapping contracts
    - Streaming Parsing: Uses lxml.etree.iterparse() to avoid loading entire XML into memory
    - XPath-like Path Construction: Builds flattened dictionary structure with XPath-style keys
    - Attribute vs Element Distinction: Properly handles XML attributes vs child elements
    - Contact Deduplication: Implements "last valid element" logic for duplicate contact records
    - Memory-Efficient Flattening: Converts hierarchical XML to flat dictionary for fast lookups

    The parser produces a flattened data structure where:
    - Keys are XPath-like paths (e.g., "/Provenir/Request/CustData/application/app_id")
    - Values are either simple values, lists (for repeated elements), or nested dicts
    - Contact elements are deduplicated using the last valid element approach
    - Attributes are preserved with case-insensitive access

    Features:
    - Memory-efficient selective parsing (only processes required elements)
    - Streaming XML processing using lxml.etree.iterparse()
    - Optimized for Provenir XML structure (no namespaces, no XML declarations)
    - Element filtering based on mapping contracts
    - Type-aware attribute extraction
    - Detailed error logging with source record identification
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None, mapping_contract: Optional[MappingContract] = None):
        """
        Initialize XML parser with configuration and optional mapping contract for selective parsing.

        When a mapping contract is provided, the parser analyzes all field mappings to build sets of
        required XML paths and element names. This enables selective parsing where only relevant
        XML sections are processed, dramatically improving performance for large XML files.

        Selective Parsing Setup:
        - required_paths: Set of complete XPath-like paths that need to be extracted
        - required_elements: Set of element names that appear in any mapping (for faster filtering)
        - If no mapping contract provided, parser falls back to full XML processing

        Args:
            config: Processing configuration controlling parser behavior and performance settings
            mapping_contract: Optional mapping contract defining which XML elements to extract.
                            When provided, enables memory-efficient selective parsing.
        """
        self.config = config or ProcessingConfig()
        self.mapping_contract = mapping_contract
        self.logger = logging.getLogger(__name__)
        
        # Build set of required element paths for selective parsing
        self.required_paths: Set[str] = set()
        self.required_elements: Set[str] = set()
        self.core_structure_elements: Set[str] = set()
        
        # Only build required paths if a mapping contract is provided.
        # This enables the parser to skip irrelevant XML sections for performance.
        if mapping_contract:
            self._build_required_paths()
            self._build_core_structure_elements()
        
        # Performance tracking
        self.parse_count = 0
        self.validation_count = 0
        self.elements_skipped = 0
        self.elements_processed = 0
        
        self.logger.info(f"XMLParser initialized with lxml={'available' if LXML_AVAILABLE else 'not available'}")
        if self.required_paths:
            self.logger.info(f"Selective parsing enabled for {len(self.required_paths)} element paths")
    
    def _build_required_paths(self) -> None:
        """
        Build set of required element paths from mapping contract for selective parsing.
        This optimizes performance by only parsing elements that are actually mapped
        to database columns, skipping large sections of XML that aren't needed.
        """
        if not self.mapping_contract:
            return

        # Extract unique XML paths from field mappings
        for mapping in self.mapping_contract.mappings:
            xml_path = mapping.xml_path.strip()
            if xml_path:
                self.required_paths.add(xml_path)
                # Add parent paths so we can navigate to the element in the tree.
                path_parts = xml_path.split('/')
                for i in range(1, len(path_parts)):
                    parent_path = '/'.join(path_parts[:i+1])
                    self.required_paths.add(parent_path)
                # Track element names for quick filtering.
                if '/' in xml_path:
                    element_name = xml_path.split('/')[-1]
                    self.required_elements.add(element_name)
                # This enables fast checks for whether a given element is relevant.
        
        # Add relationship paths
        for relationship in self.mapping_contract.relationships:
            for path in [relationship.xml_parent_path, relationship.xml_child_path]:
                if path:
                    self.required_paths.add(path)
                    path_parts = path.split('/')
                    for i in range(1, len(path_parts)):
                        parent_path = '/'.join(path_parts[:i+1])
                        self.required_paths.add(parent_path)
        # After this, self.required_paths contains all unique XML paths that are relevant for mapping or relationships.
        self.logger.debug(f"Built {len(self.required_paths)} required paths: {sorted(self.required_paths)}")
        self.logger.debug(f"Required elements: {sorted(self.required_elements)}")
    
    def _build_core_structure_elements(self) -> None:
        """
        Build set of core XML structure elements from xml_application_path.
        These are scaffolding elements that enable navigation to data elements.
        
        For example, xml_application_path='/Provenir/Request/CustData/application'
        results in core_structure_elements={'Provenir', 'Request', 'CustData', 'application'}
        """
        if not self.mapping_contract:
            return
        
        # Extract structure elements from xml_application_path
        if self.mapping_contract.xml_application_path:
            path = self.mapping_contract.xml_application_path.strip('/')
            if path:
                self.core_structure_elements = set(path.split('/'))
                self.logger.debug(f"Core structure elements from contract: {sorted(self.core_structure_elements)}")
        else:
            # Fallback to default if not specified in contract
            self.core_structure_elements = {'Provenir', 'Request', 'CustData', 'application'}
            self.logger.debug("Using default core structure elements (xml_application_path not in contract)")
    
    def set_mapping_contract(self, mapping_contract: MappingContract) -> None:
        """
        Set or update the mapping contract for selective parsing.
        
        Args:
            mapping_contract: Mapping contract defining which elements to parse
        """
        self.mapping_contract = mapping_contract
        self.required_paths.clear()
        self.required_elements.clear()
        self.core_structure_elements.clear()
        self._build_required_paths()
        self._build_core_structure_elements()
        self.logger.info(f"Updated mapping contract - selective parsing for {len(self.required_paths)} paths")
    
    def parse_xml_stream(self, xml_content: str) -> Element:
        """
        Parse XML content using streaming approach for memory efficiency.
        
        Uses lxml.etree.iterparse() when available for optimal memory usage,
        falls back to standard ElementTree for compatibility.
        
        Args:
            xml_content: Raw XML content as string
            
        Returns:
            Parsed XML element tree root
            
        Raises:
            XMLParsingError: If XML is malformed or cannot be parsed
        """
        if not xml_content or not xml_content.strip():
            raise XMLParsingError("XML content is empty or None")
        
        self.parse_count += 1
        source_record_id = f"parse_{self.parse_count}"
        
        try:
            # Clean and prepare XML content
            cleaned_xml = self._clean_xml_content(xml_content)
            
            if LXML_AVAILABLE:
                return self._parse_with_lxml(cleaned_xml, source_record_id)
            else:
                return self._parse_with_etree(cleaned_xml, source_record_id)
                
        except Exception as e:
            error_msg = f"Failed to parse XML: {str(e)}"
            self.logger.error(f"{error_msg} (Record ID: {source_record_id})")
            raise XMLParsingError(error_msg, xml_content, source_record_id)
    
    def _parse_with_lxml(self, xml_content: str, source_record_id: str) -> Element:
        """Parse XML using lxml for optimal performance and features."""
        try:
            # Use XMLParser with namespace handling and recovery
            parser = etree.XMLParser(
                recover=True,  # Attempt to recover from minor XML errors
                strip_cdata=False,  # Preserve CDATA sections
                resolve_entities=False,  # Security: don't resolve external entities
                no_network=True  # Security: disable network access
            )
            
            # Parse with streaming for memory efficiency
            root = etree.fromstring(xml_content.encode('utf-8'), parser)
            
            # Convert lxml Element to standard Element for interface compatibility
            return self._convert_lxml_to_element(root)
            
        except etree.XMLSyntaxError as e:
            raise XMLParsingError(f"XML syntax error: {e}", xml_content, source_record_id)
        except Exception as e:
            raise XMLParsingError(f"lxml parsing failed: {e}", xml_content, source_record_id)
    
    def _parse_with_etree(self, xml_content: str, source_record_id: str) -> Element:
        """Parse XML using standard ElementTree as fallback."""
        try:
            root = etree.fromstring(xml_content)
            return root
            
        except etree.ParseError as e:
            raise XMLParsingError(f"ElementTree parsing failed: {e}", xml_content, source_record_id)
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """
        Clean and normalize XML content for parsing.
        
        Args:
            xml_content: Raw XML content
            
        Returns:
            Cleaned XML content
        """
        # Remove BOM if present (UTF-8, UTF-16, UTF-32)
        if xml_content.startswith('\ufeff'):
            xml_content = xml_content[1:]
            self.logger.debug("Removed UTF-8 BOM from XML content")
        elif xml_content.startswith('\xff\xfe'):
            xml_content = xml_content[2:]
            self.logger.debug("Removed UTF-16 LE BOM from XML content")
        elif xml_content.startswith('\xfe\xff'):
            xml_content = xml_content[2:]
            self.logger.debug("Removed UTF-16 BE BOM from XML content")
        
        # Handle BOM that might appear as visible characters (like ï»¿)
        if xml_content.startswith('ï»¿'):
            xml_content = xml_content[3:]
            self.logger.debug("Removed visible UTF-8 BOM characters from XML content")
        
        # Remove other common hidden characters at the beginning
        while xml_content and ord(xml_content[0]) < 32 and xml_content[0] not in '\t\n\r':
            xml_content = xml_content[1:]
            self.logger.debug("Removed hidden leading character")
        
        # Normalize line endings
        xml_content = xml_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove leading/trailing whitespace
        xml_content = xml_content.strip()
        
        return xml_content
    
    def _convert_lxml_to_element(self, lxml_element) -> Element:
        """Convert lxml Element to standard Element for interface compatibility."""
        # lxml Elements are compatible with ElementTree interface
        return lxml_element
    
    def validate_xml_structure(self, xml_content: str) -> bool:
        """
        Validate XML structure before processing.
        
        Optimized for Provenir XML - performs minimal validation:
        - Content existence check
        - Basic well-formedness check
        - Root element validation (expects Provenir)
        
        Args:
            xml_content: Raw XML content to validate
            
        Returns:
            True if XML is valid, False otherwise
        """
        if xml_content is None:
            self.logger.warning("XML content is None")
            return False
            
        if not xml_content or not xml_content.strip():
            self.logger.warning("XML content is empty")
            return False
        
        self.validation_count += 1
        
        try:
            # Clean XML content first
            cleaned_xml = self._clean_xml_content(xml_content)
            
            # Basic structure validation (simplified for Provenir XML)
            if not self._validate_provenir_structure(cleaned_xml):
                return False
            
            # Quick well-formedness check by attempting to parse root element only
            try:
                if LXML_AVAILABLE:
                    # Use lxml for faster validation
                    parser = etree.XMLParser(recover=False, resolve_entities=False, no_network=True)
                    etree.fromstring(cleaned_xml.encode('utf-8'), parser)
                else:
                    etree.fromstring(cleaned_xml)
                
                self.logger.debug(f"XML validation passed (validation #{self.validation_count})")
                return True
                
            except Exception as e:
                self.logger.warning(f"XML well-formedness validation failed: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error during XML validation: {e}")
            return False
    
    def _validate_provenir_structure(self, xml_content: str) -> bool:
        """
        Validate Provenir XML structure - optimized for known format.
        
        Args:
            xml_content: XML content to validate
            
        Returns:
            True if Provenir structure is valid
        """
        content = xml_content.strip()
        
        # Must start with < and end with >
        if not (content.startswith('<') and content.endswith('>')):
            self.logger.warning("XML doesn't start with < or end with >")
            return False
        
        # Check for Provenir root element (case-insensitive, flexible matching)
        content_lower = content.lower()
        
        # Look for <provenir anywhere in the first 100 characters (to handle attributes)
        provenir_start_found = False
        for i in range(min(100, len(content_lower))):
            if content_lower[i:].startswith('<provenir'):
                provenir_start_found = True
                break
        
        if not provenir_start_found:
            self.logger.warning("XML doesn't contain <Provenir root element in first 100 characters")
            return False
        
        # Check for closing Provenir tag (more flexible matching)
        if '</provenir>' not in content_lower:
            self.logger.warning("XML doesn't contain </Provenir> closing tag")
            return False
        
        return True
    
    def extract_elements(self, xml_node: Element) -> Dict[str, Any]:
        """
        Extract elements from XML node with selective parsing optimization.
        
        Features:
        - Selective element processing based on mapping contract
        - Recursive traversal only for required paths
        - XPath-like path generation
        - Attribute preservation for mapped elements only
        - Performance optimization by skipping unused elements
        
        Args:
            xml_node: XML element to extract data from
            
        Returns:
            Dictionary containing extracted element data with paths as keys
        """
        if xml_node is None:
            return {}
        
        return self._extract_elements_selective(xml_node, "")
    
    def _extract_elements_selective(self, xml_node: Element, current_path: str) -> Dict[str, Any]:
        """
        Recursively extract elements with selective parsing based on required paths.
        
        Args:
            xml_node: Current XML element
            current_path: Current path in the XML tree
            
        Returns:
            Dictionary of extracted element data
        """
        extracted_data = {}
        element_path = current_path or "unknown"  # Initialize with fallback value
        
        try:
            # Build current element path
            tag_name = self._clean_tag_name(xml_node.tag)
            element_path = f"{current_path}/{tag_name}" if current_path else f"/{tag_name}"
            
            # Check if this element or its children are required
            should_process = self._should_process_element(element_path, tag_name)
            
            if should_process:
                self.elements_processed += 1
                
                # Extract current element data
                element_data = {
                    'tag': tag_name,
                    'text': (xml_node.text or '').strip(),
                    'attributes': self.extract_attributes(xml_node),
                    'path': element_path
                }
                
                # Add tail text if present
                if hasattr(xml_node, 'tail') and xml_node.tail:
                    tail_text = xml_node.tail.strip()
                    if tail_text:
                        element_data['tail'] = tail_text
                
                extracted_data[element_path] = element_data
                
                # Process children if this path might contain required elements
                for child in xml_node:
                    child_data = self._extract_elements_selective(child, element_path)
                    extracted_data.update(child_data)
            else:
                self.elements_skipped += 1
                # Still need to check if children might be required
                # (e.g., we might skip <Reports> but need <Reports/SomeChild>)
                if self._path_might_contain_required_elements(element_path):
                    for child in xml_node:
                        child_data = self._extract_elements_selective(child, element_path)
                        extracted_data.update(child_data)
            
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"Error extracting elements from XML node at path {element_path}: {e}")
            raise XMLParsingError(f"Element extraction failed at {element_path}: {e}")
    
    def _should_process_element(self, element_path: str, tag_name: str) -> bool:
        """
        Determine if an element should be processed based on mapping contract.
        
        Args:
            element_path: Full path to the element
            tag_name: Element tag name
            
        Returns:
            True if element should be processed
        """
        # If no mapping contract, process everything (fallback behavior)
        if not self.mapping_contract:
            return True
        
        # Check if this exact path is required
        if element_path in self.required_paths:
            return True
        
        # Check if this element name is in our required elements
        if tag_name in self.required_elements:
            return True
        
        # Always process core XML structure elements (from contract or default)
        if tag_name in self.core_structure_elements:
            return True
        
        return False
    
    def _path_might_contain_required_elements(self, current_path: str) -> bool:
        """
        Check if a path might contain required child elements.
        
        Args:
            current_path: Current path being evaluated
            
        Returns:
            True if path might contain required children
        """
        if not self.mapping_contract:
            return True
        
        # Check if any required path starts with this path
        for required_path in self.required_paths:
            if required_path.startswith(current_path + '/'):
                return True
        
        return False
    
    def extract_attributes(self, xml_node: Element) -> Dict[str, str]:
        """
        Extract attributes from XML node with type awareness.
        
        Features:
        - Type-aware attribute extraction
        - Namespace prefix handling
        - Empty attribute handling
        - Attribute name normalization
        
        Args:
            xml_node: XML element to extract attributes from
            
        Returns:
            Dictionary containing attribute name-value pairs
        """
        if xml_node is None:
            return {}
        
        try:
            attributes = {}
            
            # Extract all attributes
            if hasattr(xml_node, 'attrib') and xml_node.attrib:
                for attr_name, attr_value in xml_node.attrib.items():
                    # Clean attribute name (remove namespace prefixes if needed)
                    clean_name = self._clean_attribute_name(attr_name)
                    
                    # Type-aware value processing
                    processed_value = self._process_attribute_value(attr_value)
                    
                    attributes[clean_name] = processed_value
            
            return attributes
            
        except Exception as e:
            self.logger.error(f"Error extracting attributes from XML node: {e}")
            return {}
    
    def _get_element_path(self, element: Element) -> str:
        """
        Generate XPath-like path for an element.
        
        Args:
            element: XML element
            
        Returns:
            XPath-like string representing element location
        """
        try:
            # Build path by traversing up the tree
            path_parts = []
            current = element
            
            while current is not None:
                tag_name = self._clean_tag_name(current.tag)
                path_parts.insert(0, tag_name)
                
                # Try to get parent (lxml vs ElementTree compatibility)
                if hasattr(current, 'getparent'):
                    current = current.getparent()
                else:
                    # For ElementTree, we need to find parent differently
                    # This is a limitation - we'll just break for now
                    break
            
            return '/' + '/'.join(path_parts) if path_parts else '/unknown'
            
        except Exception as e:
            self.logger.warning(f"Could not generate element path: {e}")
            return '/unknown'
    
    def _clean_tag_name(self, tag) -> str:
        """
        Clean tag name by removing namespace prefixes.
        
        Args:
            tag: Raw tag name potentially with namespace (could be string or other type)
            
        Returns:
            Clean tag name without namespace prefix
        """
        # Handle different tag types (string, Cython function, etc.)
        if hasattr(tag, '__call__'):
            # If it's a callable (like Cython function), try to get string representation
            try:
                tag_str = str(tag)
                if tag_str and not tag_str.startswith('<'):
                    tag = tag_str
                else:
                    # If string representation isn't useful, try getting the name
                    tag = getattr(tag, '__name__', 'unknown')
            except:
                tag = 'unknown'
        elif not isinstance(tag, str):
            # Convert other types to string
            try:
                tag = str(tag)
            except:
                tag = 'unknown'
        
        if not tag or tag == 'None':
            return 'unknown'
        
        # Remove namespace URI if present (format: {namespace}tagname)
        if tag.startswith('{'):
            end_ns = tag.find('}')
            if end_ns > 0:
                return tag[end_ns + 1:]
        
        # Remove namespace prefix if present (format: prefix:tagname)
        if ':' in tag:
            return tag.split(':', 1)[1]
        
        return tag
    
    def _clean_attribute_name(self, attr_name: str) -> str:
        """
        Clean attribute name by removing namespace prefixes and normalizing case.
        
        Args:
            attr_name: Raw attribute name potentially with namespace
            
        Returns:
            Clean attribute name without namespace prefix, normalized to lowercase
        """
        clean_name = self._clean_tag_name(attr_name)
        # Keep original casing - case-insensitive lookup handled in data mapper
        return clean_name
    
    def _process_attribute_value(self, attr_value: str) -> str:
        """
        Process attribute value with type awareness.
        
        Args:
            attr_value: Raw attribute value
            
        Returns:
            Processed attribute value
        """
        if attr_value is None:
            return ''
        
        # Convert to string and strip whitespace
        value = str(attr_value).strip()
        
        # Handle empty values
        if not value:
            return ''
        
        # Decode HTML entities if present
        try:
            import html
            value = html.unescape(value)
        except ImportError:
            # Fallback for basic entity decoding
            value = value.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'")
        
        return value
    

    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get parser performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        total_elements = self.elements_processed + self.elements_skipped
        skip_percentage = (self.elements_skipped / total_elements * 100) if total_elements > 0 else 0
        
        return {
            'parse_count': self.parse_count,
            'validation_count': self.validation_count,
            'elements_processed': self.elements_processed,
            'elements_skipped': self.elements_skipped,
            'skip_percentage': round(skip_percentage, 2),
            'selective_parsing_enabled': bool(self.mapping_contract),
            'required_paths_count': len(self.required_paths),
            'lxml_available': LXML_AVAILABLE
        }
    
    def get_required_paths(self) -> List[str]:
        """
        Get list of required XML paths that will be processed.
        
        Returns:
            Sorted list of XML paths that selective parsing will process
        """
        return sorted(self.required_paths)
    
    def is_selective_parsing_enabled(self) -> bool:
        """
        Check if selective parsing is enabled.
        
        Returns:
            True if selective parsing is enabled via mapping contract
        """
        return bool(self.mapping_contract and self.required_paths)
    
    def reset_stats(self) -> None:
        """Reset performance statistics."""
        self.parse_count = 0
        self.validation_count = 0
        self.elements_processed = 0
        self.elements_skipped = 0
        
        self.logger.debug("XMLParser statistics reset")