"""
Sequential Chunked Processor Orchestrator

Manages sequential execution of production_processor.py with automatic process lifecycle
management. Breaks large datasets into manageable chunks, each running as a fresh process
to prevent memory degradation and performance issues over long runs.

Specifically this addresses Python internal state accumulation: lxml caches, pyodbc metadata, type system caches

=============================================================================
QUICK START
=============================================================================

Simple Usage (with defaults):
    python run_production_processor.py --app-id-start 1 --app-id-end 60000
    
    Defaults: chunk-size=10000, batch-size=500, workers=4, log-level=WARNING

Limit Mode (for testing):
    python run_production_processor.py --limit 60000

Custom Chunk Size:
    python run_production_processor.py --app-id-start 1 --app-id-end 60000 --chunk-size 5000

=============================================================================
WHY USE THIS INSTEAD OF production_processor.py?
=============================================================================

Use Orchestrator When:
  - Processing >100k records (prevents memory degradation)
  - Want automatic resume capability per chunk
  - Need per-chunk performance tracking
  - Long-running jobs that might be interrupted

Use Direct Processor When:
  - Processing <100k records
  - Running concurrent instances manually
  - Need fine-grained control over single execution

=============================================================================
HOW IT WORKS
=============================================================================

Chunking = Process Lifecycle Management (NOT Concurrency)

For: --app-id-start 1 --app-id-end 60000 --chunk-size 10000

Creates 6 sequential chunks:
  Chunk 1: Spawns process for app_ids 1-10,000     → waits for completion
  Chunk 2: Spawns process for app_ids 10,001-20,000 → waits for completion
  Chunk 3: Spawns process for app_ids 20,001-30,000 → waits for completion
  ... continues sequentially ...
  Chunk 6: Spawns process for app_ids 50,001-60,000 → waits for completion

Each chunk:
  - Fresh Python process (clean memory state)
  - Independent metrics file
  - Independent log file
  - Resume-safe (skips already-processed records)

Benefits:
  - Prevents memory leaks over long runs
  - Natural checkpoints every chunk
  - Easier to resume after interruption
  - Per-chunk performance visibility

=============================================================================
CLI REFERENCE
=============================================================================

Processing Mode (choose one):
    --app-id-start + 
    --app-id-end          Explicit range (recommended)
    --limit               Process up to N records starting from app_id 1

Chunking:
    --chunk-size          Records per chunk (default: 10000)

Pass-Through Parameters (same as production_processor.py):
    --server              SQL Server instance (default: localhost\\SQLEXPRESS)
    --database            Database name (default: XmlConversionDB)
    --workers             Parallel workers per chunk (default: 4)
    --batch-size          Records per batch (default: 500)
    --log-level           Console verbosity (default: WARNING)
    --username            SQL Server username (optional)
    --password            SQL Server password (optional)
    --enable-pooling      Enable connection pooling
    --disable-mars        Disable MARS

=============================================================================
PERFORMANCE NOTES
=============================================================================

Chunk Size Guidelines:
  - 10,000 (default): Good balance for most scenarios (~6-8 minutes per chunk)
  - 5,000: Faster checkpoints, more overhead
  - 20,000: Fewer checkpoints, longer per-chunk time

Typical Throughput:
  ~1500-1600 applications/minute per chunk (4 workers, batch-size=500)
  
Cross-Chunk Behavior:
  - First chunk includes warmup (slower start)
  - Subsequent chunks may have slight degradation (-5% typical)
  - Fresh process each chunk prevents long-term memory issues

When to Adjust Workers/Batch Size:
  - Use same tuning as production_processor.py
  - All chunks use same settings
  - Coordinate with available CPU cores and memory

=============================================================================
TROUBLESHOOTING
=============================================================================

Chunk Fails:
  - Orchestrator prompts: "Continue with next chunk? (y/n)"
  - Choose 'n' to stop and investigate
  - Fix issue, re-run same command (resume-safe)

Already-Processed Records:
  - Automatically skipped via processing_log
  - Shows as fast chunks (<30s)
  - Re-running is safe and efficient

Memory Issues:
  - Reduce --chunk-size (more frequent process restarts)
  - Reduce --batch-size (less memory per batch)
  - Reduce --workers (less parallelism)

=============================================================================
"""

