#!/usr/bin/env python3
"""
Analyze chunked processing results (6x 10k records with process restart).
Compare against original 60k continuous baseline to identify degradation patterns.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def load_metrics(filepath):
    """Load metrics from JSON file."""
    with open(filepath) as f:
        return json.load(f)

def analyze_chunk(data, chunk_num):
    """Analyze a single chunk's performance."""
    batches = data.get('batch_details', [])
    if not batches:
        return None
    
    first_rate = batches[0]['applications_per_minute']
    last_rate = batches[-1]['applications_per_minute']
    decline = ((last_rate - first_rate) / first_rate) * 100
    
    # Calculate rate progression across batches
    rates = [b['applications_per_minute'] for b in batches]
    
    return {
        'chunk': chunk_num,
        'records': data['total_applications_processed'],
        'duration_min': data['total_duration_seconds'] / 60,
        'first_rate': first_rate,
        'last_rate': last_rate,
        'avg_rate': data['applications_per_minute'],
        'decline_pct': decline,
        'batches': len(batches),
        'batch_rates': rates
    }

def main():
    metrics_dir = Path("metrics")
    
    # Get most recent 6 files (should be chunked runs)
    files = sorted(metrics_dir.glob("metrics_*.json"), 
                   key=lambda x: x.stat().st_mtime)
    recent_files = files[-6:]
    
    if len(recent_files) < 6:
        print(f"⚠️  Only found {len(recent_files)} recent metrics files")
        print(f"Expected 6 files from chunked processing test")
        print(f"\nShowing most recent files:")
        for f in files[-10:]:
            print(f"  {f.name}")
        return
    
    print("=" * 80)
    print("CHUNKED PROCESSING ANALYSIS")
    print("Test: 6x 10k records with process restart between chunks")
    print("=" * 80)
    
    print(f"\nAnalyzing files:")
    for f in recent_files:
        print(f"  {f.name}")
    
    # Analyze each chunk
    chunks = []
    for i, file in enumerate(recent_files, 1):
        data = load_metrics(file)
        result = analyze_chunk(data, i)
        if result:
            chunks.append(result)
            
            print(f"\n📊 Chunk {i}:")
            print(f"   Records: {result['records']:,}")
            print(f"   Duration: {result['duration_min']:.1f} min")
            print(f"   First batch: {result['first_rate']:.1f} apps/min")
            print(f"   Last batch:  {result['last_rate']:.1f} apps/min")
            print(f"   Average:     {result['avg_rate']:.1f} apps/min")
            print(f"   Decline:     {result['decline_pct']:+.1f}%")
    
    if not chunks:
        print("❌ No valid chunk data found")
        return
    
    # Cross-chunk analysis
    print("\n" + "=" * 80)
    print("CROSS-CHUNK STARTING SPEED")
    print("=" * 80)
    
    print("\nChunk | First Batch Rate | vs Chunk 1")
    print("------|------------------|------------")
    chunk1_first = chunks[0]['first_rate']
    for c in chunks:
        decline_vs_1 = ((c['first_rate'] - chunk1_first) / chunk1_first) * 100
        print(f"  {c['chunk']}   |   {c['first_rate']:8.1f}       | {decline_vs_1:+7.1f}%")
    
    # Intra-chunk patterns
    print("\n" + "=" * 80)
    print("INTRA-CHUNK DEGRADATION")
    print("=" * 80)
    
    avg_intra_decline = sum(c['decline_pct'] for c in chunks) / len(chunks)
    print(f"\nAverage intra-chunk decline: {avg_intra_decline:+.1f}%")
    
    print("\nPer-chunk breakdown:")
    for c in chunks:
        print(f"  Chunk {c['chunk']}: {c['first_rate']:.0f} → {c['last_rate']:.0f} ({c['decline_pct']:+.1f}%)")
    
    # Overall throughput
    total_records = sum(c['records'] for c in chunks)
    total_minutes = sum(c['duration_min'] for c in chunks)
    effective_rate = total_records / total_minutes
    
    print("\n" + "=" * 80)
    print("OVERALL PERFORMANCE")
    print("=" * 80)
    print(f"\nTotal records: {total_records:,}")
    print(f"Total time: {total_minutes:.1f} minutes ({total_minutes/60:.1f} hours)")
    print(f"Effective throughput: {effective_rate:.1f} apps/min")
    
    # Comparison to baseline
    print("\n" + "=" * 80)
    print("COMPARISON TO BASELINE (60k continuous runs)")
    print("=" * 80)
    
    print("\nOriginal Baseline (Nov 2):")
    print("  848 → 353 apps/min (-58.4%)")
    print("  887 → 355 apps/min (-60.0%)")
    print("  930 → 356 apps/min (-61.7%)")
    print("  Average: -60% intra-process degradation")
    print("  Average throughput: 463 apps/min")
    
    chunk1_vs_6 = ((chunks[-1]['first_rate'] - chunks[0]['first_rate']) / 
                   chunks[0]['first_rate'] * 100)
    
    print(f"\nChunked Processing (this test):")
    print(f"  Intra-chunk: {avg_intra_decline:+.1f}% (avg)")
    print(f"  Cross-chunk starting speed: {chunk1_vs_6:+.1f}%")
    print(f"  Overall throughput: {effective_rate:.1f} apps/min")
    
    # Key findings
    print("\n" + "=" * 80)
    print("🔍 KEY FINDINGS")
    print("=" * 80)
    
    if avg_intra_decline > -20:
        print("\n✅ Intra-chunk degradation is MINIMAL")
        print("   → Process restart DOES help")
        print("   → Python internal state accumulation is a factor")
    else:
        print("\n❌ Intra-chunk degradation is STILL SIGNIFICANT")
        print("   → Process restart does NOT help enough")
        print("   → Problem is NOT primarily process state")
    
    if chunk1_vs_6 < -30:
        print("\n❌ Cross-chunk starting speed degrades SIGNIFICANTLY")
        print("   → Destination table growth is a major factor")
        print("   → Need indexing improvements or batch archiving")
    else:
        print("\n✅ Cross-chunk starting speed stays relatively stable")
        print("   → Destination tables handle growth well")
    
    if effective_rate > 700:
        print(f"\n✅ Overall throughput is GOOD ({effective_rate:.0f} apps/min)")
        print("   → Chunking strategy is viable for production")
    elif effective_rate > 600:
        print(f"\n⚠️  Overall throughput is MODERATE ({effective_rate:.0f} apps/min)")
        print("   → Some improvement over baseline, but not optimal")
    else:
        print(f"\n❌ Overall throughput still DEGRADED ({effective_rate:.0f} apps/min)")
        print("   → Additional optimizations needed")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("📋 RECOMMENDATIONS")
    print("=" * 80)
    
    if avg_intra_decline < -30:
        print("\n1. Investigate destination table indexing")
        print("   → Add composite indexes for duplicate detection queries")
        print("   → Profile actual query execution times")
    
    if chunk1_vs_6 < -30:
        print("\n2. Consider batch archiving strategy")
        print("   → Move processed records to archive tables")
        print("   → Keep working tables smaller")
    
    if avg_intra_decline > -20 and effective_rate > 600:
        print("\n3. Implement automatic process chunking")
        print("   → Restart worker processes every 10k records")
        print("   → Maintain high throughput over long runs")
        print("   → Use production_processor_optimized.py with restart logic")

if __name__ == "__main__":
    main()
