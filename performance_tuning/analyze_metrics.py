#!/usr/bin/env python3
# tools/analyze_metrics.py
import json
import glob
import csv
import statistics
from pathlib import Path

metrics_dir = Path("metrics")
files = sorted(metrics_dir.glob("metrics_*.json"))

if not files:
    print("No metrics files found in metrics/*.json")
    raise SystemExit(1)

rows = []
for f in files:
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Skipping {f} (read failed): {e}")
        continue

    # Basic run metadata
    session = data.get("session_id") or data.get("session") or data.get("session_id", "")
    workers = data.get("workers", data.get("worker_count", None))
    batch_size = data.get("batch_size", None)
    pooling = data.get("pooling", None)
    limit = data.get("limit", None)
    enable_instrumentation = data.get("enable_instrumentation", None)

    # Safe access to batch_details -> individual_results
    parsing = []
    mapping = []
    db = []
    total_individuals = 0
    # Try new top-level 'individual_results' first (produced when --enable-instrumentation is set)
    if data.get('individual_results'):
        for r in data.get('individual_results', []):
            total_individuals += 1
            if r is None:
                continue
            if r.get("parsing_time") is not None:
                parsing.append(float(r["parsing_time"]))
            if r.get("mapping_time") is not None:
                mapping.append(float(r["mapping_time"]))
            if r.get("db_insert_time") is not None:
                db.append(float(r["db_insert_time"]))
    else:
        for b in data.get("batch_details", []):
            for r in b.get("individual_results", []):
                total_individuals += 1
                if r is None:
                    continue
                if r.get("parsing_time") is not None:
                    parsing.append(float(r["parsing_time"]))
                if r.get("mapping_time") is not None:
                    mapping.append(float(r["mapping_time"]))
                if r.get("db_insert_time") is not None:
                    db.append(float(r["db_insert_time"]))

    # Compute stats (guard for empty lists)
    def stats(arr):
        if not arr:
            return {"count":0,"avg":0,"median":0}
        return {"count": len(arr), "avg": statistics.mean(arr), "median": statistics.median(arr)}

    pstats = stats(parsing)
    mstats = stats(mapping)
    dstats = stats(db)

    # top-level throughput metrics (where present)
    perf = data.get("records_per_minute") or (data.get("overall_rate_per_minute") or data.get("records_per_minute") or 0)
    records_processed = data.get("total_applications_processed") or data.get("total_processed") or data.get("records_processed") or 0

    # compute relative shares if instrumentation present
    denom = pstats["avg"] + mstats["avg"] + dstats["avg"]
    parsing_pct = (pstats["avg"] / denom * 100) if denom>0 else 0
    mapping_pct = (mstats["avg"] / denom * 100) if denom>0 else 0
    db_pct = (dstats["avg"] / denom * 100) if denom>0 else 0
    db_over_map = (dstats["avg"] / max(1e-6, (mstats["avg"] + pstats["avg"]))) if (mstats["avg"]+pstats["avg"])>0 else float("inf") if dstats["avg"]>0 else 0

    rows.append({
        "file": str(f.name),
        "session": session,
        "workers": workers,
        "batch_size": batch_size,
        "pooling": pooling,
        "limit": limit,
        "enable_instrumentation": enable_instrumentation,
        "records_processed": records_processed,
        "throughput_rec_min": perf,
        "parsing_count": pstats["count"],
        "parsing_avg_s": round(pstats["avg"], 4),
        "parsing_median_s": round(pstats["median"], 4),
        "mapping_count": mstats["count"],
        "mapping_avg_s": round(mstats["avg"], 4),
        "mapping_median_s": round(mstats["median"], 4),
        "db_count": dstats["count"],
        "db_avg_s": round(dstats["avg"], 4),
        "db_median_s": round(dstats["median"], 4),
        "parsing_pct": round(parsing_pct, 1),
        "mapping_pct": round(mapping_pct, 1),
        "db_pct": round(db_pct, 1),
        "db_over_map_ratio": round(db_over_map, 2)
    })

# Write CSV
out_csv = Path("metrics_summary.csv")
with out_csv.open("w", newline="", encoding="utf-8") as csvfile:
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

# Print summary table
print(f"Wrote {out_csv} with {len(rows)} runs summarized.\n")
for r in rows:
    print(f"File: {r['file']} | workers={r['workers']} batch_size={r['batch_size']} pooling={r['pooling']} limit={r['limit']} throughput={r['throughput_rec_min']} rec/min")
    print(f"  parsing avg/med (s): {r['parsing_avg_s']}/{r['parsing_median_s']}  mapping avg/med (s): {r['mapping_avg_s']}/{r['mapping_median_s']}  db avg/med (s): {r['db_avg_s']}/{r['db_median_s']}")
    print(f"  shares % P/M/DB: {r['parsing_pct']}% / {r['mapping_pct']}% / {r['db_pct']}%  db/(map+parse)={r['db_over_map_ratio']}")
    print("-"*100)