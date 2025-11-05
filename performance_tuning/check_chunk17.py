#!/usr/bin/env python3
from pathlib import Path
import json

files = sorted(Path('metrics').glob('metrics_20251105_*.json'))
data = json.load(open(files[16]))

print(f"Chunk 17 file: {files[16].name}")
print(f"App range: {data['app_id_start']} - {data['app_id_end']}")
print(f"Duration: {data['total_duration_seconds']:.1f}s")
print(f"Throughput: {data['applications_per_minute']:.1f} apps/min")
print(f"Success: {data['success_rate']:.1f}%")
print(f"Failures: {data['total_applications_failed']}")
print(f"Batch details: {len(data.get('batch_details', []))} batches")

if data.get('batch_details'):
    print("\nBatch breakdown:")
    for i, b in enumerate(data['batch_details'][:3]):
        print(f"  Batch {i+1}: {b['applications_per_minute']:.1f} apps/min")
    print("  ...")
