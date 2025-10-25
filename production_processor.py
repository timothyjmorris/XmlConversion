#!/usr/bin/env python3
"""
Production XML Processing Script

Optimized for running on production SQL Server with comprehensive monitoring
and performance optimization. Designed to be run from command line with
minimal overhead and maximum throughput.

Usage:
    Windows Auth:
        python production_processor.py --server "localhost\\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --batch-size 25 --limit 25 --log-level INFO
    SQL Server Auth:
        python production_processor.py --server "your-sql-server" --database "YourDatabase" --username "your-user" --password "your-pass" --workers 4 --log-level INFO
    Performance Testing
        python production_processor.py --server "your-sql-server" --database "YourDatabase" --workers 4 --limit 1000 --log-level ERROR

    * don't forget to use --log-level INFO (or higher to see progress in console!)

    Batch vs Limit Explained
    --batch-size (Processing Batches)
        What it controls: How many XML records to process at once before moving to the next batch
        Purpose: Memory management and progress tracking
        Example: --batch-size 25 means:
        Get 25 XML records from database
        Process all 25 in parallel (with your 4 workers)
        Save metrics, show progress
        Get next 25 records
        Repeat until done
    --limit (Total Records)
        What it controls: Maximum total XML records to process in the entire run
        Purpose: Testing/limiting scope
        Example: --limit 100 means:
        Stop after processing 100 total records
        Still uses your batch-size for chunking
        How They Work Together

    Example: --batch-size 25 --limit 100
        Batch 1: Process records 1-25
        Batch 2: Process records 26-50
        Batch 3: Process records 51-75
        Batch 4: Process records 76-100
        Stop (reached limit)

    Example: --batch-size 25 (no limit)
        Processes ALL XML records in your database
        25 at a time until no more records

    Recommendations
        For Testing:
            --batch-size 25 --limit 100  # Process 100 records total, 25 at a time
        For Production:
            --batch-size 50              # Process all records, 50 at a time (no limit)
        For Performance Testing:
            --batch-size 100 --limit 1000 # Test with 1


Features:
- Command line configuration
- Production-optimized logging
- Real-time progress monitoring
- Performance metrics export
- Graceful error handling
- Resume capability
"""

import argparse
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from xml_extractor.processing.parallel_coordinator import ParallelCoordinator
from xml_extractor.database.migration_engine import MigrationEngine


