"""
Resource Profiler for XML Extraction System
Monitors CPU, memory, disk, and database performance during processing
"""
import psutil
import pyodbc
import time
import json
import threading
from datetime import datetime
from collections import defaultdict
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from xml_extractor.config.config_manager import get_config_manager


class ResourceProfiler:
    """Monitors system resources during processing"""
    
    def __init__(self, interval_seconds=1.0):
        self.interval = interval_seconds
        self.monitoring = False
        self.samples = []
        self.db_connection = None
        self.db_cursor = None
        
    def start_monitoring(self, server, database):
        """Start background monitoring thread"""
        self.monitoring = True
        self.samples = []
        
        # Establish database connection for monitoring
        try:
            conn_str = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
            )
            self.db_connection = pyodbc.connect(conn_str)
            self.db_cursor = self.db_connection.cursor()
            print(f"✓ Connected to {server}/{database} for monitoring")
        except Exception as e:
            print(f"⚠ Could not connect to database for monitoring: {e}")
            self.db_connection = None
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"✓ Resource monitoring started (interval: {self.interval}s)")
        
    def stop_monitoring(self):
        """Stop monitoring and cleanup"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.db_connection:
            self.db_connection.close()
        print(f"✓ Resource monitoring stopped ({len(self.samples)} samples collected)")
        
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            sample = self._collect_sample()
            self.samples.append(sample)
            time.sleep(self.interval)
    
    def _collect_sample(self):
        """Collect single resource sample"""
        timestamp = datetime.now()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=None, percpu=False)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        # Memory metrics
        mem = psutil.virtual_memory()
        
        # Disk I/O metrics
        disk_io = psutil.disk_io_counters()
        
        # Process-specific metrics (current Python process)
        process = psutil.Process()
        process_cpu = process.cpu_percent(interval=None)
        process_mem = process.memory_info()
        process_threads = process.num_threads()
        
        # Database metrics (if connected)
        db_metrics = {}
        if self.db_cursor:
            try:
                # Use queries that don't require VIEW SERVER STATE permission
                
                # Check if database is responding (simple query)
                self.db_cursor.execute("SELECT @@SERVERNAME as server_name, DB_NAME() as database_name")
                row = self.db_cursor.fetchone()
                db_metrics['server_name'] = row[0]
                db_metrics['database_name'] = row[1]
                db_metrics['responsive'] = True
                    
            except Exception as e:
                db_metrics['error'] = str(e)
                db_metrics['responsive'] = False
        
        return {
            'timestamp': timestamp.isoformat(),
            'cpu': {
                'percent_total': cpu_percent,
                'percent_per_core': cpu_per_core,
                'count_logical': cpu_count_logical,
                'count_physical': cpu_count_physical,
            },
            'memory': {
                'total_gb': mem.total / (1024**3),
                'available_gb': mem.available / (1024**3),
                'used_gb': mem.used / (1024**3),
                'percent': mem.percent,
            },
            'disk_io': {
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
            },
            'process': {
                'cpu_percent': process_cpu,
                'memory_mb': process_mem.rss / (1024**2),
                'threads': process_threads,
            },
            'database': db_metrics,
        }
    
    def get_summary(self):
        """Generate summary statistics"""
        if not self.samples:
            return {}
        
        # CPU summary
        cpu_percents = [s['cpu']['percent_total'] for s in self.samples]
        cpu_per_core_max = [max(s['cpu']['percent_per_core']) for s in self.samples]
        
        # Memory summary
        mem_percents = [s['memory']['percent'] for s in self.samples]
        
        # Process summary
        process_cpu = [s['process']['cpu_percent'] for s in self.samples]
        process_mem = [s['process']['memory_mb'] for s in self.samples]
        
        # Database summary
        db_responsive = [s['database'].get('responsive', False) for s in self.samples if s['database']]
        db_responsive_rate = (sum(db_responsive) / len(db_responsive) * 100) if db_responsive else 0
        
        summary = {
            'sample_count': len(self.samples),
            'duration_seconds': (
                datetime.fromisoformat(self.samples[-1]['timestamp']) -
                datetime.fromisoformat(self.samples[0]['timestamp'])
            ).total_seconds(),
            'cpu': {
                'total_avg': sum(cpu_percents) / len(cpu_percents),
                'total_max': max(cpu_percents),
                'total_min': min(cpu_percents),
                'max_core_avg': sum(cpu_per_core_max) / len(cpu_per_core_max),
                'max_core_max': max(cpu_per_core_max),
                'logical_cores': self.samples[0]['cpu']['count_logical'],
                'physical_cores': self.samples[0]['cpu']['count_physical'],
            },
            'memory': {
                'avg_percent': sum(mem_percents) / len(mem_percents),
                'max_percent': max(mem_percents),
                'total_gb': self.samples[0]['memory']['total_gb'],
            },
            'process': {
                'cpu_avg': sum(process_cpu) / len(process_cpu),
                'cpu_max': max(process_cpu),
                'memory_avg_mb': sum(process_mem) / len(process_mem),
                'memory_max_mb': max(process_mem),
                'threads': self.samples[-1]['process']['threads'],
            },
            'database': {
                'responsive_rate': db_responsive_rate,
                'responsive': db_responsive_rate > 95.0,
            }
        }
        
        return summary
    
    def print_summary(self):
        """Print human-readable summary"""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("RESOURCE PROFILER SUMMARY")
        print("="*80)
        
        print(f"\n📊 SAMPLING")
        print(f"  Duration: {summary['duration_seconds']:.1f} seconds")
        print(f"  Samples:  {summary['sample_count']}")
        
        print(f"\n💻 CPU (System-Wide)")
        print(f"  Logical Cores:  {summary['cpu']['logical_cores']}")
        print(f"  Physical Cores: {summary['cpu']['physical_cores']}")
        print(f"  Average Usage:  {summary['cpu']['total_avg']:.1f}%")
        print(f"  Peak Usage:     {summary['cpu']['total_max']:.1f}%")
        print(f"  Minimum Usage:  {summary['cpu']['total_min']:.1f}%")
        print(f"  Hottest Core Avg: {summary['cpu']['max_core_avg']:.1f}%")
        print(f"  Hottest Core Max: {summary['cpu']['max_core_max']:.1f}%")
        
        # CPU assessment
        if summary['cpu']['total_avg'] > 80:
            print(f"  ⚠️  CPU IS SATURATED (avg {summary['cpu']['total_avg']:.1f}%)")
        elif summary['cpu']['total_avg'] > 60:
            print(f"  ⚠️  CPU is heavily utilized (avg {summary['cpu']['total_avg']:.1f}%)")
        else:
            print(f"  ✓  CPU has capacity (avg {summary['cpu']['total_avg']:.1f}%)")
        
        print(f"\n🧠 MEMORY (System-Wide)")
        print(f"  Total:   {summary['memory']['total_gb']:.1f} GB")
        print(f"  Average: {summary['memory']['avg_percent']:.1f}%")
        print(f"  Peak:    {summary['memory']['max_percent']:.1f}%")
        
        if summary['memory']['max_percent'] > 90:
            print(f"  ⚠️  MEMORY IS CONSTRAINED (peak {summary['memory']['max_percent']:.1f}%)")
        elif summary['memory']['max_percent'] > 75:
            print(f"  ⚠️  Memory is heavily utilized (peak {summary['memory']['max_percent']:.1f}%)")
        else:
            print(f"  ✓  Memory has capacity (peak {summary['memory']['max_percent']:.1f}%)")
        
        print(f"\n🐍 PYTHON PROCESS")
        print(f"  CPU Average:    {summary['process']['cpu_avg']:.1f}%")
        print(f"  CPU Peak:       {summary['process']['cpu_max']:.1f}%")
        print(f"  Memory Average: {summary['process']['memory_avg_mb']:.1f} MB")
        print(f"  Memory Peak:    {summary['process']['memory_max_mb']:.1f} MB")
        print(f"  Threads:        {summary['process']['threads']}")
        
        # Python process assessment
        if summary['process']['cpu_avg'] > 80:
            print(f"  ⚠️  Python process is CPU-saturated (avg {summary['process']['cpu_avg']:.1f}%)")
        else:
            print(f"  ℹ️  Python process CPU usage is {summary['process']['cpu_avg']:.1f}%")
        
        print(f"\n🗄️  DATABASE")
        print(f"  Responsive Rate: {summary['database']['responsive_rate']:.1f}%")
        
        # Database assessment
        if summary['database']['responsive']:
            print(f"  ✓  Database is responsive ({summary['database']['responsive_rate']:.1f}% uptime)")
        else:
            print(f"  ⚠️  Database had connectivity issues ({summary['database']['responsive_rate']:.1f}% uptime)")
        
        print(f"\n🎯 BOTTLENECK DIAGNOSIS")
        
        # Determine primary bottleneck
        bottlenecks = []
        
        if summary['cpu']['total_avg'] > 80:
            bottlenecks.append(("CPU (System)", summary['cpu']['total_avg'], "high"))
        if summary['process']['cpu_avg'] > 80:
            bottlenecks.append(("CPU (Python)", summary['process']['cpu_avg'], "high"))
        if summary['memory']['max_percent'] > 95:  # Adjust threshold - 85% is baseline
            bottlenecks.append(("Memory", summary['memory']['max_percent'], "high"))
        if not summary['database']['responsive']:
            bottlenecks.append(("Database Connectivity", summary['database']['responsive_rate'], "low"))
        
        # Check for IDLE workers (low CPU with many cores available)
        cpu_cores_available = summary['cpu']['logical_cores']
        cpu_utilization_per_core = summary['cpu']['total_avg'] / cpu_cores_available
        
        if bottlenecks:
            bottlenecks.sort(key=lambda x: x[1], reverse=True)
            print(f"  Primary Bottleneck: {bottlenecks[0][0]} ({bottlenecks[0][1]:.1f})")
            if len(bottlenecks) > 1:
                print(f"  Secondary Issues:")
                for name, value, _ in bottlenecks[1:]:
                    print(f"    - {name} ({value:.1f})")
        else:
            print(f"  ⚠️  WORKERS ARE IDLE - COORDINATION BOTTLENECK DETECTED")
            print(f"     System CPU: {summary['cpu']['total_avg']:.1f}% average ({summary['cpu']['total_max']:.1f}% peak)")
            print(f"     Per-Core Utilization: {cpu_utilization_per_core:.1f}% average")
            print(f"     Available Cores: {cpu_cores_available} logical cores")
            print(f"     Hottest Core: {summary['cpu']['max_core_avg']:.1f}% average, {summary['cpu']['max_core_max']:.1f}% peak")
            print(f"")
            print(f"     ROOT CAUSE: Workers are waiting/blocked, not processing")
            print(f"     Possible causes:")
            print(f"       1. Multiprocessing coordination overhead (queue/lock contention)")
            print(f"       2. Database connection serialization (single connection bottleneck)")
            print(f"       3. Work distribution inefficiency (batch size too small)")
            print(f"       4. GIL contention (unlikely with multiprocessing but possible)")
            print(f"       5. Network latency to RDS (workers waiting for DB responses)")
        
        print(f"\n💡 RECOMMENDATIONS (Priority Order)")
        
        # Analyze the specific scenario
        if summary['cpu']['total_avg'] < 20:
            print(f"\n  🚨 CRITICAL: Workers are SEVERELY IDLE (CPU: {summary['cpu']['total_avg']:.1f}%)")
            print(f"")
            print(f"  IMMEDIATE ACTIONS:")
            print(f"")
            print(f"  1. INCREASE BATCH SIZE (highest priority)")
            print(f"     Current: 250")
            print(f"     Test:    --batch-size 500")
            print(f"     Then:    --batch-size 1000")
            print(f"     Reason: Reduce per-batch coordination overhead")
            print(f"")
            print(f"  2. PROFILE DATABASE OPERATIONS")
            print(f"     Add timing to MigrationEngine bulk inserts")
            print(f"     Check if workers wait for DB responses")
            print(f"     Test with connection pooling disabled (currently enabled)")
            print(f"")
            print(f"  3. CHECK NETWORK LATENCY TO RDS")
            print(f"     Run: Test-NetConnection {summary.get('server', 'RDS-endpoint')} -Port 1433")
            print(f"     High latency (>50ms) multiplied by 16 workers = significant wait time")
            print(f"")
            print(f"  4. DON'T INCREASE WORKERS YET")
            print(f"     Adding more workers won't help if they're already idle")
            print(f"     Fix coordination bottleneck first, then scale workers")
            
        elif summary['cpu']['total_avg'] < 50:
            print(f"\n  ⚠️  Workers are underutilized (CPU: {summary['cpu']['total_avg']:.1f}%)")
            print(f"")
            print(f"  1. Increase batch size to reduce coordination overhead")
            print(f"     → Test --batch-size 500 and --batch-size 1000")
            print(f"")
            print(f"  2. Profile to identify wait points")
            print(f"     → Use cProfile on worker processes")
            print(f"")
            print(f"  3. Consider increasing workers after fixing coordination")
            print(f"     → Test with 24 workers once CPU reaches 60%+")
        
        if summary['cpu']['max_core_max'] > 90 and summary['cpu']['total_avg'] < 30:
            print(f"\n  ℹ️  Single-core hotspot detected (hottest: {summary['cpu']['max_core_max']:.1f}%)")
            print(f"     → Main coordinator thread may be serializing work")
            print(f"     → Check ParallelCoordinator._distribute_work_items() for bottlenecks")
        
        print("="*80 + "\n")
    
    def save_detailed_report(self, filepath):
        """Save detailed samples to JSON file"""
        report = {
            'summary': self.get_summary(),
            'samples': self.samples,
        }
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✓ Detailed report saved to {filepath}")


def main():
    """Run profiler alongside production processor"""
    import subprocess
    
    print("="*80)
    print("RESOURCE PROFILER FOR XML EXTRACTION SYSTEM")
    print("="*80)
    print("\nThis script will:")
    print("  1. Start resource monitoring (CPU, memory, disk, database)")
    print("  2. Run production_processor.py with specified parameters")
    print("  3. Generate performance analysis and bottleneck diagnosis")
    print()
    
    # Get configuration
    config = get_config_manager()
    server = config.database_config.server
    database = config.database_config.database
    
    # Default test parameters
    workers = 16
    batch_size = 250
    limit = 2000
    
    print(f"Configuration:")
    print(f"  Server:     {server}")
    print(f"  Database:   {database}")
    print(f"  Workers:    {workers}")
    print(f"  Batch Size: {batch_size}")
    print(f"  Limit:      {limit}")
    print()
    
    input("Press Enter to start profiling...")
    
    # Start profiler
    profiler = ResourceProfiler(interval_seconds=1.0)
    profiler.start_monitoring(server, database)
    
    # Build command
    cmd = [
        'python',
        'production_processor.py',
        '--server', server,
        '--database', database,
        '--workers', str(workers),
        '--batch-size', str(batch_size),
        '--limit', str(limit),
        '--log-level', 'WARNING',
    ]
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    print("="*80 + "\n")
    
    try:
        # Run processor
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    finally:
        # Stop profiler
        print("\n")
        profiler.stop_monitoring()
        
        # Print summary
        profiler.print_summary()
        
        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"diagnostics/profile_report_{timestamp}.json"
        os.makedirs("diagnostics", exist_ok=True)
        profiler.save_detailed_report(report_file)


if __name__ == '__main__':
    main()
