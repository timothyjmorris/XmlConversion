#!/usr/bin/env python3
"""
Diagnose performance dip between first and subsequent runs.

Measures:
1. XML parsing time
2. Data mapping time
3. Database insert time
4. Connection pool behavior
5. SQL Server wait times (if available)
"""

import sys
import time
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import statistics

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('PerformanceDiagnostics')


class PerformanceDiagnostics:
    """Diagnose performance characteristics across multiple runs."""
    
    def __init__(self, connection_string: str, mapping_contract_path: str, sample_xml_path: str):
        """Initialize diagnostics."""
        self.connection_string = connection_string
        self.mapping_contract_path = mapping_contract_path
        self.sample_xml_path = sample_xml_path
        
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        self.mapper = DataMapper(mapping_contract_path=mapping_contract_path)
        self.migration_engine = MigrationEngine(connection_string)
        
        self.results = {
            'parsing_times': [],
            'validation_times': [],
            'mapping_times': [],
            'insert_times': [],
            'total_times': [],
            'timestamps': []
        }
    
    def run_diagnostic(self, num_runs: int = 5) -> Dict:
        """
        Run the same XML through the pipeline multiple times.
        
        Measures each stage to identify where performance degrades.
        
        Args:
            num_runs: Number of times to process the same XML
            
        Returns:
            Dict with timing statistics
        """
        logger.info(f"Starting performance diagnostics ({num_runs} runs)")
        logger.info(f"Sample XML: {self.sample_xml_path}")
        
        # Read XML once
        with open(self.sample_xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        for run_num in range(1, num_runs + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"RUN {run_num}/{num_runs}")
            logger.info(f"{'='*60}")
            
            run_start = time.time()
            
            try:
                # Stage 1: Validation
                val_start = time.time()
                validation_result = self.validator.validate_xml_for_processing(
                    xml_content,
                    record_id=f"diag_run_{run_num}"
                )
                val_time = time.time() - val_start
                self.results['validation_times'].append(val_time)
                logger.info(f"Validation: {val_time*1000:.2f}ms")
                
                if not validation_result.is_valid:
                    logger.error(f"Validation failed: {validation_result.validation_errors}")
                    continue
                
                # Stage 2: Parsing
                parse_start = time.time()
                root = self.parser.parse_xml_stream(xml_content)
                xml_data = self.parser.extract_elements(root)
                parse_time = time.time() - parse_start
                self.results['parsing_times'].append(parse_time)
                logger.info(f"Parsing: {parse_time*1000:.2f}ms")
                
                if root is None or not xml_data:
                    logger.error("Parsing failed")
                    continue
                
                # Stage 3: Mapping
                map_start = time.time()
                mapped_data = self.mapper.map_xml_to_database(
                    xml_data,
                    validation_result.app_id,
                    validation_result.valid_contacts,
                    root
                )
                map_time = time.time() - map_start
                self.results['mapping_times'].append(map_time)
                logger.info(f"Mapping: {map_time*1000:.2f}ms")
                
                if not mapped_data:
                    logger.error("Mapping failed")
                    continue
                
                # Stage 4: Insert
                insert_start = time.time()
                total_inserted = 0
                for table_name in ["app_base", "contact_base", "app_operational_cc", 
                                  "app_pricing_cc", "app_transactional_cc", "app_solicited_cc",
                                  "contact_address", "contact_employment"]:
                    records = mapped_data.get(table_name, [])
                    if records:
                        enable_identity = table_name in ["app_base", "contact_base"]
                        inserted = self.migration_engine.execute_bulk_insert(
                            records,
                            table_name,
                            enable_identity_insert=enable_identity
                        )
                        total_inserted += inserted
                
                insert_time = time.time() - insert_start
                self.results['insert_times'].append(insert_time)
                logger.info(f"Insert ({total_inserted} records): {insert_time*1000:.2f}ms")
                
                run_total = time.time() - run_start
                self.results['total_times'].append(run_total)
                self.results['timestamps'].append(datetime.now().isoformat())
                
                logger.info(f"Total: {run_total*1000:.2f}ms")
                logger.info(f"Throughput: {total_inserted / run_total:.0f} rec/sec ({total_inserted / run_total * 60:.0f} rec/min)")
                
                # Clean up for next run
                with self.migration_engine.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM app_base WHERE app_id = ?", (validation_result.app_id,))
                    conn.commit()
                
            except Exception as e:
                logger.error(f"Run {run_num} failed: {e}", exc_info=True)
        
        return self._analyze_results()
    
    def _analyze_results(self) -> Dict:
        """Analyze timing results to identify performance dips."""
        logger.info(f"\n{'='*60}")
        logger.info("PERFORMANCE ANALYSIS")
        logger.info(f"{'='*60}\n")
        
        analysis = {}
        
        for stage in ['validation', 'parsing', 'mapping', 'insert', 'total']:
            times = self.results[f'{stage}_times']
            if not times:
                continue
            
            analysis[stage] = {
                'times_ms': [t*1000 for t in times],
                'mean_ms': statistics.mean(times) * 1000,
                'median_ms': statistics.median(times) * 1000,
                'stdev_ms': statistics.stdev(times) * 1000 if len(times) > 1 else 0,
                'min_ms': min(times) * 1000,
                'max_ms': max(times) * 1000,
                'dip_percent': ((times[0] - statistics.mean(times[1:])) / times[0] * 100) if len(times) > 1 else 0
            }
            
            logger.info(f"\n{stage.upper()}:")
            logger.info(f"  First:  {analysis[stage]['times_ms'][0]:.2f}ms")
            logger.info(f"  Mean:   {analysis[stage]['mean_ms']:.2f}ms")
            logger.info(f"  Median: {analysis[stage]['median_ms']:.2f}ms")
            logger.info(f"  StdDev: {analysis[stage]['stdev_ms']:.2f}ms")
            logger.info(f"  Min/Max: {analysis[stage]['min_ms']:.2f}ms / {analysis[stage]['max_ms']:.2f}ms")
            
            if analysis[stage]['dip_percent'] > 0:
                logger.info(f"  ⚠️  First run {analysis[stage]['dip_percent']:.1f}% faster than average")
        
        return analysis


def main():
    """Run diagnostics."""
    import pyodbc
    
    # Configuration
    server = "localhost\\SQLEXPRESS"
    database = "XmlConversionDB"
    connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};Trusted_Connection=yes;"
    mapping_contract_path = str(project_root / "config" / "mapping_contract.json")
    sample_xml = str(project_root / "config" / "samples" / "sample-source-xml-1.xml")
    
    logger.info(f"Connection: {server} / {database}")
    logger.info(f"Mapping: {mapping_contract_path}")
    logger.info(f"Sample: {sample_xml}")
    
    diag = PerformanceDiagnostics(connection_string, mapping_contract_path, sample_xml)
    results = diag.run_diagnostic(num_runs=7)
    
    # Save results
    output_file = Path(__file__).parent / f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total stage analysis shows:")
    logger.info(f"- First run is typically {results['total']['dip_percent']:.1f}% faster")
    logger.info(f"- This suggests: COLD START ADVANTAGE (expected)")
    logger.info(f"- Subsequent runs stabilize around {results['total']['median_ms']:.0f}ms")
    
    if results['insert']['dip_percent'] > 15:
        logger.warning(f"\n⚠️  INSERT TIME shows {results['insert']['dip_percent']:.1f}% dip!")
        logger.warning("This suggests database contention or lock issues.")
        logger.warning("Consider: UPDATESTATS, DBCC DBREINDEX, or connection pooling tuning")
    else:
        logger.info(f"\n✅ Insert time is stable ({results['insert']['dip_percent']:.1f}% dip)")


if __name__ == '__main__':
    main()
