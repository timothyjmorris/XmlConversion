"""
Processing module for XML extraction system.

This module provides parallel processing capabilities for high-throughput XML
processing with flexible batch processor implementations.
"""

from .parallel_coordinator import ParallelCoordinator, WorkItem, WorkResult

__all__ = [
    'ParallelCoordinator',
    'WorkItem', 
    'WorkResult'
]