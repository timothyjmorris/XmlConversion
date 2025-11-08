"""
Centralized configuration defaults for XML processing operations.

This module defines operational configuration constants used throughout the system.
These are processing infrastructure settings (not domain-specific), shared across all
migrations and ETL runs. CLI arguments can override these defaults at runtime.

Single Source of Truth: Change these values once; all modules automatically use updated defaults.
"""


class ProcessingDefaults:
    """
    Centralized operational configuration for XML processing.
    
    All values are defaults that can be overridden via CLI arguments:
    - python production_processor.py --batch-size 1000 --workers 8
    - python production_processor.py --log-level DEBUG
    
    These settings apply consistently across all migrations unless explicitly overridden.
    """
    
    # Batch processing
    BATCH_SIZE = 1000  # Records per batch for parallel workers
    CHUNK_SIZE = 10000  # XML chunk size for memory-efficient parsing
    
    # Parallelization
    WORKERS = 4  # Number of parallel worker processes
    
    # Processing limits
    LIMIT = 10000  # Maximum applications to process (0 = unlimited)
    
    # Database connection pooling (pyodbc ODBC DSN pooling)
    ENABLE_POOLING = False  # Enable connection pooling (requires min/max pool sizes)
    CONNECTION_POOL_MIN = 4  # Minimum connections to maintain in pool
    CONNECTION_POOL_MAX = 20  # Maximum connections to allow in pool
    CONNECTION_TIMEOUT = 30  # Connection timeout in seconds
    MARS_ENABLED = True  # Enable Multiple Active Result Sets (MARS)
    
    # Logging
    LOG_LEVEL = "WARNING"  # Default logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG)
    
    @classmethod
    def to_dict(cls) -> dict:
        """
        Export all defaults as a dictionary.
        
        Useful for logging configuration or passing to templates.
        
        Returns:
            Dictionary of all ProcessingDefaults class attributes.
        """
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }
    
    @classmethod
    def log_summary(cls, logger=None):
        """
        Log a summary of all operational defaults.
        
        Args:
            logger: Optional logger instance. If None, prints to stdout.
        """
        config_dict = cls.to_dict()
        summary = "\n".join([f"  {key}: {value}" for key, value in sorted(config_dict.items())])
        message = f"Processing Configuration Defaults:\n{summary}"
        
        if logger:
            logger.info(message)
        else:
            print(message)
