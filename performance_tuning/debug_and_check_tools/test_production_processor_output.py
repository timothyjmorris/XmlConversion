#!/usr/bin/env python3
"""Direct test of production_processor.py to see what it outputs."""

import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent

# Run production_processor.py directly
cmd = [
    sys.executable,
    str(project_root / "production_processor.py"),
    "--server", "localhost\\SQLEXPRESS",
    "--database", "XmlConversionDB",
    "--workers", "2",
    "--batch-size", "1000",
    "--log-level", "INFO"
]

print("Running production_processor.py with INFO logging...")
print(f"Command: {' '.join(cmd)}\n")

result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

print("STDOUT:")
print("=" * 80)
print(result.stdout)
print("=" * 80)

print("\nSTDERR:")
print("=" * 80)
print(result.stderr)
print("=" * 80)

print(f"\nReturn code: {result.returncode}")

# Try to parse metrics
import re
output = result.stdout + result.stderr
match = re.search(r'Overall Rate:\s*(\d+\.?\d*)\s*applications/minute', output, re.IGNORECASE)
if match:
    print(f"\n✅ Found throughput: {match.group(1)} applications/minute")
else:
    print("\n❌ Could not find throughput in output")
    
match = re.search(r'Total Applications Processed:\s*(\d+)', output, re.IGNORECASE)
if match:
    print(f"✅ Found records processed: {match.group(1)}")
else:
    print("❌ Could not find records processed")
