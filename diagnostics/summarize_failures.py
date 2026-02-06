"""
Summarize Failed Applications from Production Metrics

Reads metrics JSON files and generates a consolidated failure report showing:
- All failed app_ids with failure reasons
- Failure breakdown by error stage
- Optional CSV/JSON export for further analysis

USAGE:
    # Summarize latest metrics file (outputs to console and JSON)
    python diagnostics/summarize_failures.py
    
    # Summarize specific metrics file
    python diagnostics/summarize_failures.py --metrics-file metrics/metrics_20260206_001448.json
    
    # Export to CSV
    python diagnostics/summarize_failures.py --csv failures_summary.csv
    
    # Export to JSON
    python diagnostics/summarize_failures.py --json failures_summary.json
    
    # Summarize all metrics from a session
    python diagnostics/summarize_failures.py --session 20260206_001448
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict


def find_latest_metrics_file() -> Path:
    """Find the most recent metrics file."""
    metrics_dir = Path("metrics")
    if not metrics_dir.exists():
        raise FileNotFoundError("metrics/ directory not found")
    
    metrics_files = list(metrics_dir.glob("metrics_*.json"))
    if not metrics_files:
        raise FileNotFoundError("No metrics files found in metrics/")
    
    # Sort by modification time, most recent first
    metrics_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return metrics_files[0]


def find_session_metrics_files(session_id: str) -> List[Path]:
    """Find all metrics files for a specific session."""
    metrics_dir = Path("metrics")
    if not metrics_dir.exists():
        raise FileNotFoundError("metrics/ directory not found")
    
    # Match files like metrics_20260206_001448*.json
    pattern = f"metrics_{session_id}*.json"
    metrics_files = list(metrics_dir.glob(pattern))
    
    if not metrics_files:
        raise FileNotFoundError(f"No metrics files found for session {session_id}")
    
    # Sort by filename (handles instance numbers naturally)
    metrics_files.sort()
    return metrics_files


def find_latest_batch_metrics_files() -> List[Path]:
    """Find all metrics files from the latest batch run.
    
    Extracts the batch info from the latest metrics file and finds all files
    from that same batch (e.g., all instance files from the same 13-instance run).
    """
    metrics_dir = Path("metrics")
    if not metrics_dir.exists():
        raise FileNotFoundError("metrics/ directory not found")
    
    # Find all main metrics files (not error files)
    metrics_files = list(metrics_dir.glob("metrics_*.json"))
    if not metrics_files:
        raise FileNotFoundError("No metrics files found in metrics/")
    
    # Sort by modification time to get the latest batch
    metrics_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    latest_file = metrics_files[0]
    
    # Extract batch info from filename
    # Format: metrics_YYYYMMDD_HHMMSS_instance_X_of_N.json
    filename = latest_file.name
    
    # Extract the "of_N" part to identify batch size
    if "_of_" in filename:
        batch_size_part = filename.split("_of_")[1].split(".")[0]
        try:
            batch_size = int(batch_size_part)
        except ValueError:
            raise ValueError(f"Cannot parse batch size from: {filename}")
        
        # Extract date part (YYYYMMDD)
        date_part = filename.split("_")[1]  # e.g., "20260206"
        
        # Find all files from this date with the same batch size
        pattern = f"metrics_{date_part}_*_of_{batch_size}.json"
        batch_files = list(metrics_dir.glob(pattern))
    else:
        # Single file without instance info
        batch_files = [latest_file]
    
    if not batch_files:
        raise FileNotFoundError(f"No metrics files found for latest batch")
    
    # Sort by filename (handles instance numbers naturally)
    batch_files.sort()
    
    return batch_files


def load_metrics(metrics_file: Path) -> dict:
    """Load metrics from JSON file."""
    with open(metrics_file, 'r') as f:
        return json.load(f)


def extract_failures(metrics: dict) -> List[Dict]:
    """Extract failed apps from metrics structure."""
    failed_apps = metrics.get('failed_apps', [])
    
    # Enrich with metadata from metrics
    run_timestamp = metrics.get('run_timestamp', 'unknown')
    app_id_start = metrics.get('app_id_start')
    app_id_end = metrics.get('app_id_end')
    
    for failed_app in failed_apps:
        failed_app['run_timestamp'] = run_timestamp
        failed_app['app_id_start'] = app_id_start
        failed_app['app_id_end'] = app_id_end
    
    return failed_apps


def format_failure_summary(all_failures: List[Dict], metrics_files: List[Path]) -> str:
    """Format a human-readable failure summary."""
    if not all_failures:
        return "No failures found in metrics files."
    
    lines = []
    lines.append("=" * 100)
    lines.append(" FAILURE SUMMARY")
    lines.append("=" * 100)
    lines.append(f" Metrics Files Analyzed: {len(metrics_files)}")
    lines.append(f" Total Failed Applications: {len(all_failures)}")
    lines.append("")
    
    # Breakdown by error stage
    stage_counts = defaultdict(int)
    for failure in all_failures:
        stage = failure.get('error_stage', 'unknown')
        stage_counts[stage] += 1
    
    lines.append(" Failure Breakdown by Stage:")
    lines.append(" " + "-" * 60)
    for stage, count in sorted(stage_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(all_failures) * 100)
        lines.append(f"   {stage:25s}: {count:5d} ({pct:5.1f}%)")
    lines.append("")
    
    # Detailed failure list (grouped by error stage)
    lines.append(" Failed Applications by Error Stage:")
    lines.append(" " + "-" * 98)
    
    failures_by_stage = defaultdict(list)
    for failure in all_failures:
        stage = failure.get('error_stage', 'unknown')
        failures_by_stage[stage].append(failure)
    
    for stage in sorted(failures_by_stage.keys()):
        stage_failures = failures_by_stage[stage]
        lines.append(f"\n [{stage.upper()}] ({len(stage_failures)} failures)")
        lines.append(" " + "-" * 98)
        
        # Show first 20 of each stage
        for i, failure in enumerate(stage_failures[:20], 1):
            app_id = failure.get('app_id', 'unknown')
            error_msg = failure.get('error_message', 'No error message')
            # Truncate long error messages
            if len(error_msg) > 80:
                error_msg = error_msg[:77] + "..."
            lines.append(f"   {i:3d}. app_id={app_id:8d} | {error_msg}")
        
        if len(stage_failures) > 20:
            lines.append(f"   ... and {len(stage_failures) - 20} more {stage} failures")
    
    lines.append("")
    lines.append("=" * 100)
    
    return "\n".join(lines)


def export_to_csv(all_failures: List[Dict], csv_path: Path):
    """Export failures to CSV file."""
    import csv
    
    if not all_failures:
        print("No failures to export")
        return
    
    # Determine CSV headers from first failure
    fieldnames = ['app_id', 'error_stage', 'error_message', 'processing_time', 
                  'run_timestamp', 'app_id_start', 'app_id_end']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_failures)
    
    print(f"Exported {len(all_failures)} failures to: {csv_path}")


def export_to_json(all_failures: List[Dict], json_path: Path):
    """Export failures to JSON file with structured format."""
    if not all_failures:
        print("No failures to export")
        return
    
    # Group failures by error stage for easier analysis
    failures_by_stage = defaultdict(list)
    for failure in all_failures:
        stage = failure.get('error_stage', 'unknown')
        failures_by_stage[stage].append(failure)
    
    # Build output structure
    output = {
        'export_timestamp': datetime.now().isoformat(),
        'total_failed_apps': len(all_failures),
        'failures_by_stage': dict(sorted(failures_by_stage.items())),
        'all_failures': all_failures
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"Exported {len(all_failures)} failures to: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Summarize Failed Applications from Metrics")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--metrics-file", type=Path, 
                       help="Specific metrics JSON file to analyze")
    group.add_argument("--session", type=str,
                       help="Session ID to analyze all metrics files (e.g., '20260206_081615')")
    
    parser.add_argument("--csv", type=Path,
                       help="Export failures to CSV file")
    parser.add_argument("--json", type=Path, dest="json_file",
                       help="Export failures to JSON file (default: auto-generated filename)")
    parser.add_argument("--no-json", action="store_true",
                       help="Disable automatic JSON export")
    
    args = parser.parse_args()
    
    try:
        # Determine which metrics files to analyze
        if args.metrics_file:
            metrics_files = [args.metrics_file]
            if not metrics_files[0].exists():
                print(f"ERROR: Metrics file not found: {metrics_files[0]}")
                return 1
        elif args.session:
            metrics_files = find_session_metrics_files(args.session)
            print(f"Found {len(metrics_files)} metrics files for session {args.session}")
        else:
            # Use all metrics files from the latest batch
            metrics_files = find_latest_batch_metrics_files()
            print(f"Found {len(metrics_files)} metrics files from latest batch")
        
        # Load and extract failures from all files
        all_failures = []
        for metrics_file in metrics_files:
            metrics = load_metrics(metrics_file)
            failures = extract_failures(metrics)
            all_failures.extend(failures)
        
        # Print summary
        summary = format_failure_summary(all_failures, metrics_files)
        print(summary)
        
        # Export to CSV if requested
        if args.csv:
            export_to_csv(all_failures, args.csv)
        
        # Export to JSON (default: auto-generate filename, unless --no-json specified)
        if not args.no_json:
            if args.json_file:
                # Use specified JSON path
                export_to_json(all_failures, args.json_file)
            else:
                # Auto-generate JSON filename based on timestamp
                timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")[:-3]
                json_filename = f"failures_{timestamp}.json"
                json_path = Path("metrics") / json_filename
                export_to_json(all_failures, json_path)
        
        return 0
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
