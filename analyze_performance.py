#!/usr/bin/env python3
"""
Analyze performance degradation from metrics files
"""
import json
import sys

def analyze_metrics_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    
    print(f"\n=== Analysis of {filename} ===")
    print(f"Total Duration: {data['total_duration_seconds']:.1f} seconds ({data['total_duration_seconds']/3600:.1f} hours)")
    print(f"Total Applications: {data['total_applications_processed']:,}")
    print(f"Overall Rate: {data['applications_per_minute']:.1f} apps/min")
    if data.get('app_id_start') is not None and data.get('app_id_end') is not None:
        print(f"App ID Range: {data['app_id_start']} to {data['app_id_end']}")
    else:
        print(f"App ID Range: ALL applications")
    
    # Analyze batch performance decline
    batches = data['batch_details']
    print(f"\nBatch Performance Analysis ({len(batches)} batches):")
    print("Batch | Apps/Min | Duration | Decline from Start")
    print("------|----------|----------|-------------------")
    
    first_rate = batches[0]['applications_per_minute']
    
    # Show first 15 batches
    for i in range(min(15, len(batches))):
        batch = batches[i]
        rate = batch['applications_per_minute'] 
        duration = batch['duration_seconds']
        decline = ((rate - first_rate) / first_rate) * 100
        print(f"{i+1:5d} | {rate:8.1f} | {duration:8.1f} | {decline:+7.1f}%")
    
    if len(batches) > 15:
        print("  ... (middle batches omitted)")
        
        # Show last 5 batches
        print("\nLast 5 batches:")
        for i in range(len(batches)-5, len(batches)):
            batch = batches[i]
            rate = batch['applications_per_minute']
            decline = ((rate - first_rate) / first_rate) * 100
            print(f"{i+1:5d} | {rate:8.1f} | {batch['duration_seconds']:8.1f} | {decline:+7.1f}%")
    
    # Calculate overall decline
    last_rate = batches[-1]['applications_per_minute']
    total_decline = ((last_rate - first_rate) / first_rate) * 100
    print(f"\nOverall Performance Decline: {total_decline:+.1f}%")
    print(f"First batch: {first_rate:.1f} apps/min")
    print(f"Last batch: {last_rate:.1f} apps/min")
    
    return {
        'first_rate': first_rate,
        'last_rate': last_rate,
        'total_decline': total_decline,
        'total_time': data['total_duration_seconds'],
        'app_id_start': data.get('app_id_start'),
        'app_id_end': data.get('app_id_end')
    }

if __name__ == "__main__":
    metrics_files = [
        "metrics/metrics_20251102_230655_range_1_60000.json",
        "metrics/metrics_20251102_230657_range_60001_120000.json", 
        "metrics/metrics_20251102_230659_range_120001_180000.json"
    ]
    
    results = []
    for filename in metrics_files:
        try:
            result = analyze_metrics_file(filename)
            results.append(result)
        except Exception as e:
            print(f"Error analyzing {filename}: {e}")
    
    # Summary across all processing runs
    print("\n" + "="*60)
    print("SUMMARY ACROSS ALL PROCESSING RUNS")
    print("="*60)
    
    for result in results:
        if result['app_id_start'] is not None and result['app_id_end'] is not None:
            range_info = f"Range {result['app_id_start']}-{result['app_id_end']}"
        else:
            range_info = "All Apps"
        print(f"{range_info}: {result['first_rate']:.1f} → {result['last_rate']:.1f} apps/min ({result['total_decline']:+.1f}%)")
    
    if results:
        avg_decline = sum(r['total_decline'] for r in results) / len(results)
        total_time_hours = max(r['total_time'] for r in results) / 3600
        print(f"\nAverage decline across instances: {avg_decline:+.1f}%")
        print(f"Total processing time: {total_time_hours:.1f} hours")
        
        print(f"\nAt this rate of decline, processing 11MM records could result in:")
        print(f"- Severe performance degradation over time")
        print(f"- Potentially very low throughput by the end")
        print(f"- Need for intervention or optimization")