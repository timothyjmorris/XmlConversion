"""
Processing module for XML extraction system.

This module provides parallel and sequential processing capabilities for
high-throughput XML processing with flexible batch processor implementations.
"""

from .parallel_coordinator import ParallelCoordinator, WorkItem, WorkResult
from .sequential_processor import SequentialProcessor

__all__ = [
    'ParallelCoordinator',
    'SequentialProcessor',
    'WorkItem', 
    'WorkResult'
]