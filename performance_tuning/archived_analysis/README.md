# Archived Analysis Documents

This folder contains detailed analysis and investigation documents from the performance optimization phases. These are reference documents that explain the technical findings, investigation results, and architectural decisions.

## Document Organization

### Connection Pooling Investigation
- **POOLING_REGRESSION_ANALYSIS.md** - Root cause analysis of pooling regression (-29% on SQLExpress)
- **POOLING_TEST_PLAN.md** - Diagnostic framework and test plan for pooling issues
- **CONNECTION_POOLING_INVESTIGATION.md** - Full investigation document
- **SUMMARY_CONNECTION_POOLING.md** - Quick reference summary

### Architecture & Design
- **ARCHITECTURE_CONNECTIONS_EXPLAINED.md** - System architecture explanation
- **BENCHMARK_GUIDE.md** - Guide to benchmarking performance

### Detailed Analysis
- **BENCHMARK_PARALLEL_ANALYSIS.md** - Analysis of parallel processing performance
- **README_PHASE2_2_POOLING_INVESTIGATION.md** - Phase II.2 investigation summary

## When to Use

- **Troubleshooting performance:** See POOLING_TEST_PLAN.md
- **Understanding architecture:** See ARCHITECTURE_CONNECTIONS_EXPLAINED.md
- **Root cause analysis:** See POOLING_REGRESSION_ANALYSIS.md
- **Setting up benchmarking:** See BENCHMARK_GUIDE.md

## Key Findings (Summary)

- Connection pooling disabled by default on SQLExpress (local I/O bottleneck)
- Pooling available as option for SQL Server Dev/Prod (network latency benefit)
- Parallel processing architecture: each worker has independent connections
- Bottleneck identified as I/O, not connections or CPU

## See Also

- For active performance tuning: See `../phase_2_investigation/`
- For environment-specific setup: See `../environment_setup/`
- For test modules: See `../test_modules/`
- For benchmarking: See `../benchmarks/`
