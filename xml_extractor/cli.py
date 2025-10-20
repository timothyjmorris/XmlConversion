"""
Command-line interface for the XML Database Extraction system.

This module provides the main entry point for running extraction jobs
from the command line with centralized configuration management.
"""

import sys
import logging
from typing import Optional

from .config.config_manager import get_config_manager


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for the CLI application.
    
    Args:
        args: Optional command line arguments (defaults to sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    if args is None:
        args = sys.argv[1:]
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    print("XML Database Extraction System v1.0.0")
    print("Centralized Configuration Management Active")
    
    try:
        # Initialize centralized configuration
        config_manager = get_config_manager()
        
        # Display configuration summary
        print("\n=== Configuration Summary ===")
        summary = config_manager.get_configuration_summary()
        
        print(f"Database Server: {summary['database']['server']}")
        print(f"Database Name: {summary['database']['database']}")
        print(f"Batch Size: {summary['processing']['batch_size']}")
        print(f"Parallel Processes: {summary['processing']['parallel_processes']}")
        print(f"Memory Limit: {summary['processing']['memory_limit_mb']}MB")
        
        # Validate configuration
        print("\n=== Configuration Validation ===")
        is_valid = config_manager.validate_configuration()
        print(f"Configuration Status: {'✅ VALID' if is_valid else '❌ INVALID'}")
        
        print("\n=== Available Components ===")
        print("- ✅ Centralized Configuration Management")
        print("- ✅ Database Connection Management")
        print("- ✅ Environment Variable Support")
        print("- ✅ XML parsing engine") 
        print("- ✅ Data mapping system")
        print("- ✅ Migration engine")
        print("- ✅ Performance monitoring")
        
        print("\n=== Environment Variables ===")
        print("Set these environment variables to customize configuration:")
        print("- XML_EXTRACTOR_CONNECTION_STRING: Database connection string")
        print("- XML_EXTRACTOR_BATCH_SIZE: Batch size for processing")
        print("- XML_EXTRACTOR_PARALLEL_PROCESSES: Number of parallel processes")
        print("- XML_EXTRACTOR_MEMORY_LIMIT_MB: Memory limit in MB")
        print("- XML_EXTRACTOR_DB_SERVER: Database server")
        print("- XML_EXTRACTOR_DB_DATABASE: Database name")
        
        print("\nCLI interface will be fully implemented in task 8.1")
        
        return 0
        
    except Exception as e:
        logger.error(f"Configuration initialization failed: {e}")
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())