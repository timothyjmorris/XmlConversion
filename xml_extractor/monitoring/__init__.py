"""
Monitoring module for XML extraction system.

This module provides performance monitoring and metrics collection
for benchmarking and production monitoring.
"""

from .performance_monitor import PerformanceMonitor, PerformanceMetrics

__all__ = [
    'PerformanceMonitor',
    'PerformanceMetrics'
]