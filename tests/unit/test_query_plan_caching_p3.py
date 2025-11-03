#!/usr/bin/env python3
"""
Test case for P3 - Query Plan Caching Performance Fix

This test validates that the MigrationEngine properly caches INSERT SQL 
statements to avoid repeated query compilation overhead, implementing 
the P3 performance optimization from CODE_REVIEW_AND_ACTION_PLAN.md.
"""

import pytest
from xml_extractor.database.migration_engine import MigrationEngine


class TestQueryPlanCaching:
    """Test query plan caching performance optimization (P3 fix)."""
    
    def test_query_caching_generates_correct_sql(self):
        """
        Test that cached SQL generation produces correct INSERT statements.
        """
        # Create a MigrationEngine instance
        engine = MigrationEngine()
        
        # Test SQL generation for a simple table
        qualified_table = "[sandbox].[contact_base]"
        columns = ["con_id", "first_name", "last_name"]
        
        sql = engine._get_insert_sql(qualified_table, columns)
        
        # Verify the SQL is correct
        expected_sql = "INSERT INTO [sandbox].[contact_base] ([con_id], [first_name], [last_name]) VALUES (?, ?, ?)"
        assert sql == expected_sql
    
    def test_query_caching_reuses_cached_sql(self):
        """
        Test that identical table/column combinations return cached SQL.
        """
        # Create a MigrationEngine instance  
        engine = MigrationEngine()
        
        qualified_table = "[dbo].[contact_address]"
        columns = ["con_id", "address_type_enum", "street", "city"]
        
        # First call - generates and caches SQL
        sql1 = engine._get_insert_sql(qualified_table, columns)
        cache_size_after_first = len(engine._query_cache)
        
        # Second call - should use cached SQL
        sql2 = engine._get_insert_sql(qualified_table, columns)
        cache_size_after_second = len(engine._query_cache)
        
        # Verify same SQL returned and cache size unchanged
        assert sql1 == sql2
        assert cache_size_after_first == cache_size_after_second == 1
        assert qualified_table + "::" + ",".join(sorted(columns)) in engine._query_cache
    
    def test_query_caching_handles_column_order_independence(self):
        """
        Test that different column orders result in same cached entry.
        
        This verifies the cache key uses sorted columns for consistency.
        """
        # Create a MigrationEngine instance
        engine = MigrationEngine()
        
        qualified_table = "[test].[table_name]" 
        columns1 = ["col_a", "col_b", "col_c"]
        columns2 = ["col_c", "col_a", "col_b"]  # Different order
        
        # Both calls should use same cache entry
        sql1 = engine._get_insert_sql(qualified_table, columns1)
        sql2 = engine._get_insert_sql(qualified_table, columns2)
        
        # Should have only 1 cache entry
        assert len(engine._query_cache) == 1
        
        # SQL should be identical (both using sorted column order)
        assert sql1 == sql2
        expected_sql = "INSERT INTO [test].[table_name] ([col_a], [col_b], [col_c]) VALUES (?, ?, ?)"
        assert sql1 == expected_sql
    
    def test_query_caching_differentiates_tables_and_columns(self):
        """
        Test that different tables and column sets create separate cache entries.
        """
        # Create a MigrationEngine instance
        engine = MigrationEngine()
        
        # Different table, same columns
        sql1 = engine._get_insert_sql("[dbo].[table1]", ["col1", "col2"])
        sql2 = engine._get_insert_sql("[dbo].[table2]", ["col1", "col2"])
        
        # Same table, different columns  
        sql3 = engine._get_insert_sql("[dbo].[table1]", ["col1", "col3"])
        
        # Should have 3 different cache entries
        assert len(engine._query_cache) == 3
        
        # Each SQL should be different
        assert sql1 != sql2 != sql3
        assert "table1" in sql1 and "table2" in sql2
        assert "col2" in sql1 and "col3" in sql3
    
    def test_cache_performance_benefit_simulation(self):
        """
        Simulate the performance benefit by testing repeated calls.
        
        While we can't measure actual query compilation time, we can 
        verify the caching mechanism works for repeated operations.
        """
        # Create a MigrationEngine instance
        engine = MigrationEngine()
        
        qualified_table = "[production].[app_base]"
        columns = ["app_id", "receive_date", "status_enum"]
        
        # Simulate 100 identical bulk insert operations
        # In production, this would avoid 99 query plan compilations
        for i in range(100):
            sql = engine._get_insert_sql(qualified_table, columns)
            
            # SQL should be consistent every time
            expected = "INSERT INTO [production].[app_base] ([app_id], [receive_date], [status_enum]) VALUES (?, ?, ?)"
            assert sql == expected
        
        # Should still have only 1 cache entry despite 100 calls
        assert len(engine._query_cache) == 1