class ProductionProcessor:
    """Production-optimized XML processor with monitoring and performance tracking."""
    
    def __init__(self, server: str, database: str, username: str = None, password: str = None,
                 workers: int = 4, batch_size: int = 100, log_level: str = "INFO"):
        """
        Initialize production processor.
        
        Args:
            server: SQL Server instance (e.g., "localhost\\SQLEXPRESS" or "prod-server")
            database: Database name
            username: SQL Server username (optional, uses Windows auth if not provided)
            password: SQL Server password (optional)
            workers: Number of parallel workers
            batch_size: Records to process per batch
            log_level: Logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG)
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.workers = workers
        self.batch_size = batch_size
        
        # Build connection string
        self.connection_string = self._build_connection_string()
        
        # Performance tracking (must be before logging setup)
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        
        # Set up production logging
        self._setup_logging(log_level)
        
        # Initialize components
        self.mapping_contract_path = str(project_root / "config" / "credit_card_mapping_contract.json")
        
        self.logger.info(f"ProductionProcessor initialized:")
        self.logger.info(f"  Server: {server}")
        self.logger.info(f"  Database: {database}")
        self.logger.info(f"  Workers: {workers}")
        self.logger.info(f"  Processing Batch Size: {batch_size}")
        self.logger.info(f"  Session ID: {self.session_id}")
        self.logger.debug(f"  Connection String: {self.connection_string}")
    
    def _build_connection_string(self) -> str:
        """Build SQL Server connection string."""
        # Handle server name formatting (replace double backslash with single)
        server_name = self.server.replace('\\\\', '\\')
        
        if self.username and self.password:
            # SQL Server authentication
            return (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                   f"SERVER={server_name};"
                   f"DATABASE={self.database};"
                   f"UID={self.username};"
                   f"PWD={self.password};"
                   f"TrustServerCertificate=yes;")
        else:
            # Windows authentication
            return (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                   f"SERVER={server_name};"
                   f"DATABASE={self.database};"
                   f"Trusted_Connection=yes;"
                   f"TrustServerCertificate=yes;")
    
    def _setup_logging(self, log_level: str):
        """Set up production-optimized logging."""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Configure logging
        log_file = logs_dir / f"production_{self.session_id}.log"
        
        # Set root logger level to suppress all other module noise
        logging.getLogger().setLevel(logging.WARNING)
        
        # Configure our specific logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove any existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatters
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler (logs everything at our configured level)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        
        # Console handler (only shows INFO and above for our logger)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Add handlers to our logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Suppress all other loggers (xml_extractor modules, etc.)
        logging.getLogger('xml_extractor').setLevel(logging.WARNING)
        logging.getLogger('lxml').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        self.logger.info(f"Logging initialized: {log_file}")
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            migration_engine = MigrationEngine(self.connection_string)
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                self.logger.info(f"Database connection successful: {version}")
                return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
    
    def get_xml_records(self, limit: Optional[int] = None, offset: int = 0) -> List[Tuple[int, str]]:
        """
        Extract XML records from app_xml table.
        
        Args:
            limit: Maximum number of records to retrieve (None for all)
            offset: Number of records to skip
            
        Returns:
            List of (app_id, xml_content) tuples
        """
        self.logger.info(f"Extracting XML records (limit={limit}, offset={offset})")
        
        xml_records = []
        
        try:
            migration_engine = MigrationEngine(self.connection_string)
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query - exclude apps that have already been processed
                if limit:
                    query = f"""
                        SELECT ax.app_id, ax.xml 
                        FROM app_xml ax
                        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
                        WHERE ax.xml IS NOT NULL 
                        AND DATALENGTH(ax.xml) > 100
                        AND ab.app_id IS NULL  -- Only get apps not already processed
                        ORDER BY ax.app_id
                        OFFSET {offset} ROWS
                        FETCH NEXT {limit} ROWS ONLY
                    """
                else:
                    query = f"""
                        SELECT ax.app_id, ax.xml 
                        FROM app_xml ax
                        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
                        WHERE ax.xml IS NOT NULL 
                        AND DATALENGTH(ax.xml) > 100
                        AND ab.app_id IS NULL  -- Only get apps not already processed
                        ORDER BY ax.app_id
                        OFFSET {offset} ROWS
                    """
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                seen_app_ids = set()
                for row in rows:
                    app_id = row[0]
                    xml_content = row[1]
                    
                    if xml_content and len(xml_content.strip()) > 0:
                        # Check for duplicate app_ids in the same batch
                        if app_id in seen_app_ids:
                            self.logger.warning(f"Duplicate app_id {app_id} found in app_xml table - skipping duplicate")
                            continue
                        seen_app_ids.add(app_id)
                        xml_records.append((app_id, xml_content))
                
                self.logger.info(f"Extracted {len(xml_records)} XML records (excluding already processed)")
                
                # Log if we found any duplicates
                if len(seen_app_ids) < len(rows):
                    duplicates_found = len(rows) - len(seen_app_ids)
                    self.logger.warning(f"Found {duplicates_found} duplicate app_ids in app_xml table")
                
        except Exception as e:
            self.logger.error(f"Failed to extract XML records: {e}")
            raise
        
        return xml_records
    
    def process_batch(self, xml_records: List[Tuple[int, str]]) -> dict:
        """
        Process a batch of XML applications with full monitoring.
        
        Success Rate Definition:
            success_rate = (applications_successful / applications_processed) * 100
            
            - applications_successful: XML applications completely processed with data inserted into database
            - applications_processed: Total XML applications attempted 
            - applications_failed: XML applications that failed at any stage (parsing, mapping, or insertion)
            
        Returns:
            Dictionary containing processing metrics including failed_apps list with failure details
        """
        if not xml_records:
            self.logger.warning("No XML records to process")
            return {}
        
        self.logger.info(f"Starting batch processing of {len(xml_records)} records")
        
        # Create parallel coordinator
        # Note: batch_size here is for database operations, not processing batches
        coordinator = ParallelCoordinator(
            connection_string=self.connection_string,
            mapping_contract_path=self.mapping_contract_path,
            num_workers=self.workers,
            batch_size=1000  # Database batch size (keep at 1000 for performance)
        )
        
        # Process batch
        start_time = time.time()
        processing_result = coordinator.process_xml_batch(xml_records)
        end_time = time.time()
        
        # Extract failed app details from individual results
        individual_results = processing_result.performance_metrics.get('individual_results', [])
        failed_apps = []
        
        for result in individual_results:
            if not result.get('success', True):
                failed_app = {
                    'app_id': result.get('app_id'),
                    'error_stage': result.get('error_stage', 'unknown'),
                    'error_message': result.get('error_message', 'No error message available'),
                    'processing_time': result.get('processing_time', 0)
                }
                failed_apps.append(failed_app)
        
        # Categorize failures by stage
        failure_summary = {
            'parsing_failures': len([f for f in failed_apps if f['error_stage'] == 'parsing']),
            'mapping_failures': len([f for f in failed_apps if f['error_stage'] == 'mapping']),
            'insertion_failures': len([f for f in failed_apps if f['error_stage'] == 'insertion']),
            'constraint_violations': len([f for f in failed_apps if f['error_stage'] == 'constraint_violation']),
            'database_errors': len([f for f in failed_apps if f['error_stage'] == 'database_error']),
            'system_errors': len([f for f in failed_apps if f['error_stage'] == 'system_error']),
            'unknown_failures': len([f for f in failed_apps if f['error_stage'] == 'unknown'])
        }
        
        # Calculate metrics
        metrics = {
            'session_id': self.session_id,
            'batch_start_time': datetime.fromtimestamp(start_time).isoformat(),
            'batch_end_time': datetime.fromtimestamp(end_time).isoformat(),
            'total_processing_time': end_time - start_time,
            'records_processed': processing_result.records_processed,
            'records_successful': processing_result.records_successful,
            'records_failed': processing_result.records_failed,
            'success_rate': processing_result.success_rate,
            'records_per_minute': processing_result.performance_metrics.get('records_per_minute', 0),
            'records_per_second': processing_result.performance_metrics.get('records_per_second', 0),
            'total_records_inserted': processing_result.performance_metrics.get('total_records_inserted', 0),
            'parallel_efficiency': processing_result.performance_metrics.get('parallel_efficiency', 0),
            'worker_count': self.workers,
            'server': self.server,
            'database': self.database,
            'failed_apps': failed_apps,
            'failure_summary': failure_summary
        }
        
        # Log summary
        self.logger.info("="*60)
        self.logger.info("BATCH PROCESSING COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Applications Processed: {metrics['records_processed']}")
        self.logger.info(f"Success Rate: {metrics['success_rate']:.1f}%")
        self.logger.info(f"Throughput: {metrics['records_per_minute']:.1f} applications/minute")
        self.logger.info(f"Total Time: {metrics['total_processing_time']:.2f} seconds")
        self.logger.info(f"Database Records Inserted: {metrics['total_records_inserted']}")
        self.logger.info(f"Parallel Efficiency: {metrics['parallel_efficiency']*100:.1f}%")
        
        # Log failure details if any
        if metrics['records_failed'] > 0:
            self.logger.warning(f"Failed Applications: {metrics['records_failed']}")
            
            # Log failure breakdown
            failure_summary = metrics['failure_summary']
            if failure_summary['parsing_failures'] > 0:
                self.logger.warning(f"  Parsing Failures: {failure_summary['parsing_failures']} (XML structure/format issues)")
            if failure_summary['mapping_failures'] > 0:
                self.logger.warning(f"  Mapping Failures: {failure_summary['mapping_failures']} (Data transformation issues)")
            if failure_summary['insertion_failures'] > 0:
                self.logger.warning(f"  Insertion Failures: {failure_summary['insertion_failures']} (General database insertion issues)")
            if failure_summary['constraint_violations'] > 0:
                self.logger.warning(f"  Constraint Violations: {failure_summary['constraint_violations']} (Primary key, foreign key, null constraints)")
            if failure_summary['database_errors'] > 0:
                self.logger.warning(f"  Database Errors: {failure_summary['database_errors']} (Connection, timeout, SQL errors)")
            if failure_summary['system_errors'] > 0:
                self.logger.warning(f"  System Errors: {failure_summary['system_errors']} (Unexpected system issues)")
            if failure_summary['unknown_failures'] > 0:
                self.logger.warning(f"  Unknown Failures: {failure_summary['unknown_failures']} (Unclassified errors)")
            
            # Log failed app_ids (keep it concise)
            failed_app_ids = [str(f['app_id']) for f in metrics['failed_apps']]
            if len(failed_app_ids) <= 10:
                self.logger.warning(f"  Failed App IDs: {', '.join(failed_app_ids)}")
            else:
                self.logger.warning(f"  Failed App IDs: {', '.join(failed_app_ids[:10])} ... and {len(failed_app_ids)-10} more")
            
            # Log detailed errors at DEBUG level
            for failed_app in metrics['failed_apps']:
                self.logger.debug(f"  App {failed_app['app_id']}: {failed_app['error_stage']} - {failed_app['error_message']}")
        else:
            self.logger.info("✅ All records processed successfully!")
        
        # Save metrics to file
        self._save_metrics(metrics)
        
        return metrics
    
    def _save_metrics(self, metrics: dict):
        """Save performance metrics to JSON file."""
        metrics_dir = Path("metrics")
        metrics_dir.mkdir(exist_ok=True)
        
        metrics_file = metrics_dir / f"metrics_{self.session_id}.json"
        
        try:
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            self.logger.info(f"Metrics saved to: {metrics_file}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")
    
    def run_full_processing(self, limit: Optional[int] = None):
        """Run full processing with batching and monitoring."""
        self.logger.info("Starting full processing run")
        
        # Test connection first
        if not self.test_connection():
            raise RuntimeError("Database connection test failed")
        
        # Get total record count for progress tracking
        try:
            migration_engine = MigrationEngine(self.connection_string)
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM app_xml WHERE xml IS NOT NULL AND DATALENGTH(xml) > 100")
                total_records = cursor.fetchone()[0]
                
                if limit:
                    total_records = min(total_records, limit)
                
                self.logger.info(f"Total records to process: {total_records}")
        except Exception as e:
            self.logger.error(f"Failed to get record count: {e}")
            total_records = 0
        
        # Process in batches
        offset = 0
        total_processed = 0
        total_successful = 0
        total_failed = 0
        all_failed_apps = []
        overall_failure_summary = {
            'parsing_failures': 0,
            'mapping_failures': 0,
            'insertion_failures': 0,
            'constraint_violations': 0,
            'database_errors': 0,
            'system_errors': 0,
            'unknown_failures': 0
        }
        overall_start = time.time()
        
        while True:
            # Get next batch
            batch_records = self.get_xml_records(limit=self.batch_size, offset=offset)
            
            if not batch_records:
                break
            
            if limit and total_processed + len(batch_records) > limit:
                # Trim batch to respect limit
                batch_records = batch_records[:limit - total_processed]
            
            # Process batch
            self.logger.info(f"Processing batch {offset//self.batch_size + 1}: records {offset+1}-{offset+len(batch_records)}")
            metrics = self.process_batch(batch_records)
            
            # Update totals
            total_processed += metrics.get('records_processed', 0)
            total_successful += metrics.get('records_successful', 0)
            total_failed += metrics.get('records_failed', 0)
            
            # Accumulate failed apps and failure summary
            all_failed_apps.extend(metrics.get('failed_apps', []))
            batch_failure_summary = metrics.get('failure_summary', {})
            for key in overall_failure_summary:
                overall_failure_summary[key] += batch_failure_summary.get(key, 0)
            
            offset += len(batch_records)
            
            # Check if we've reached the limit
            if limit and total_processed >= limit:
                break
        
        # Final summary
        overall_time = time.time() - overall_start
        overall_rate = total_processed / (overall_time / 60) if overall_time > 0 else 0
        overall_success_rate = (total_successful/total_processed*100) if total_processed > 0 else 0
        
        self.logger.info("="*80)
        self.logger.info("FULL PROCESSING COMPLETE")
        self.logger.info("="*80)
        self.logger.info(f"Total Applications Processed: {total_processed}")
        self.logger.info(f"Total Successful: {total_successful}")
        self.logger.info(f"Total Failed: {total_failed}")
        self.logger.info(f"Overall Success Rate: {overall_success_rate:.1f}%")
        self.logger.info(f"Overall Time: {overall_time/60:.1f} minutes")
        self.logger.info(f"Overall Rate: {overall_rate:.1f} applications/minute")
        
        # Log overall failure summary if there were failures
        if total_failed > 0:
            self.logger.warning("="*60)
            self.logger.warning("FAILURE ANALYSIS")
            self.logger.warning("="*60)
            
            if overall_failure_summary['parsing_failures'] > 0:
                self.logger.warning(f"Parsing Failures: {overall_failure_summary['parsing_failures']} (XML structure/format issues)")
            if overall_failure_summary['mapping_failures'] > 0:
                self.logger.warning(f"Mapping Failures: {overall_failure_summary['mapping_failures']} (Data transformation issues)")
            if overall_failure_summary['insertion_failures'] > 0:
                self.logger.warning(f"Insertion Failures: {overall_failure_summary['insertion_failures']} (General database insertion issues)")
            if overall_failure_summary['constraint_violations'] > 0:
                self.logger.warning(f"Constraint Violations: {overall_failure_summary['constraint_violations']} (Primary key, foreign key, null constraints)")
            if overall_failure_summary['database_errors'] > 0:
                self.logger.warning(f"Database Errors: {overall_failure_summary['database_errors']} (Connection, timeout, SQL errors)")
            if overall_failure_summary['system_errors'] > 0:
                self.logger.warning(f"System Errors: {overall_failure_summary['system_errors']} (Unexpected system issues)")
            if overall_failure_summary['unknown_failures'] > 0:
                self.logger.warning(f"Unknown Failures: {overall_failure_summary['unknown_failures']} (Unclassified errors)")
            
            # Log sample of failed app_ids for investigation
            failed_app_ids = [str(f['app_id']) for f in all_failed_apps]
            unique_failed_ids = list(dict.fromkeys(failed_app_ids))  # Remove duplicates while preserving order
            
            if len(unique_failed_ids) <= 20:
                self.logger.warning(f"Failed App IDs: {', '.join(unique_failed_ids)}")
            else:
                self.logger.warning(f"Failed App IDs (first 20): {', '.join(unique_failed_ids[:20])}")
                self.logger.warning(f"Total unique failed apps: {len(unique_failed_ids)}")
        
        return {
            'total_processed': total_processed,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_success_rate': overall_success_rate,
            'overall_time_minutes': overall_time / 60,
            'overall_rate_per_minute': overall_rate,
            'failed_apps': all_failed_apps,
            'failure_summary': overall_failure_summary
        }


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Production XML Processing")
    
    # Required arguments
    parser.add_argument("--server", required=True, help="SQL Server instance (e.g., 'localhost\\SQLEXPRESS')")
    parser.add_argument("--database", required=True, help="Database name")
    
    # Optional arguments
    parser.add_argument("--username", help="SQL Server username (uses Windows auth if not provided)")
    parser.add_argument("--password", help="SQL Server password")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers (default: 4)")
    parser.add_argument("--batch-size", type=int, default=100, help="Records per batch (default: 100)")
    parser.add_argument("--limit", type=int, help="Maximum records to process (default: all)")
    parser.add_argument("--log-level", default="INFO", choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
                       help="Logging level (default: INFO)")
    
    args = parser.parse_args()
    
    try:
        # Create processor
        processor = ProductionProcessor(
            server=args.server,
            database=args.database,
            username=args.username,
            password=args.password,
            workers=args.workers,
            batch_size=args.batch_size,
            log_level=args.log_level
        )
        
        # Run processing
        results = processor.run_full_processing(limit=args.limit)
        
        print("\n" + "="*60)
        print("PRODUCTION PROCESSING COMPLETED SUCCESSFULLY")
        print("="*60)
        print(f"Check logs/ and metrics/ directories for detailed results")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        return 1
    except Exception as e:
        print(f"\nProcessing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)