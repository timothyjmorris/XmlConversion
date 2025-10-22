"""
Processing module for XML extraction system.

This module provides parallel processing capabilities and coordination
for high-throughput XML processing across multiple CPU cores.
"""

from .parallel_coordinator import ParallelCoordinator, WorkItem, WorkResult

__all__ = [
    'ParallelCoordinator',
    'WorkItem', 
    'WorkResult'
]