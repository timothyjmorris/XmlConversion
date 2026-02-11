import json
import os

def check_file(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    try:
        with open(path, 'r') as f:
            data = json.load(f)
            print(f"File: {path}")
            print(f"Total entries: {len(data)}")
            # Count unique app_ids
            app_ids = set(item['app_id'] for item in data)
            print(f"Unique App IDs: {len(app_ids)}")
            
            # Group by issue type if possible
            print("First 5 entries:")
            for item in data[:5]:
                print(f" - {item['app_id']}: {item.get('issues', [])} | {len(item.get('smell_tasks', []))} tasks")
            print("-" * 20)
    except Exception as e:
        print(f"Error reading {path}: {e}")

check_file('diagnostics/cc_smell_scan_results.json')
check_file('diagnostics/smell_scan_results.json')
