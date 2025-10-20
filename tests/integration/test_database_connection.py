#!/usr/bin/env python3
"""
Database connection test for SQL Server environment validation.
This script tests the database connection and validates the environment is ready.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc not installed. Run: pip install pyodbc")
    sys.exit(1)


class DatabaseConnectionTester:
    """Test database connectivity and environment setup."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize with database configuration."""
        self.logger = logging.getLogger(__name__)
        
        if config_path is None:
            # Default to config/database_config.json relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "database_config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.connection = None
    
    def _load_config(self) -> Dict:
        """Load database configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Database config file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def get_available_drivers(self) -> List[str]:
        """Get list of available ODBC drivers."""
        try:
            return pyodbc.drivers()
        except Exception as e:
            print(f"Warning: Could not get ODBC drivers: {e}")
            return []
    
    def build_connection_string(self, driver: Optional[str] = None) -> str:
        """Build connection string with specified or default driver."""
        db_config = self.config["database"].copy()
        
        if driver:
            db_config["driver"] = driver
        
        # Choose template based on authentication method
        if db_config.get("trusted_connection", False):
            template = self.config["connection_string_template_windows_auth"]
        else:
            template = self.config["connection_string_template_sql_auth"]
        
        return template.format(**db_config)
    
    def test_connection(self, driver: Optional[str] = None) -> Tuple[bool, str]:
        """Test database connection with specified driver."""
        try:
            conn_str = self.build_connection_string(driver)
            self.logger.info(f"Testing connection with driver: {driver or self.config['database']['driver']}")
            self.logger.debug(f"Connection string: {conn_str}")
            
            self.connection = pyodbc.connect(conn_str)
            return True, "Connection successful"
            
        except pyodbc.Error as e:
            return False, f"Database error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def run_test_queries(self) -> Dict[str, any]:
        """Run test queries to validate database functionality."""
        if not self.connection:
            raise RuntimeError("No active database connection")
        
        results = {}
        test_queries = self.config["test_queries"]
        
        try:
            cursor = self.connection.cursor()
            
            for test_name, query in test_queries.items():
                try:
                    print(f"Running {test_name}: {query}")
                    cursor.execute(query)
                    result = cursor.fetchone()
                    results[test_name] = result[0] if result else None
                    print(f"  Result: {results[test_name]}")
                except Exception as e:
                    results[test_name] = f"ERROR: {e}"
                    print(f"  Error: {e}")
            
            cursor.close()
            
        except Exception as e:
            results["query_error"] = str(e)
        
        return results
    
    def test_table_creation(self) -> Tuple[bool, str]:
        """Test ability to create and drop a test table."""
        if not self.connection:
            raise RuntimeError("No active database connection")
        
        test_table_name = "xml_extractor_connection_test"
        
        try:
            cursor = self.connection.cursor()
            
            # Create test table
            create_sql = f"""
            CREATE TABLE {test_table_name} (
                id int IDENTITY(1,1) PRIMARY KEY,
                test_column varchar(50),
                created_at datetime DEFAULT GETDATE()
            )
            """
            print(f"Creating test table: {test_table_name}")
            cursor.execute(create_sql)
            
            # Insert test data
            insert_sql = f"INSERT INTO {test_table_name} (test_column) VALUES (?)"
            cursor.execute(insert_sql, "connection_test")
            
            # Query test data
            select_sql = f"SELECT COUNT(*) FROM {test_table_name}"
            cursor.execute(select_sql)
            count = cursor.fetchone()[0]
            
            # Drop test table
            drop_sql = f"DROP TABLE {test_table_name}"
            cursor.execute(drop_sql)
            
            cursor.close()
            self.connection.commit()
            
            return True, f"Table operations successful (inserted {count} row)"
            
        except Exception as e:
            # Try to clean up test table if it exists
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {test_table_name}")
                cursor.close()
                self.connection.commit()
            except:
                pass
            
            return False, f"Table operation failed: {e}"
    
    def close_connection(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def run_full_test(self) -> bool:
        """Run complete database environment test."""
        print("=" * 60)
        print("SQL Server Environment Test")
        print("=" * 60)
        
        # Check available drivers
        print("\n1. Checking available ODBC drivers...")
        available_drivers = self.get_available_drivers()
        print(f"Available drivers: {available_drivers}")
        
        # Find best driver
        preferred_drivers = self.config.get("alternative_drivers", [])
        best_driver = None
        
        for driver in preferred_drivers:
            if driver in available_drivers:
                best_driver = driver
                break
        
        if not best_driver:
            print("WARNING: No preferred drivers found, using default")
            best_driver = self.config["database"]["driver"]
        
        print(f"Selected driver: {best_driver}")
        
        # Test connection with multiple server configurations
        print(f"\n2. Testing database connection...")
        
        # Try different server configurations
        server_configs = [
            self.config["database"]["server"],  # Original config
            "localhost\\SQLEXPRESS",           # Common SQL Express instance
            "(localdb)\\MSSQLLocalDB",         # LocalDB
            "localhost,1433",                  # Explicit port
            "127.0.0.1",                      # IP address
            "127.0.0.1,1433"                  # IP with port
        ]
        
        success = False
        working_server = None
        
        for server in server_configs:
            print(f"\nTrying server: {server}")
            
            # Temporarily update config
            original_server = self.config["database"]["server"]
            self.config["database"]["server"] = server
            
            test_success, message = self.test_connection(best_driver)
            
            if test_success:
                print(f"✅ {message}")
                success = True
                working_server = server
                break
            else:
                print(f"❌ Failed: {message}")
            
            # Restore original server
            self.config["database"]["server"] = original_server
        
        if not success:
            print(f"\n❌ Could not connect to any server configuration")
            print(f"Tried: {', '.join(server_configs)}")
            return False
        
        # Update config with working server
        self.config["database"]["server"] = working_server
        print(f"\n✅ Using working server configuration: {working_server}")
        
        print(f"✅ {message}")
        
        # Run test queries
        print(f"\n3. Running test queries...")
        try:
            query_results = self.run_test_queries()
            
            all_passed = True
            for test_name, result in query_results.items():
                if isinstance(result, str) and result.startswith("ERROR"):
                    print(f"❌ {test_name}: {result}")
                    all_passed = False
                else:
                    print(f"✅ {test_name}: {result}")
            
            if not all_passed:
                return False
                
        except Exception as e:
            print(f"❌ Query test failed: {e}")
            return False
        
        # Test table operations
        print(f"\n4. Testing table creation/deletion...")
        success, message = self.test_table_creation()
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            return False
        
        print(f"\n" + "=" * 60)
        print("✅ All database tests passed! Environment is ready.")
        print("=" * 60)
        
        return True


def main():
    """Main function to run database connection test."""
    try:
        tester = DatabaseConnectionTester()
        success = tester.run_full_test()
        tester.close_connection()
        
        if success:
            print("\n🎉 Database environment is ready for XML extraction tasks!")
            return 0
        else:
            print("\n❌ Database environment setup needs attention.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())