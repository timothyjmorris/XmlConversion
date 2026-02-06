"""
Find Unprocessed Applications

Identifies apps that exist in staging table but are NOT in processing_log.
These are apps that were never attempted (not processed, not failed, not logged).

USAGE:
    # Find all unprocessed apps for migration schema
    python diagnostics/find_unprocessed_apps.py --server localhost\\SQLEXPRESS --database XmlConversionDB
    
    # With app_id range filter
    python diagnostics/find_unprocessed_apps.py --server localhost\\SQLEXPRESS --database XmlConversionDB --app-id-start 1 --app-id-end 50000
    
    # Export to file
    python diagnostics/find_unprocessed_apps.py --server localhost\\SQLEXPRESS --database XmlConversionDB --output unprocessed_apps.txt
"""

import argparse
import sys
import pyodbc
from pathlib import Path
from typing import List, Optional


def get_unprocessed_apps(connection_string: str, target_schema: str = 'migration',
                         app_id_start: Optional[int] = None, 
                         app_id_end: Optional[int] = None) -> List[int]:
    """
    Query database for apps in staging table but not in processing_log.
    
    Args:
        connection_string: Database connection string
        target_schema: Target schema (default: migration)
        app_id_start: Optional starting app_id filter
        app_id_end: Optional ending app_id filter
        
    Returns:
        List of app_ids not in processing_log
    """
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    # Build WHERE clause for app_id range
    where_conditions = ["ax.app_XML IS NOT NULL"]
    if app_id_start is not None:
        where_conditions.append(f"ax.app_id >= {app_id_start}")
    if app_id_end is not None:
        where_conditions.append(f"ax.app_id <= {app_id_end}")
    
    where_clause = " AND ".join(where_conditions)
    
    query = f"""
        SELECT ax.app_id
        FROM [{target_schema}].[app_xml_staging] ax
        WHERE {where_clause}
        AND NOT EXISTS (
            SELECT 1 
            FROM [{target_schema}].[processing_log] pl 
            WHERE pl.app_id = ax.app_id
        )
        ORDER BY ax.app_id
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    app_ids = [row[0] for row in rows]
    
    conn.close()
    return app_ids


def build_connection_string(server: str, database: str, username: Optional[str] = None, 
                            password: Optional[str] = None) -> str:
    """Build SQL Server connection string."""
    server_name = server.replace('\\\\', '\\')
    
    if username and password:
        return (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_name};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate=yes;"
                f"Encrypt=no;")
    else:
        return (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server_name};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
                f"Encrypt=no;")


def format_report(app_ids: List[int], target_schema: str, app_id_start: Optional[int], 
                  app_id_end: Optional[int]) -> str:
    """Format unprocessed apps report."""
    lines = []
    lines.append("=" * 80)
    lines.append(" UNPROCESSED APPLICATIONS REPORT")
    lines.append("=" * 80)
    lines.append(f" Schema: {target_schema}")
    
    if app_id_start is not None or app_id_end is not None:
        range_str = f"{app_id_start or 'start'} - {app_id_end or 'end'}"
        lines.append(f" Range: {range_str}")
    
    lines.append(f" Total Unprocessed: {len(app_ids)}")
    lines.append("")
    
    if not app_ids:
        lines.append(" ✓ All apps in staging have been processed or logged")
    else:
        lines.append(" Unprocessed App IDs:")
        lines.append(" " + "-" * 78)
        
        # Show first 100, 10 per line
        for i, app_id in enumerate(app_ids[:100], 1):
            if i % 10 == 1:
                # Start new line
                line_apps = [f"{app_id:8d}"]
            else:
                line_apps.append(f"{app_id:8d}")
            
            if i % 10 == 0 or i == len(app_ids[:100]):
                # End of line - append to lines
                lines.append("   " + " ".join(line_apps))
        
        if len(app_ids) > 100:
            lines.append("")
            lines.append(f"   ... and {len(app_ids) - 100} more")
    
    lines.append("")
    lines.append("=" * 80)
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Find Unprocessed Applications")
    
    parser.add_argument("--server", required=True, 
                       help="SQL Server instance (e.g., 'localhost\\SQLEXPRESS')")
    parser.add_argument("--database", required=True, 
                       help="Database name")
    parser.add_argument("--username", 
                       help="SQL Server username (uses Windows auth if not provided)")
    parser.add_argument("--password", 
                       help="SQL Server password")
    parser.add_argument("--target-schema", default="migration",
                       help="Target schema (default: migration)")
    parser.add_argument("--app-id-start", type=int,
                       help="Starting app_id filter (optional)")
    parser.add_argument("--app-id-end", type=int,
                       help="Ending app_id filter (optional)")
    parser.add_argument("--output", type=Path,
                       help="Output file (prints to console if not specified)")
    
    args = parser.parse_args()
    
    try:
        # Build connection string
        conn_str = build_connection_string(args.server, args.database, 
                                           args.username, args.password)
        
        # Query unprocessed apps
        print("Querying database...")
        app_ids = get_unprocessed_apps(conn_str, args.target_schema, 
                                      args.app_id_start, args.app_id_end)
        
        # Format report
        report = format_report(app_ids, args.target_schema, 
                              args.app_id_start, args.app_id_end)
        
        # Output
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report)
            print(f"Report saved to: {args.output}")
            print(f"Total unprocessed apps: {len(app_ids)}")
        else:
            print(report)
        
        return 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