import argparse
import subprocess
import sys
import json

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from xml_extractor.config.processing_defaults import ProcessingDefaults


class ChunkedProcessorOrchestrator:
    """Orchestrates sequential execution of production_processor.py in chunks."""
    
    def __init__(self, chunk_size: int, app_id_start: int = None, app_id_end: int = None, limit: int = None, **processor_kwargs):
        """
        Initialize orchestrator.
        
        Args:
            chunk_size: Records per chunk
            app_id_start: Starting app_id for range-based processing (requires app_id_end)
            app_id_end: Ending app_id for range-based processing (requires app_id_start)
            limit: Total records to process starting from app_id 1 (alternative to range mode)
            **processor_kwargs: Pass-through arguments for production_processor.py
        
        Note: Must provide EITHER (app_id_start AND app_id_end) OR limit, not both.
        """
        # Validate mutually exclusive modes
        if (app_id_start is not None or app_id_end is not None) and limit is not None:
            raise ValueError("Cannot specify both app_id range (--app-id-start/--app-id-end) and --limit")
        
        if app_id_start is not None and app_id_end is None:
            raise ValueError("--app-id-start requires --app-id-end")
        
        if app_id_end is not None and app_id_start is None:
            raise ValueError("--app-id-end requires --app-id-start")
        
        if app_id_start is None and app_id_end is None and limit is None:
            raise ValueError("Must specify either app_id range (--app-id-start and --app-id-end) or --limit")
        
        # Calculate range parameters
        if app_id_start is not None and app_id_end is not None:
            # Range mode
            self.app_id_start = app_id_start
            self.app_id_end = app_id_end
            self.total_records = app_id_end - app_id_start + 1
            self.mode = "range"
        else:
            # Limit mode
            self.app_id_start = 1
            self.app_id_end = limit
            self.total_records = limit
            self.mode = "limit"
        
        self.chunk_size = chunk_size
        self.processor_kwargs = processor_kwargs
        self.num_chunks = (self.total_records + chunk_size - 1) // chunk_size  # Ceiling division
        self.chunk_results: List[Dict] = []
    
    def run(self) -> int:
        """
        Execute all chunks sequentially.
        
        Returns:
            0 on success, 1 on failure
        """
        print("=" * 82)
        print(" CHUNKED PROCESSING ORCHESTRATOR")
        print("=" * 82)
        print(f"  Run Mode:       {self.mode.upper()}")
        print(f"  App Id Range:   {self.app_id_start:,} - {self.app_id_end:,} ({self.total_records:,} applications)")
        print(f"  Chunk Size:     {self.chunk_size:,}")
        print(f"  Total Chunks:   {self.num_chunks}")
        print(f"  Start Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 82)
        print()
        
        start_time = datetime.now()
        
        try:
            # Execute each chunk sequentially
            for chunk_num in range(1, self.num_chunks + 1):
                # Calculate app_id range for this chunk
                chunk_start_id = self.app_id_start + (chunk_num - 1) * self.chunk_size
                chunk_end_id = min(self.app_id_start + chunk_num * self.chunk_size - 1, self.app_id_end)
                
                print("\n" + "=" * 82)
                print(f" CHUNK {chunk_num}/{self.num_chunks}: [app_id] RANGE: {chunk_start_id:,} - {chunk_end_id:,}")
                print("=" * 82)
                
                chunk_start_time = datetime.now()
                
                # Build command for production_processor.py
                cmd = self._build_processor_command(chunk_start_id, chunk_end_id)
                
                # Execute chunk (blocks until completion)
                result = subprocess.run(cmd, shell=True)
                
                chunk_end_time = datetime.now()
                chunk_duration = (chunk_end_time - chunk_start_time).total_seconds()
                
                # Track chunk result
                chunk_info = {
                    'chunk_num': chunk_num,
                    'start_id': chunk_start_id,
                    'end_id': chunk_end_id,
                    'duration_seconds': chunk_duration,
                    'exit_code': result.returncode,
                    'success': result.returncode == 0,
                    'throughput': None  # Will be populated from metrics file
                }
                
                # Try to load throughput from metrics file
                chunk_info['throughput'] = self._extract_throughput_from_metrics(chunk_start_id, chunk_end_id)
                
                self.chunk_results.append(chunk_info)
                
                # Show chunk summary with context
                status = " SUCCESS" if result.returncode == 0 else " FAILED"
                if chunk_duration < 30:
                    print(f"\n Chunk {chunk_num} {status} - Duration: {chunk_duration:.1f}s (fast - likely already processed)")
                else:
                    print(f"\n Chunk {chunk_num} {status} - Duration: {chunk_duration:.1f}s")
                
                if result.returncode != 0:
                    print(f"\n  Chunk {chunk_num} FAILED with exit code {result.returncode}")
                    if chunk_num < self.num_chunks:
                        response = input(" Continue with next chunk? (y/n): ")
                        if response.lower() != 'y':
                            print(" Orchestration aborted by user")
                            return 1
            
            # Print final summary
            self._print_summary(start_time)
            
            return 0
            
        except KeyboardInterrupt:
            print("\n\n  Orchestration interrupted by user")
            self._print_summary(start_time)
            return 1
        except Exception as e:
            print(f"\n\n Orchestration error: {e}")
            return 1
    
    def _build_processor_command(self, start_id: int, end_id: int) -> str:
        """
        Build command line for production_processor.py.
        
        Args:
            start_id: Starting app_id for this chunk
            end_id: Ending app_id for this chunk
            
        Returns:
            Command string ready for subprocess.run()
        """
        cmd_parts = [
            "python",
            "production_processor.py",
            f"--app-id-start {start_id}",
            f"--app-id-end {end_id}"
        ]
        
        # Add pass-through parameters
        for key, value in self.processor_kwargs.items():
            if value is not None:
                # Convert Python snake_case to CLI kebab-case
                cli_key = key.replace('_', '-')
                
                # Handle boolean flags
                if isinstance(value, bool):
                    if value:
                        cmd_parts.append(f"--{cli_key}")
                else:
                    cmd_parts.append(f"--{cli_key} {value}")
        
        return " ".join(cmd_parts)
    
    def _extract_throughput_from_metrics(self, start_id: int, end_id: int) -> Optional[float]:
        """
        Extract throughput (apps/min) from the metrics file for a chunk.
        
        Args:
            start_id: Starting app_id for this chunk
            end_id: Ending app_id for this chunk
            
        Returns:
            Throughput in apps/minute, or None if metrics file not found
        """
        try:
            # Look for most recent metrics file matching this range
            metrics_dir = Path("metrics")
            pattern = f"metrics_*_range_{start_id}_{end_id}.json"
            
            matching_files = sorted(metrics_dir.glob(pattern), 
                                   key=lambda x: x.stat().st_mtime, 
                                   reverse=True)
            
            if matching_files:
                metrics_file = matching_files[0]
                with open(metrics_file) as f:
                    data = json.load(f)
                    return data.get('applications_per_minute')
        except Exception:
            pass  # Silently skip if file not found or error reading
        
        return None
    
    
    def _print_summary(self, start_time: datetime):
        """Print summary of all chunks processed."""
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 82)
        print(" ORCHESTRATION SUMMARY")
        print("=" * 82)
        
        if not self.chunk_results:
            print(" No chunks completed!")
            return
        
        successful_chunks = sum(1 for c in self.chunk_results if c['success'])
        failed_chunks = len(self.chunk_results) - successful_chunks
        
        print(f"  Total Chunks:      {len(self.chunk_results)}/{self.num_chunks}")
        print(f"  Successful:        {successful_chunks}")
        print(f"  Failed:            {failed_chunks}")
        print(f"  Total Duration:    {total_duration:.1f}s ({total_duration / 60:.1f} minutes)")
        
        if len(self.chunk_results) > 1:
            avg_duration = sum(c['duration_seconds'] for c in self.chunk_results) / len(self.chunk_results)
            print(f"  Avg Chunk Time:    {avg_duration:.1f}s")
        
        print(f"  End Time:          {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Throughput analysis (if metrics are available)
        throughputs = [c['throughput'] for c in self.chunk_results if c['throughput'] is not None]
        if throughputs:
            avg_throughput = sum(throughputs) / len(throughputs)
            min_throughput = min(throughputs)
            max_throughput = max(throughputs)
            
            print(f"\n THROUGHPUT")
            print(f"  Average:           {avg_throughput:.1f} apps/min")
            print(f"  Peak:              {max_throughput:.1f} apps/min")
            print(f"  Minimum:           {min_throughput:.1f} apps/min")
            # print(f"  Range:             {max_throughput - min_throughput:.1f} apps/min ({((max_throughput - min_throughput) / max_throughput * 100):.1f}%)")
            
            # Per-third analysis
            if len(throughputs) >= 3:
                third = len(throughputs) // 3
                first_third_avg = sum(throughputs[:third]) / len(throughputs[:third])
                last_third_avg = sum(throughputs[-third:]) / len(throughputs[-third:])
                degradation = ((last_third_avg - first_third_avg) / first_third_avg) * 100
                # print(f"  First/Last Thirds:  {first_third_avg:.1f} → {last_third_avg:.1f} ({degradation:+.1f}%)")
        
        # Per-chunk breakdown
        if self.chunk_results:
            print("\n BREAKDOWN")
            if throughputs:
                print(f"{'  Chunk':<10} {' Range':<20} {'Duration':<12} {'Apps/Min':<12} {'Status':<10}")
                print("-" * 82)
                
                for i, chunk in enumerate(self.chunk_results):
                    range_str = f"  {chunk['start_id']:,}-{chunk['end_id']:,}"
                    duration_str = f" {chunk['duration_seconds']:.1f}s"
                    throughput_str = f" {chunk['throughput']:.1f}" if chunk['throughput'] is not None else " N/A"
                    status_str = " SUCCESS" if chunk['success'] else " FAILED"
                    
                    print(f" {chunk['chunk_num']:<10} {range_str:<20} {duration_str:<12} {throughput_str:<12} {status_str:<10}")
            else:
                print(f" {'  Chunk':<10} {' Range':<20} {'Duration':<12} {'Status':<10}")
                print("-" * 82)
                
                for chunk in self.chunk_results:
                    range_str = f"  {chunk['start_id']:,}-{chunk['end_id']:,}"
                    duration_str = f" {chunk['duration_seconds']:.1f}s"
                    status_str = " SUCCESS" if chunk['success'] else " FAILED"

                    print(f" {chunk['chunk_num']:<10} {range_str:<20} {duration_str:<12} {status_str:<10}")

        print("-" * 82)
        print("\n FINISHED!\n")


def main():
    """Parse arguments and run orchestrator."""
    parser = argparse.ArgumentParser(
        description="Sequential Chunked Processor Orchestrator - Process large datasets in manageable chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
    Examples:
    # Process app_ids 1-60,000 in chunks of 10,000 (RANGE MODE - recommended)
        python run_production_processor.py --app-id-start 1 --app-id-end 60000
    
    # Process app_ids 70,001-100,000 with custom chunk size (RANGE MODE)
        python run_production_processor.py --app-id-start 70001 --app-id-end 100000 --chunk-size 5000
    
    # Process up to 60,000 records in default chunks (LIMIT MODE - for testing)
        python run_production_processor.py --limit 60000
    
    # Use 6 workers per chunk with custom batch size
        python run_production_processor.py --batch-size 750 --app-id-start 1 --app-id-end 60000 --workers 6

    Note: For concurrent processing, manually spawn multiple instances with different ranges.
        """
    )
    
    # Chunking parameters (mutually exclusive: range mode OR limit mode)
    parser.add_argument("--chunk-size", type=int, default=ProcessingDefaults.CHUNK_SIZE,
                       help=f"Number of records per chunk (default: {ProcessingDefaults.CHUNK_SIZE})")
    parser.add_argument("--app-id-start", type=int,
                       help="Starting app_id for range-based chunking (requires --app-id-end)")
    parser.add_argument("--app-id-end", type=int,
                       help="Ending app_id for range-based chunking (requires --app-id-start)")
    parser.add_argument("--limit", type=int,
                       help="Total records to process starting from app_id 1 (alternative to range mode)")
    
    # Database connection (pass-through to production_processor.py)
    parser.add_argument("--server", default="localhost\\SQLEXPRESS",
                       help="SQL Server instance (default: localhost\\SQLEXPRESS)")
    parser.add_argument("--database", default="XmlConversionDB",
                       help="Database name (default: XmlConversionDB)")
    parser.add_argument("--username", help="SQL Server username (uses Windows auth if not provided)")

    parser.add_argument("--password", help="SQL Server password")
    
    # Processing parameters (pass-through)
    parser.add_argument("--workers", type=int, default=ProcessingDefaults.WORKERS,
                       help=f"Number of parallel workers per chunk (default: {ProcessingDefaults.WORKERS})")
    parser.add_argument("--batch-size", type=int, default=ProcessingDefaults.BATCH_SIZE,
                       help=f"Records per batch (default: {ProcessingDefaults.BATCH_SIZE})")
    parser.add_argument("--log-level", default=ProcessingDefaults.LOG_LEVEL,
                       choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
                       help=f"Logging level (default: {ProcessingDefaults.LOG_LEVEL})")
    
    # Connection pooling (pass-through)
    parser.add_argument("--enable-pooling", action="store_true", default=ProcessingDefaults.ENABLE_POOLING,
                       help=f"Enable connection pooling (default: {ProcessingDefaults.ENABLE_POOLING})")
    parser.add_argument("--min-pool-size", type=int, default=ProcessingDefaults.CONNECTION_POOL_MIN,
                       help=f"Minimum pool size (default: {ProcessingDefaults.CONNECTION_POOL_MIN})")
    parser.add_argument("--max-pool-size", type=int, default=ProcessingDefaults.CONNECTION_POOL_MAX,
                       help=f"Maximum pool size (default: {ProcessingDefaults.CONNECTION_POOL_MAX})")
    parser.add_argument("--disable-mars", action="store_true", default=not ProcessingDefaults.MARS_ENABLED,
                       help=f"Disable Multiple Active Result Sets (default: MARS {'enabled' if ProcessingDefaults.MARS_ENABLED else 'disabled'})")
    parser.add_argument("--connection-timeout", type=int, default=ProcessingDefaults.CONNECTION_TIMEOUT,
                       help=f"Connection timeout in seconds (default: {ProcessingDefaults.CONNECTION_TIMEOUT})")
    
    args = parser.parse_args()
    
    # Validate mutually exclusive modes
    has_range = args.app_id_start is not None or args.app_id_end is not None
    has_limit = args.limit is not None
    
    if not has_range and not has_limit:
        print(" ERROR: Must specify either --app-id-start/--app-id-end (range mode) or --limit (limit mode)")
        return 1
    
    if has_range and has_limit:
        print(" ERROR: Cannot specify both range mode (--app-id-start/--app-id-end) and limit mode (--limit)")
        return 1
    
    if args.app_id_start is not None and args.app_id_end is None:
        print(" ERROR: --app-id-start requires --app-id-end")
        return 1
    
    if args.app_id_end is not None and args.app_id_start is None:
        print(" ERROR: --app-id-end requires --app-id-start")
        return 1
    
    # Validate range values
    if has_range:
        if args.app_id_start < 1:
            print(" ERROR: --app-id-start must be >= 1")
            return 1
        if args.app_id_end < args.app_id_start:
            print(" ERROR: --app-id-end must be >= --app-id-start")
            return 1
    
    # Validate chunk size
    if args.chunk_size <= 0:
        print(" ERROR: --chunk-size must be positive")
        return 1
    
    # Build pass-through kwargs
    processor_kwargs = {
        'server': args.server,
        'database': args.database,
        'username': args.username,
        'password': args.password,
        'workers': args.workers,
        'batch_size': args.batch_size,
        'log_level': args.log_level,
        'enable_pooling': args.enable_pooling,
        'min_pool_size': args.min_pool_size,
        'max_pool_size': args.max_pool_size,
        'disable_mars': args.disable_mars,
        'connection_timeout': args.connection_timeout
    }
    
    # Run orchestrator
    orchestrator = ChunkedProcessorOrchestrator(
        chunk_size=args.chunk_size,
        app_id_start=args.app_id_start,
        app_id_end=args.app_id_end,
        limit=args.limit,
        **processor_kwargs
    )
    
    return orchestrator.run()


if __name__ == "__main__":
    sys.exit(main())

