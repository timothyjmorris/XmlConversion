#!/usr/bin/env python3
"""
Script to enhance the mapping_contract.json with nullable, required, and default_value fields
based on the database schema from create_destination_tables.sql.

This script:
1. Parses the SQL CREATE TABLE statements
2. Extracts column nullability and default values
3. Matches against existing contract mappings
4. Adds nullable, required, and default_value fields
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class SchemaParser:
    """Parse SQL CREATE TABLE statements to extract column metadata."""

    def __init__(self, sql_file_path: str):
        self.sql_file_path = sql_file_path
        self.table_schemas = {}

    def parse_sql_file(self) -> Dict[str, Dict[str, Any]]:
        """Parse the SQL file and extract table schemas."""
        with open(self.sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Find all CREATE TABLE blocks
        create_table_pattern = r'CREATE TABLE\s+(\w+)\s*\((.*?)\);'
        matches = re.findall(create_table_pattern, sql_content, re.DOTALL | re.IGNORECASE)
        
        print(f"Found {len(matches)} CREATE TABLE matches")

        for table_name, columns_block in matches:
            print(f"Processing table: {table_name}")
            table_info = self._parse_table_columns(table_name, columns_block)
            if table_info:
                self.table_schemas[table_info['table_name']] = table_info

        return self.table_schemas

    def _parse_table_columns(self, table_name: str, columns_block: str) -> Optional[Dict[str, Any]]:
        """Parse column definitions from a CREATE TABLE columns block."""
        columns = {}
        
        print(f"Parsing columns for table {table_name}:")
        print(f"Columns block: {columns_block[:200]}...")
        
        # Split by commas, but be careful about commas inside parentheses
        column_defs = self._split_column_definitions(columns_block)
        
        if column_defs is None:
            print(f"Failed to split column definitions for {table_name}")
            return None
            
        print(f"Found {len(column_defs)} column definitions")
        
        for col_def in column_defs:
            col_def = col_def.strip()
            
            # Skip comments and empty lines
            if not col_def or col_def.startswith('--') or col_def.startswith('/*'):
                continue
                
            # Skip CONSTRAINT lines that are standalone
            if col_def.upper().startswith('CONSTRAINT') or col_def.upper().startswith('PRIMARY KEY') or col_def.upper().startswith('FOREIGN KEY'):
                continue
            
            print(f"Processing: {col_def[:100]}...")
            
            # Parse column: column_name data_type [NULL|NOT NULL] [DEFAULT value] [CONSTRAINT ...]
            parts = col_def.split()
            if len(parts) < 2:
                continue
                
            col_name = parts[0].strip('[],')
            
            # Skip if column name looks like a comment or invalid
            if not col_name or col_name.startswith('--') or len(col_name) > 100:
                continue
            
            # Handle computed columns (AS keyword)
            if 'AS' in col_def.upper():
                # This is a computed column, skip for now
                continue
            
            data_type = parts[1].strip()
            
            # Handle data types with parameters like varchar(50), decimal(12,2)
            if len(parts) > 2 and '(' in parts[1]:
                data_type = f"{parts[1]} {parts[2]}".strip('(),')
            
            # Check for NULL/NOT NULL
            nullable = True  # Default
            default_value = None
            
            # Look for NULL/NOT NULL
            if 'NOT NULL' in col_def.upper():
                nullable = False
            elif 'NULL' in col_def.upper():
                nullable = True
            
            # Look for DEFAULT
            default_match = re.search(r'DEFAULT\s+([^,\s]+)', col_def, re.IGNORECASE)
            if default_match:
                default_value = default_match.group(1).strip()
                # Clean up
                if default_value.startswith('(') and default_value.endswith(')'):
                    default_value = default_value[1:-1]
            
            columns[col_name] = {
                'data_type': data_type,
                'nullable': nullable,
                'default_value': default_value
            }
            print(f"  Column: {col_name}, nullable: {nullable}, default: {default_value}")

        return {
            'table_name': table_name,
            'columns': columns
        }

    def _split_column_definitions(self, columns_block: str) -> List[str]:
        """Split column definitions by commas, handling nested parentheses and quotes."""
        parts = []
        current = ""
        paren_depth = 0
        in_single_quote = False
        in_double_quote = False
        
        for char in columns_block:
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == '(' and not in_single_quote and not in_double_quote:
                paren_depth += 1
            elif char == ')' and not in_single_quote and not in_double_quote:
                paren_depth -= 1
            elif char == ',' and paren_depth == 0 and not in_single_quote and not in_double_quote:
                parts.append(current.strip())
                current = ""
                continue
            current += char
        
        if current.strip():
            parts.append(current.strip())
        
        return parts
        
class ContractEnhancer:
    """Enhance the contract with schema-derived metadata."""

    def __init__(self, contract_path: str, schema_data: Dict[str, Dict[str, Any]]):
        self.contract_path = contract_path
        self.schema_data = schema_data

    def enhance_contract(self) -> Dict[str, Any]:
        """Add nullable, required, and default_value fields to contract mappings."""
        with open(self.contract_path, 'r', encoding='utf-8') as f:
            contract = json.load(f)

        enhanced_mappings = []

        for mapping in contract.get('mappings', []):
            enhanced_mapping = self._enhance_mapping(mapping)
            enhanced_mappings.append(enhanced_mapping)

        contract['mappings'] = enhanced_mappings
        return contract

    def _enhance_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a single mapping with schema metadata."""
        table_name = mapping.get('target_table')
        column_name = mapping.get('target_column')

        if not table_name or not column_name:
            return mapping

        # Get schema info for this table/column
        table_schema = self.schema_data.get(table_name)
        if not table_schema:
            print(f"Warning: No schema found for table {table_name}")
            return mapping

        column_schema = table_schema['columns'].get(column_name)
        if not column_schema:
            print(f"Warning: No schema found for column {column_name} in table {table_name}")
            return mapping

        # Add schema-derived fields
        enhanced = mapping.copy()

        # nullable: True if column allows NULL
        enhanced['nullable'] = column_schema['nullable']

        # required: True if column is NOT NULL and has no default
        # This is a business decision - NOT NULL columns are generally required
        enhanced['required'] = not column_schema['nullable']

        # default_value: Copy from schema if present
        if column_schema['default_value']:
            enhanced['default_value'] = column_schema['default_value']

        return enhanced


def main():
    """Main script execution."""
    # File paths - adjust for current working directory
    script_dir = Path(__file__).parent
    sql_file = script_dir / "config" / "samples" / "create_destination_tables.sql"
    contract_file = script_dir / "config" / "mapping_contract.json"
    output_file = script_dir / "config" / "mapping_contract_enhanced.json"

    print(f"Script directory: {script_dir}")
    print(f"Parsing SQL schema from: {sql_file}")
    print(f"Enhancing contract: {contract_file}")
    print(f"Output will be saved to: {output_file}")

    # Parse SQL schema
    parser = SchemaParser(str(sql_file))
    schema_data = parser.parse_sql_file()

    print(f"Found {len(schema_data)} tables in schema:")
    for table_name, table_info in schema_data.items():
        print(f"  - {table_name}: {len(table_info['columns'])} columns")

    # Enhance contract
    enhancer = ContractEnhancer(str(contract_file), schema_data)
    enhanced_contract = enhancer.enhance_contract()

    # Save enhanced contract
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_contract, f, indent=2, ensure_ascii=False)

    print(f"\nEnhanced contract saved to: {output_file}")
    print("Please review the changes and verify they are correct before replacing the original contract.")


if __name__ == '__main__':
    main()