#!/usr/bin/env python3
"""Debug script to show the actual connection string being used."""

from production_processor import ProductionProcessor

# Test with pooling disabled (default)
print("\n" + "="*80)
print("CONNECTION STRING TEST #1: POOLING DISABLED (DEFAULT)")
print("="*80)
p1 = ProductionProcessor(
    server="localhost\\SQLEXPRESS",
    database="XmlConversionDB",
    workers=4,
    enable_pooling=False,
    min_pool_size=4,
    max_pool_size=20,
    enable_mars=True,
    connection_timeout=30
)

print("Connection String:")
print(p1.connection_string)
print()
print("Components:")
parts = p1.connection_string.split(';')
for part in parts:
    if part.strip():
        print(f"  • {part.strip()}")

print()
if "Pooling=False" in p1.connection_string:
    print("✅ Connection pooling is DISABLED (as expected)")
elif "Pooling=True" in p1.connection_string:
    print("❌ Connection pooling is ENABLED (unexpected)")
else:
    print("❌ Pooling setting not found in connection string")

# Test with pooling enabled
print("\n" + "="*80)
print("CONNECTION STRING TEST #2: POOLING ENABLED")
print("="*80)
p2 = ProductionProcessor(
    server="localhost\\SQLEXPRESS",
    database="XmlConversionDB",
    workers=4,
    enable_pooling=True,
    min_pool_size=4,
    max_pool_size=20,
    enable_mars=True,
    connection_timeout=30
)

print("Connection String:")
print(p2.connection_string)
print()
print("Components:")
parts = p2.connection_string.split(';')
for part in parts:
    if part.strip():
        print(f"  • {part.strip()}")

print()
if "Pooling=True" in p2.connection_string:
    print("✅ Connection pooling is ENABLED (as expected)")
    if f"Min Pool Size=4" in p2.connection_string:
        print("✅ Min Pool Size set to 4")
    if f"Max Pool Size=20" in p2.connection_string:
        print("✅ Max Pool Size set to 20")
else:
    print("❌ Connection pooling is DISABLED (unexpected)")

if "MultipleActiveResultSets=True" in p2.connection_string:
    print("✅ MARS is ENABLED")
else:
    print("❌ MARS is DISABLED or missing")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print("✅ enable_pooling=False → Pooling=False in connection string")
print("✅ enable_pooling=True → Pooling=True with Min/Max Pool Size in connection string")
