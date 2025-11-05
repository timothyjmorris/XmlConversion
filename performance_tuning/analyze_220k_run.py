#!/usr/bin/env python3
"""
Analyze sustained 220k record processing run for throughput and degradation patterns.
Tests if system maintains performance over extended execution with process restarts.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def load_metrics(filepath):
    """Load metrics from JSON file."""
    with open(filepath) as f:
        return json.load(f)

def analyze_chunk(data, chunk_num):
    """Analyze a single 10k chunk."""
    batches = data.get('batch_details', [])
    
    # For single-file chunks, use overall metrics
    if not batches or len(batches) == 0:
        return {
            'chunk': chunk_num,
            'records': data['total_applications_processed'],
            'duration_sec': data['total_duration_seconds'],
            'throughput': data['applications_per_minute'],
            'success_rate': data['success_rate'],
            'failed': data['total_applications_failed'],
            'timestamp': data.get('run_timestamp', 'N/A'),
        }
    
    # If batch details exist, use first/last batch rates
    first_rate = batches[0]['applications_per_minute']
    last_rate = batches[-1]['applications_per_minute']
    decline = ((last_rate - first_rate) / first_rate) * 100
    
    return {
        'chunk': chunk_num,
        'records': data['total_applications_processed'],
        'duration_sec': data['total_duration_seconds'],
        'first_rate': first_rate,
        'last_rate': last_rate,
        'throughput': data['applications_per_minute'],
        'decline_pct': decline,
        'success_rate': data['success_rate'],
        'failed': data['total_applications_failed'],
        'timestamp': data.get('run_timestamp', 'N/A'),
    }

def main():
    metrics_dir = Path("metrics")
    
    # Find all 220k run files (range_*_*.json pattern from Nov 5 early morning)
    files = sorted(metrics_dir.glob("metrics_20251105_*.json"), 
                   key=lambda x: x.stat().st_mtime)
    
    if len(files) == 0:
        print("❌ No metrics files found from Nov 5 run")
        return
    
    print("=" * 90)
    print(f"SUSTAINED 220K PROCESSING RUN ANALYSIS")
    print(f"Total files: {len(files)}")
    print("=" * 90)
    
    print(f"\nAnalyzing {len(files)} chunks (10k records each):")
    
    # Analyze each chunk
    chunks = []
    for i, file in enumerate(files, 1):
        try:
            data = load_metrics(file)
            result = analyze_chunk(data, i)
            chunks.append(result)
        except Exception as e:
            print(f"⚠️  Error reading {file.name}: {e}")
    
    if not chunks:
        print("❌ No valid chunk data found")
        return
    
    # Display chunk-by-chunk results
    print("\n" + "=" * 90)
    print("CHUNK-BY-CHUNK THROUGHPUT")
    print("=" * 90)
    print("\nChunk | Records | Duration | Apps/Min | Success Rate | Status")
    print("------|---------|----------|----------|--------------|--------")
    
    for c in chunks:
        status = "✅" if c['success_rate'] == 100 else f"⚠️  ({c['failed']} failed)"
        print(f" {c['chunk']:3d}  | {c['records']:7,} | {c['duration_sec']:8.1f}s | {c['throughput']:8.1f} | {c['success_rate']:6.1f}%     | {status}")
    
    # Overall statistics
    total_records = sum(c['records'] for c in chunks)
    total_seconds = sum(c['duration_sec'] for c in chunks)
    total_minutes = total_seconds / 60
    total_failed = sum(c['failed'] for c in chunks)
    overall_success = 100 * (total_records - total_failed) / total_records
    overall_throughput = total_records / total_minutes
    
    print("\n" + "=" * 90)
    print("OVERALL PERFORMANCE METRICS")
    print("=" * 90)
    
    print(f"\nTotal records processed: {total_records:,}")
    print(f"Total time: {total_seconds:,.1f}s ({total_minutes:.1f} minutes, {total_minutes/60:.2f} hours)")
    print(f"Overall throughput: {overall_throughput:.1f} apps/min")
    print(f"Total failures: {total_failed}")
    print(f"Overall success rate: {overall_success:.1f}%")
    
    # Degradation analysis
    print("\n" + "=" * 90)
    print("DEGRADATION ANALYSIS")
    print("=" * 90)
    
    first_chunk_rate = chunks[0]['throughput']
    last_chunk_rate = chunks[-1]['throughput']
    overall_decline = ((last_chunk_rate - first_chunk_rate) / first_chunk_rate) * 100
    
    print(f"\nChunk 1 throughput: {first_chunk_rate:.1f} apps/min")
    print(f"Chunk {len(chunks)} throughput: {last_chunk_rate:.1f} apps/min")
    print(f"Overall decline: {overall_decline:+.1f}%")
    
    # Find min/max
    rates = [c['throughput'] for c in chunks]
    min_rate = min(rates)
    max_rate = max(rates)
    min_chunk = chunks[rates.index(min_rate)]['chunk']
    max_chunk = chunks[rates.index(max_rate)]['chunk']
    
    print(f"\nPeak throughput: {max_rate:.1f} apps/min (chunk {max_chunk})")
    print(f"Minimum throughput: {min_rate:.1f} apps/min (chunk {min_chunk})")
    print(f"Range: {max_rate - min_rate:.1f} apps/min ({((max_rate - min_rate) / max_rate * 100):.1f}%)")
    
    # Trend analysis (first 5, middle 5, last 5)
    print("\n" + "=" * 90)
    print("TREND ANALYSIS (by thirds)")
    print("=" * 90)
    
    third = len(chunks) // 3
    
    first_third_avg = sum(c['throughput'] for c in chunks[:third]) / len(chunks[:third])
    middle_third_avg = sum(c['throughput'] for c in chunks[third:2*third]) / len(chunks[third:2*third])
    last_third_avg = sum(c['throughput'] for c in chunks[2*third:]) / len(chunks[2*third:])
    
    print(f"\nFirst {third} chunks: {first_third_avg:.1f} apps/min (avg)")
    print(f"Middle {third} chunks: {middle_third_avg:.1f} apps/min (avg)")
    print(f"Last {len(chunks)-2*third} chunks: {last_third_avg:.1f} apps/min (avg)")
    
    first_to_middle = ((middle_third_avg - first_third_avg) / first_third_avg) * 100
    middle_to_last = ((last_third_avg - middle_third_avg) / middle_third_avg) * 100
    
    print(f"\nFirst → Middle: {first_to_middle:+.1f}%")
    print(f"Middle → Last: {middle_to_last:+.1f}%")
    print(f"Overall: {((last_third_avg - first_third_avg) / first_third_avg) * 100:+.1f}%")
    
    # Stability assessment
    print("\n" + "=" * 90)
    print("STABILITY ASSESSMENT")
    print("=" * 90)
    
    # Standard deviation
    avg_rate = overall_throughput
    variance = sum((c['throughput'] - avg_rate) ** 2 for c in chunks) / len(chunks)
    std_dev = variance ** 0.5
    cv = (std_dev / avg_rate) * 100  # Coefficient of variation
    
    print(f"\nAverage: {avg_rate:.1f} apps/min")
    print(f"Std Dev: {std_dev:.1f} apps/min")
    print(f"Coefficient of Variation: {cv:.1f}%")
    
    if cv < 5:
        print("✅ Throughput is VERY STABLE (CV < 5%)")
    elif cv < 10:
        print("✅ Throughput is STABLE (CV < 10%)")
    elif cv < 15:
        print("⚠️  Throughput is MODERATELY STABLE (CV < 15%)")
    else:
        print("❌ Throughput is UNSTABLE (CV >= 15%)")
    
    # Performance assessment
    print("\n" + "=" * 90)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 90)
    
    baseline_good = 1500  # ~1500 apps/min was target from earlier tuning
    baseline_acceptable = 1000  # Anything above 1000 is usable
    
    print(f"\nTarget baseline: {baseline_good:.0f} apps/min")
    print(f"Minimum acceptable: {baseline_acceptable:.0f} apps/min")
    print(f"Actual sustained: {overall_throughput:.1f} apps/min")
    
    if overall_throughput >= baseline_good:
        print(f"\n✅ EXCEEDS target baseline by {((overall_throughput - baseline_good) / baseline_good * 100):.1f}%")
    elif overall_throughput >= baseline_acceptable:
        print(f"\n⚠️  MEETS minimum acceptable ({((overall_throughput - baseline_acceptable) / baseline_acceptable * 100):.1f}% above floor)")
    else:
        print(f"\n❌ BELOW minimum acceptable ({((overall_throughput - baseline_acceptable) / baseline_acceptable * 100):.1f}% deficit)")
    
    # Key findings
    print("\n" + "=" * 90)
    print("🔍 KEY FINDINGS")
    print("=" * 90)
    
    findings = []
    
    if overall_decline < -20:
        findings.append("❌ Significant throughput degradation over 220k records")
    elif overall_decline < -5:
        findings.append("⚠️  Moderate throughput degradation (-5% to -20%)")
    else:
        findings.append("✅ Minimal or no throughput degradation")
    
    if cv < 10:
        findings.append("✅ Throughput is stable and predictable")
    else:
        findings.append("❌ Throughput is variable and unpredictable")
    
    if overall_success == 100:
        findings.append("✅ 100% success rate across all 220k records")
    else:
        findings.append(f"⚠️  {overall_success:.1f}% success rate ({total_failed} failures)")
    
    if last_chunk_rate > first_chunk_rate * 0.8:
        findings.append("✅ Late chunks maintain good speed (>80% of early speed)")
    elif last_chunk_rate > first_chunk_rate * 0.6:
        findings.append("⚠️  Late chunks slowing down (60-80% of early speed)")
    else:
        findings.append("❌ Late chunks severely degraded (<60% of early speed)")
    
    for finding in findings:
        print(f"\n{finding}")
    
    # Recommendations
    print("\n" + "=" * 90)
    print("📋 RECOMMENDATIONS")
    print("=" * 90)
    
    if overall_decline < -30:
        print("\n1. URGENT: Investigate database performance under load")
        print("   → Profile SQL Server: CPU, I/O, lock contention")
        print("   → Check index fragmentation on destination tables")
        print("   → Consider table partitioning for large tables")
        print("   → Review stats: ARE duplicate detection queries slowing down?")
    elif overall_decline < -10:
        print("\n1. Investigate destination table index strategy")
        print("   → Analyze query plans for duplicate detection")
        print("   → Consider indexed views for frequently scanned columns")
        print("   → Verify statistics are up-to-date")
    
    if cv > 15:
        print("\n2. Address throughput inconsistency")
        print("   → Check for resource contention (other processes)")
        print("   → Verify network/I/O stability during run")
        print("   → Profile slow chunks vs fast chunks")
    
    if overall_throughput >= baseline_good:
        print(f"\n3. Current performance is PRODUCTION-READY")
        print(f"   → {overall_throughput:.0f} apps/min sustained")
        print(f"   → {(total_records / total_minutes / 60):.1f} records/sec")
        print(f"   → Can process ~{(1440 * overall_throughput):,.0f} records/day (24hr continuous)")
    elif overall_throughput >= baseline_acceptable:
        print(f"\n3. Performance is acceptable for moderate throughput needs")
        print(f"   → Consider additional optimization for high-volume")
    
    print("\n")

if __name__ == "__main__":
    main()
