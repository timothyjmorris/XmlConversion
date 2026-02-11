#!/usr/bin/env python3
"""
Quick test to verify metrics collection fixes:
1. total_database_inserts should show actual count (not 0)
2. quality_issue_apps should contain app_id 7357 and others with warnings
"""
import json
from pathlib import Path

metrics_dir = Path("metrics")
latest_metrics = sorted(metrics_dir.glob("metrics_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

if not latest_metrics:
    print("No metrics files found!")
    exit(1)

# Check the most recent metrics file
for i, metrics_file in enumerate(latest_metrics[:5]):
    print(f"\n{'='*80}")
    print(f"File: {metrics_file.name}")
    print('='*80)
    
    with open(metrics_file, 'r') as f:
        data = json.load(f)
    
    processed = data.get('total_applications_processed', 0)
    successful = data.get('total_applications_successful', 0)
    failed = data.get('total_applications_failed', 0)
    inserts = data.get('total_database_inserts', 0)
    quality_count = data.get('quality_issue_count', 0)
    quality_apps = data.get('quality_issue_apps', [])
    
    print(f"Processed: {processed:,}")
    print(f"Successful: {successful:,}")
    print(f"Failed: {failed:,}")
    print(f"Database Inserts: {inserts:,} {'✓' if inserts > 0 else '❌ ZERO!'}")
    print(f"Quality Issues: {quality_count:,} apps")
    
    if quality_apps:
        print(f"\nQuality Issue Apps (first 10):")
        for app in quality_apps[:10]:
            app_id = app.get('app_id')
            issues = app.get('quality_issues', [])
            print(f"  - app_id {app_id}: {len(issues)} issues")
            for issue in issues[:3]:  # Show first 3 issues per app
                print(f"      {issue}")
    else:
        print("\n  ⚠️  No quality_issue_apps found (should have app_id 7357 and others)")
    
    if i == 0:  # Only show detailed breakdown for most recent
        print(f"\nFailure Summary:")
        failure_summary = data.get('failure_summary', {})
        for key, count in failure_summary.items():
            if count > 0:
                print(f"  {key}: {count}")

print("\n" + "="*80)
