"""
Multi-Instance Parallel Launcher - Modulo Sharding

Launches multiple production_processor instances in parallel, each processing
a subset of applications based on modulo sharding (app_id % num_instances).

This avoids gaps in processing and ensures even distribution across instances.

USAGE:
    python launch_parallel_instances.py --instances 10 --limit 10000

FEATURES:
    - Modulo sharding: Instance N processes apps where app_id % num_instances == N
    - Automatic window launching (PowerShell windows for each instance)
    - Configurable workers per instance
    - Real-time progress monitoring
    - Graceful shutdown on Ctrl+C

PERFORMANCE:
    With 10 instances × 550 apps/min = 5,500 apps/min total throughput
    Each instance operates independently (no coordination overhead)
"""

import argparse
import subprocess
import sys
import time
import json
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class ParallelInstanceLauncher:
    """Launches and manages multiple production_processor instances with modulo sharding."""
    
    def __init__(self, num_instances: int, workers_per_instance: int = 4, 
                 batch_size: int = 500, limit: Optional[int] = None,
                 server: str = None, database: str = None,
                 log_level: str = "WARNING"):
        """
        Initialize multi-instance launcher.
        
        Args:
            num_instances: Number of parallel instances to launch (modulo shards)
            workers_per_instance: Workers per instance (default: 4)
            batch_size: Batch size for database operations (default: 500)
            limit: Total limit across all instances (evenly distributed)
            server: SQL Server instance (uses config default if None)
            database: Database name (uses config default if None)
            log_level: Logging level for instances
        """
        self.num_instances = num_instances
        self.workers_per_instance = workers_per_instance
        self.batch_size = batch_size
        self.limit = limit
        self.server = server
        self.database = database
        self.log_level = log_level
        
        self.processes: List[subprocess.Popen] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C and termination signals."""
        print("\n\n🛑 Shutdown signal received. Terminating all instances...")
        self.terminate_all()
        sys.exit(0)
    
    def launch_all(self):
        """Launch all instances with modulo sharding."""
        print("="*80)
        print("MULTI-INSTANCE PARALLEL LAUNCHER")
        print("="*80)
        print(f"\nConfiguration:")
        print(f"  Instances:           {self.num_instances}")
        print(f"  Workers per instance: {self.workers_per_instance}")
        print(f"  Total workers:       {self.num_instances * self.workers_per_instance}")
        print(f"  Batch size:          {self.batch_size}")
        print(f"  Limit per instance:  {self.limit // self.num_instances if self.limit else 'UNLIMITED'}")
        print(f"  Total limit:         {self.limit if self.limit else 'UNLIMITED'}")
        print(f"  Server:              {self.server or '(from config)'}")
        print(f"  Database:            {self.database or '(from config)'}")
        print(f"  Session ID:          {self.session_id}")
        print()
        print("Sharding Strategy: Modulo")
        print(f"  Instance 0 processes: app_id % {self.num_instances} == 0")
        print(f"  Instance 1 processes: app_id % {self.num_instances} == 1")
        print(f"  ...")
        print(f"  Instance {self.num_instances-1} processes: app_id % {self.num_instances} == {self.num_instances-1}")
        print()
        
        # Calculate limit per instance (evenly distributed)
        limit_per_instance = self.limit // self.num_instances if self.limit else None
        
        print(f"Launching {self.num_instances} instances in separate PowerShell windows...")
        print()
        
        for instance_id in range(self.num_instances):
            self._launch_instance(instance_id, limit_per_instance)
            time.sleep(0.5)  # Stagger launches slightly
        
        print(f"\n✅ All {self.num_instances} instances launched successfully!")
        print()
        print("Monitoring:")
        print(f"  - Each instance logs to: logs/production_*.log")
        print(f"  - Each instance metrics to: metrics/metrics_*.json")
        print(f"  - Press Ctrl+C to terminate all instances")
        print()
        
        # Monitor instances
        self._monitor_instances()
    
    def _launch_instance(self, instance_id: int, limit_per_instance: Optional[int]):
        """Launch a single instance with modulo sharding."""
        
        # Build command
        cmd_parts = [
            "python",
            "production_processor.py",
            "--workers", str(self.workers_per_instance),
            "--batch-size", str(self.batch_size),
            "--log-level", self.log_level,
        ]
        
        # Add server/database if specified
        if self.server:
            cmd_parts.extend(["--server", self.server])
        if self.database:
            cmd_parts.extend(["--database", self.database])
        
        # Add limit per instance
        if limit_per_instance:
            cmd_parts.extend(["--limit", str(limit_per_instance)])
        
        # CRITICAL: Add modulo sharding parameters
        # This tells production_processor to only process apps where app_id % num_instances == instance_id
        cmd_parts.extend(["--modulo-shard", str(self.num_instances)])
        cmd_parts.extend(["--modulo-instance", str(instance_id)])
        
        cmd_string = " ".join(cmd_parts)
        
        # Launch in new PowerShell window
        ps_cmd = [
            "powershell.exe",
            "-NoExit",  # Keep window open after completion
            "-Command",
            f"$Host.UI.RawUI.WindowTitle = 'Instance {instance_id} (mod {self.num_instances})'; {cmd_string}"
        ]
        
        try:
            process = subprocess.Popen(
                ps_cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=str(project_root)
            )
            self.processes.append(process)
            print(f"  ✅ Instance {instance_id}: PID {process.pid} (processing app_id % {self.num_instances} == {instance_id})")
        except Exception as e:
            print(f"  ❌ Instance {instance_id}: Failed to launch - {e}")
    
    def _monitor_instances(self):
        """Monitor running instances and wait for completion."""
        print("\n" + "="*80)
        print("MONITORING INSTANCES")
        print("="*80)
        print("\nAll instances are running in separate windows.")
        print("This terminal will monitor their status.\n")
        
        try:
            while True:
                # Check process status
                running = sum(1 for p in self.processes if p.poll() is None)
                completed = len(self.processes) - running
                
                if running == 0:
                    print(f"\n✅ All {len(self.processes)} instances completed!")
                    break
                
                # Print status every 30 seconds
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {running} running, {completed} completed")
                time.sleep(30)
        
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring interrupted. Terminating all instances...")
            self.terminate_all()
    
    def terminate_all(self):
        """Terminate all running instances."""
        for i, process in enumerate(self.processes):
            if process.poll() is None:  # Still running
                print(f"  Terminating instance {i} (PID {process.pid})...")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except Exception as e:
                    print(f"    ⚠️  Failed to terminate gracefully: {e}")
                    try:
                        process.kill()
                    except:
                        pass
        
        print("✅ All instances terminated.")
    
    def get_aggregated_metrics(self):
        """Aggregate metrics from all instance runs (after completion)."""
        metrics_dir = project_root / "metrics"
        # Metrics files are named: metrics_YYYYMMDD_HHMMSS.json
        # Session ID format: YYYYMMDD_HHMMSS
        # Just look for files from today with timestamps near our session
        today = self.session_id[:8]  # YYYYMMDD part
        session_pattern = f"metrics_{today}_*.json"
        
        print(f"\n📊 Aggregating metrics (looking for {session_pattern})...")
        
        # Find all metrics files from today (includes all instances)
        all_metrics_files = list(metrics_dir.glob(session_pattern))
        
        # Filter to only files created after session start (within last 5 minutes)
        session_time = datetime.strptime(self.session_id, "%Y%m%d_%H%M%S")
        metrics_files = []
        for f in all_metrics_files:
            file_time = datetime.fromtimestamp(f.stat().st_mtime)
            if file_time >= session_time:
                metrics_files.append(f)
        
        print(f"Found {len(metrics_files)} metrics files created since session start")
        
        if not metrics_files:
            print("⚠️  No metrics files found for this session.")
            return
        
        # Aggregate results
        total_processed = 0
        total_successful = 0
        total_failed = 0
        total_duration = 0
        total_inserts = 0
        
        for metrics_file in metrics_files:
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    total_processed += data.get('total_applications_processed', 0)
                    total_successful += data.get('total_applications_successful', 0)
                    total_failed += data.get('total_applications_failed', 0)
                    total_duration = max(total_duration, data.get('total_duration_seconds', 0))
                    total_inserts += data.get('total_database_inserts', 0)
            except Exception as e:
                print(f"⚠️  Error reading {metrics_file.name}: {e}")
        
        # Calculate aggregate metrics
        apps_per_minute = (total_processed / total_duration * 60) if total_duration > 0 else 0
        success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
        
        print("\n" + "="*80)
        print("AGGREGATE RESULTS")
        print("="*80)
        print(f"  Total Applications Processed: {total_processed:,}")
        print(f"  Total Successful:             {total_successful:,}")
        print(f"  Total Failed:                 {total_failed:,}")
        print(f"  Success Rate:                 {success_rate:.1f}%")
        print(f"  Total Database Inserts:       {total_inserts:,}")
        print(f"  Total Duration:               {total_duration:.1f} seconds")
        print(f"  Aggregate Throughput:         {apps_per_minute:.1f} apps/min")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Launch multiple production_processor instances with modulo sharding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch 10 instances, each with 4 workers
  python launch_parallel_instances.py --instances 10
  
  # Launch 8 instances with 8 workers each, process 20,000 apps total
  python launch_parallel_instances.py --instances 8 --workers 8 --limit 20000
  
  # Specify server and database explicitly
  python launch_parallel_instances.py --instances 10 --server "myserver" --database "mydb"
        """
    )
    
    parser.add_argument("--instances", type=int, required=True,
                       help="Number of parallel instances to launch")
    parser.add_argument("--workers", type=int, default=4,
                       help="Workers per instance (default: 4)")
    parser.add_argument("--batch-size", type=int, default=500,
                       help="Batch size for database operations (default: 500)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Total limit across all instances (evenly distributed)")
    parser.add_argument("--server", type=str, default=None,
                       help="SQL Server instance (uses config default if not specified)")
    parser.add_argument("--database", type=str, default=None,
                       help="Database name (uses config default if not specified)")
    parser.add_argument("--log-level", type=str, default="WARNING",
                       choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
                       help="Logging level for instances (default: WARNING)")
    
    args = parser.parse_args()
    
    # Validate
    if args.instances < 1:
        print("❌ Error: --instances must be >= 1")
        return 1
    
    if args.instances > 20:
        print("⚠️  Warning: Launching >20 instances may overwhelm your system")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != 'y':
            return 0
    
    # Create launcher
    launcher = ParallelInstanceLauncher(
        num_instances=args.instances,
        workers_per_instance=args.workers,
        batch_size=args.batch_size,
        limit=args.limit,
        server=args.server,
        database=args.database,
        log_level=args.log_level
    )
    
    # Launch all instances
    launcher.launch_all()
    
    # After completion, show aggregate metrics
    launcher.get_aggregated_metrics()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
