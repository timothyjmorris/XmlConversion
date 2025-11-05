#!/usr/bin/env python3
"""
Demo of the enhanced orchestration summary with throughput analysis.
Shows what the output will look like when running run_production_processor.py
"""

import json
from pathlib import Path

print("=" * 82)
print("ORCHESTRATION SUMMARY (Enhanced)")
print("=" * 82)

# Load some actual metrics files to show real data
metrics_dir = Path("metrics")
files = sorted(metrics_dir.glob("metrics_20251105_*.json"))[:6]  # First 6 chunks of 220k run

if files:
    throughputs = []
    chunks_info = []
    
    for i, metrics_file in enumerate(files, 1):
        with open(metrics_file) as f:
            data = json.load(f)
            throughput = data['applications_per_minute']
            throughputs.append(throughput)
            chunks_info.append({
                'chunk_num': i,
                'start_id': data['app_id_start'],
                'end_id': data['app_id_end'],
                'duration': data['total_duration_seconds'],
                'throughput': throughput,
                'success': data['success_rate'] == 100
            })
    
    # Summary stats
    print(f"\nTotal Chunks:      {len(chunks_info)}/6")
    print(f"Successful:        {len(chunks_info)}")
    print(f"Failed:            0")
    print(f"Total Duration:    {sum(c['duration'] for c in chunks_info):.1f}s ({sum(c['duration'] for c in chunks_info) / 60:.1f} minutes)")
    print(f"End Time:          2025-11-05 01:55:25")
    
    # Throughput analysis
    avg_throughput = sum(throughputs) / len(throughputs)
    min_throughput = min(throughputs)
    max_throughput = max(throughputs)
    
    print(f"\nThroughput Analysis:")
    print(f"Average:           {avg_throughput:.1f} apps/min")
    print(f"Peak:              {max_throughput:.1f} apps/min")
    print(f"Minimum:           {min_throughput:.1f} apps/min")
    print(f"Range:             {max_throughput - min_throughput:.1f} apps/min ({((max_throughput - min_throughput) / max_throughput * 100):.1f}%)")
    
    # Per-third analysis
    if len(throughputs) >= 3:
        third = len(throughputs) // 3
        first_third_avg = sum(throughputs[:third]) / len(throughputs[:third])
        last_third_avg = sum(throughputs[-third:]) / len(throughputs[-third:])
        degradation = ((last_third_avg - first_third_avg) / first_third_avg) * 100
        print(f"First/Last Thirds:  {first_third_avg:.1f} → {last_third_avg:.1f} ({degradation:+.1f}%)")
    
    # Per-chunk breakdown with throughput
    print("\nPer-Chunk Breakdown:")
    print(f"{'Chunk':<8} {'Range':<20} {'Duration':<12} {'Apps/Min':<12} {'Status':<10}")
    print("-" * 82)
    
    for chunk in chunks_info:
        range_str = f"{chunk['start_id']:,}-{chunk['end_id']:,}"
        duration_str = f"{chunk['duration']:.1f}s"
        throughput_str = f"{chunk['throughput']:.1f}"
        status_str = "✓ SUCCESS" if chunk['success'] else "✗ FAILED"
        
        print(f"{chunk['chunk_num']:<8} {range_str:<20} {duration_str:<12} {throughput_str:<12} {status_str:<10}")
    
    print("=" * 82)
else:
    print("No metrics files found")
