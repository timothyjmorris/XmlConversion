"""Stage app_XML orchestrator

Launches multiple `appxml_staging_extractor.py` workers, optionally drops the staging index once
before the load, recreates the index after, and aggregates per-worker metrics into a single
summary file.

Usage (PowerShell):
python env_prep\appxml_staging_orchestrator.py --workers 8 --batch 2000 --drop-index --metrics-dir metrics
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
PILOT = os.path.join(HERE, 'appxml_staging_extractor.py')


def ensure_dirs(log_dir, metrics_dir):
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(metrics_dir, exist_ok=True)


def launch_worker(rem, workers, batch, extra_args, log_dir, metrics_path):
    args = [sys.executable, PILOT, '--batch', str(batch), '--mod', str(workers), '--rem', str(rem), '--metrics', metrics_path]
    args += extra_args
    stdout_path = os.path.join(log_dir, f'appxml_{rem}.out')
    stderr_path = os.path.join(log_dir, f'appxml_{rem}.err')
    stdout_f = open(stdout_path, 'w', encoding='utf-8')
    stderr_f = open(stderr_path, 'w', encoding='utf-8')
    proc = subprocess.Popen(args, stdout=stdout_f, stderr=stderr_f)
    return proc, stdout_f, stderr_f


def wait_for_procs(procs):
    # procs: list of (proc, stdout_f, stderr_f)
    while procs:
        time.sleep(5)
        for p, so, se in procs[:]:
            ret = p.poll()
            if ret is not None:
                so.close(); se.close()
                procs.remove((p, so, se))


def aggregate_metrics(metrics_dir, out_path):
    agg = {'workers': [], 'total_processed': 0, 'total_duration_s': 0.0, 'collected_at': datetime.utcnow().isoformat() + 'Z'}
    for fname in sorted(os.listdir(metrics_dir)):
        if not fname.lower().endswith('.json'):
            continue
        path = os.path.join(metrics_dir, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                m = json.load(f)
            agg['workers'].append({'file': fname, 'processed': m.get('processed', 0), 'duration_s': m.get('duration_s', 0.0), 'rows_per_sec': m.get('rows_per_sec', 0.0)})
            agg['total_processed'] += m.get('processed', 0)
            agg['total_duration_s'] += m.get('duration_s', 0.0)
        except Exception:
            continue
    if agg['workers']:
        try:
            with open(out_path, 'w', encoding='utf-8') as of:
                json.dump(agg, of, indent=2)
        except Exception:
            pass
    return agg


def main(workers, batch, drop_index, recreate_index, metrics_dir, log_dir, extra_args):
    ensure_dirs(log_dir, metrics_dir)

    procs = []

    print(f"Starting {workers} workers, batch={batch}, drop_index={drop_index}, recreate_index={recreate_index}")

    for rem in range(workers):
        metrics_path = os.path.join(metrics_dir, f'appxml_{rem}.json')
        worker_args = list(extra_args)
        if drop_index and rem == 0:
            worker_args += ['--drop-index']
        proc, so, se = launch_worker(rem, workers, batch, worker_args, log_dir, metrics_path)
        procs.append((proc, so, se))

    try:
        wait_for_procs(procs)
    except KeyboardInterrupt:
        print('Interrupted: terminating workers')
        for p, so, se in procs:
            try:
                p.terminate()
            except Exception:
                pass
        raise

    print('All workers finished; aggregating metrics')
    agg = aggregate_metrics(metrics_dir, os.path.join(metrics_dir, 'appxml_aggregate.json'))
    print(f"Aggregated total_processed={agg.get('total_processed', 0)}")

    if recreate_index:
        print('Recreating staging index (single invocation)')
        args = [sys.executable, PILOT, '--batch', '1', '--recreate-index']
        subprocess.run(args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Orchestrate multiple appxml_staging_extractor.py workers')
    parser.add_argument('--workers', type=int, default=8, help='number of worker processes to launch')
    parser.add_argument('--batch', type=int, default=2000, help='batch size passed to worker')
    parser.add_argument('--drop-index', action='store_true', help='drop staging index before load (worker 0 will drop it)')
    parser.add_argument('--recreate-index', action='store_true', help='recreate staging index after load')
    parser.add_argument('--metrics-dir', type=str, default=os.path.join(ROOT, 'metrics'), help='directory to store per-worker metrics')
    parser.add_argument('--log-dir', type=str, default=os.path.join(ROOT, 'logs'), help='directory to store per-worker stdout/stderr')
    parser.add_argument('--extra', nargs=argparse.REMAINDER, help='extra args to forward to workers')

    args = parser.parse_args()
    extra = args.extra or []
    main(workers=args.workers, batch=args.batch, drop_index=args.drop_index, recreate_index=args.recreate_index, metrics_dir=args.metrics_dir, log_dir=args.log_dir, extra_args=extra)
