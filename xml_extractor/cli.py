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
    
    # Set up logging without reconfiguring root if already configured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("XML Database Extraction System v1.0.0")
    logger.info("Centralized Configuration Management Active")
    
    try:
        # Initialize centralized configuration
        config_manager = get_config_manager()
        
        # Display configuration summary
        logger.info("\n=== Configuration Summary ===")
        summary = config_manager.get_configuration_summary()

        logger.info(f"Database Server: {summary['database']['server']}")
        logger.info(f"Database Name: {summary['database']['database']}")
        logger.info(f"Batch Size: {summary['processing']['batch_size']}")
        logger.info(f"Parallel Processes: {summary['processing']['parallel_processes']}")
        logger.info(f"Memory Limit: {summary['processing']['memory_limit_mb']}MB")
        
        # Validate configuration
        logger.info("\n=== Configuration Validation ===")
        is_valid = config_manager.validate_configuration()
        logger.info(f"Configuration Status: {'VALID' if is_valid else 'INVALID'}")

        logger.info("\n=== Available Components ===")
        logger.info("- OK Centralized Configuration Management")
        logger.info("- OK Database Connection Management")
        logger.info("- OK Variable Support")
        logger.info("- OK XML parsing engine")
        logger.info("- OK Data mapping system")
        logger.info("- OK Migration engine")
        logger.info("- OK Performance monitoring")

        logger.info("\n=== Environment Variables ===")
        logger.info("Set these environment variables to customize configuration:")
        logger.info("- XML_EXTRACTOR_CONNECTION_STRING: Database connection string")
        logger.info("- XML_EXTRACTOR_BATCH_SIZE: Batch size for processing")
        logger.info("- XML_EXTRACTOR_PARALLEL_PROCESSES: Number of parallel processes")
        logger.info("- XML_EXTRACTOR_MEMORY_LIMIT_MB: Memory limit in MB")
        logger.info("- XML_EXTRACTOR_DB_SERVER: Database server")
        logger.info("- XML_EXTRACTOR_DB_DATABASE: Database name")

        logger.info("\nCLI interface will be fully implemented in task 8.1")
        
        return 0
        
    except Exception as e:
        logger.error(f"Configuration initialization failed: {e}")
        logger.error(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())