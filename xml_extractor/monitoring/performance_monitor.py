"""
Performance monitoring implementation for XML extraction system.

This module provides performance tracking and metrics collection for
benchmarking the current state of the XML extraction pipeline.
"""

import time
import logging
import psutil
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..interfaces import PerformanceMonitorInterface
from ..models import ProcessingResult


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    
    # Processing stage timings
    validation_time: float = 0.0
    parsing_time: float = 0.0
    mapping_time: float = 0.0
    insertion_time: float = 0.0
    
    # System resource metrics
    peak_memory_mb: float = 0.0
    avg_cpu_percent: float = 0.0
    
    # Throughput metrics
    records_per_second: float = 0.0
    records_per_minute: float = 0.0
    
    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor(PerformanceMonitorInterface):
    """
    Performance monitoring implementation for benchmarking XML extraction.
    
    Provides real-time metrics collection and performance analysis
    for the complete XML processing pipeline.
    """
    
    def __init__(self):
        """Initialize the performance monitor."""
        self.logger = logging.getLogger(__name__)
        self._metrics = PerformanceMetrics()
        self._is_monitoring = False
        self._monitoring_thread = None
        self._stop_monitoring_flag = threading.Event()
        
        # Resource monitoring
        self._memory_samples = []
        self._cpu_samples = []
        
        # Stage timing
        self._stage_start_times = {}
        
    def start_monitoring(self) -> None:
        """Start performance monitoring with resource tracking."""
        if self._is_monitoring:
            self.logger.warning("Performance monitoring already started")
            return
        
        self._metrics = PerformanceMetrics()
        self._metrics.start_time = datetime.now()
        self._is_monitoring = True
        self._stop_monitoring_flag.clear()
        
        # Start resource monitoring thread
        self._monitoring_thread = threading.Thread(
            target=self._monitor_resources,
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> ProcessingResult:
        """Stop monitoring and return comprehensive results."""
        if not self._is_monitoring:
            self.logger.warning("Performance monitoring not started")
            return ProcessingResult()
        
        self._metrics.end_time = datetime.now()
        self._is_monitoring = False
        self._stop_monitoring_flag.set()
        
        # Wait for monitoring thread to finish
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=1.0)
        
        # Calculate final metrics
        self._calculate_final_metrics()
        
        # Create processing result
        result = ProcessingResult(
            records_processed=self._metrics.records_processed,
            records_successful=self._metrics.records_successful,
            records_failed=self._metrics.records_failed,
            processing_time_seconds=self._get_total_processing_time(),
            performance_metrics=self._get_performance_summary()
        )
        
        self.logger.info(f"Performance monitoring stopped. Processed {result.records_processed} records "
                        f"in {result.processing_time_seconds:.2f} seconds "
                        f"({self._metrics.records_per_minute:.1f} records/min)")
        
        return result
    
    def record_metric(self, metric_name: str, value: Any) -> None:
        """Record a custom performance metric."""
        if not self._is_monitoring:
            return
        
        self._metrics.custom_metrics[metric_name] = value
        self.logger.debug(f"Recorded metric: {metric_name} = {value}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics snapshot."""
        if not self._is_monitoring:
            return {}
        
        current_time = datetime.now()
        elapsed_seconds = (current_time - self._metrics.start_time).total_seconds()
        
        # Calculate current throughput
        current_rps = self._metrics.records_processed / elapsed_seconds if elapsed_seconds > 0 else 0
        current_rpm = current_rps * 60
        
        return {
            'elapsed_time_seconds': elapsed_seconds,
            'records_processed': self._metrics.records_processed,
            'records_successful': self._metrics.records_successful,
            'records_failed': self._metrics.records_failed,
            'records_per_second': current_rps,
            'records_per_minute': current_rpm,
            'current_memory_mb': self._get_current_memory_mb(),
            'peak_memory_mb': self._metrics.peak_memory_mb,
            'avg_cpu_percent': self._get_avg_cpu_percent(),
            'custom_metrics': self._metrics.custom_metrics.copy()
        }
    
    def start_stage(self, stage_name: str) -> None:
        """Start timing a processing stage."""
        self._stage_start_times[stage_name] = time.time()
    
    def end_stage(self, stage_name: str) -> float:
        """End timing a processing stage and return duration."""
        if stage_name not in self._stage_start_times:
            return 0.0
        
        duration = time.time() - self._stage_start_times[stage_name]
        
        # Update stage timing in metrics
        if stage_name == 'validation':
            self._metrics.validation_time += duration
        elif stage_name == 'parsing':
            self._metrics.parsing_time += duration
        elif stage_name == 'mapping':
            self._metrics.mapping_time += duration
        elif stage_name == 'insertion':
            self._metrics.insertion_time += duration
        
        del self._stage_start_times[stage_name]
        return duration
    
    def record_processing_result(self, success: bool) -> None:
        """Record the result of processing a single record."""
        self._metrics.records_processed += 1
        if success:
            self._metrics.records_successful += 1
        else:
            self._metrics.records_failed += 1
    
    def _monitor_resources(self) -> None:
        """Monitor system resources in background thread."""
        while not self._stop_monitoring_flag.is_set():
            try:
                # Sample memory usage
                memory_mb = self._get_current_memory_mb()
                self._memory_samples.append(memory_mb)
                
                # Update peak memory
                if memory_mb > self._metrics.peak_memory_mb:
                    self._metrics.peak_memory_mb = memory_mb
                
                # Sample CPU usage
                cpu_percent = psutil.cpu_percent(interval=None)
                self._cpu_samples.append(cpu_percent)
                
                # Sleep for sampling interval
                self._stop_monitoring_flag.wait(0.5)  # Sample every 500ms
                
            except Exception as e:
                self.logger.warning(f"Error monitoring resources: {e}")
                break
    
    def _get_current_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
    
    def _get_avg_cpu_percent(self) -> float:
        """Get average CPU usage percentage."""
        if not self._cpu_samples:
            return 0.0
        return sum(self._cpu_samples) / len(self._cpu_samples)
    
    def _calculate_final_metrics(self) -> None:
        """Calculate final performance metrics."""
        total_time = self._get_total_processing_time()
        
        if total_time > 0:
            self._metrics.records_per_second = self._metrics.records_processed / total_time
            self._metrics.records_per_minute = self._metrics.records_per_second * 60
        
        if self._cpu_samples:
            self._metrics.avg_cpu_percent = self._get_avg_cpu_percent()
    
    def _get_total_processing_time(self) -> float:
        """Get total processing time in seconds."""
        if not self._metrics.start_time or not self._metrics.end_time:
            return 0.0
        return (self._metrics.end_time - self._metrics.start_time).total_seconds()
    
    def _get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        total_time = self._get_total_processing_time()
        
        return {
            'total_processing_time_seconds': total_time,
            'records_per_second': self._metrics.records_per_second,
            'records_per_minute': self._metrics.records_per_minute,
            'success_rate_percent': (self._metrics.records_successful / self._metrics.records_processed * 100) 
                                   if self._metrics.records_processed > 0 else 0.0,
            
            # Stage timing breakdown
            'stage_timings': {
                'validation_time_seconds': self._metrics.validation_time,
                'parsing_time_seconds': self._metrics.parsing_time,
                'mapping_time_seconds': self._metrics.mapping_time,
                'insertion_time_seconds': self._metrics.insertion_time,
                'validation_percent': (self._metrics.validation_time / total_time * 100) if total_time > 0 else 0,
                'parsing_percent': (self._metrics.parsing_time / total_time * 100) if total_time > 0 else 0,
                'mapping_percent': (self._metrics.mapping_time / total_time * 100) if total_time > 0 else 0,
                'insertion_percent': (self._metrics.insertion_time / total_time * 100) if total_time > 0 else 0,
            },
            
            # Resource usage
            'resource_usage': {
                'peak_memory_mb': self._metrics.peak_memory_mb,
                'avg_cpu_percent': self._metrics.avg_cpu_percent,
                'memory_samples_count': len(self._memory_samples),
                'cpu_samples_count': len(self._cpu_samples),
            },
            
            # Custom metrics
            'custom_metrics': self._metrics.custom_metrics.copy()
        }
    
    def print_performance_report(self) -> None:
        """Print a detailed performance report."""
        if not self._metrics.end_time:
            print("⚠️ Performance monitoring not completed")
            return
        
        total_time = self._get_total_processing_time()
        
        print("\n" + "="*80)
        print("📊 PERFORMANCE BENCHMARK REPORT")
        print("="*80)
        
        # Overall metrics
        print(f"🕒 Processing Summary:")
        print(f"   Total Time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        print(f"   Records Processed: {self._metrics.records_processed}")
        print(f"   Success Rate: {(self._metrics.records_successful/self._metrics.records_processed*100):.1f}%")
        print(f"   Failed Records: {self._metrics.records_failed}")
        
        # Throughput metrics
        print(f"\n⚡ Throughput Metrics:")
        print(f"   Records/Second: {self._metrics.records_per_second:.2f}")
        print(f"   Records/Minute: {self._metrics.records_per_minute:.1f}")
        
        # Stage timing breakdown
        print(f"\n⏱️ Stage Timing Breakdown:")
        stages = [
            ('Validation', self._metrics.validation_time),
            ('Parsing', self._metrics.parsing_time),
            ('Mapping', self._metrics.mapping_time),
            ('Insertion', self._metrics.insertion_time)
        ]
        
        for stage_name, stage_time in stages:
            percentage = (stage_time / total_time * 100) if total_time > 0 else 0
            print(f"   {stage_name}: {stage_time:.2f}s ({percentage:.1f}%)")
        
        # Resource usage
        print(f"\n💾 Resource Usage:")
        print(f"   Peak Memory: {self._metrics.peak_memory_mb:.1f} MB")
        print(f"   Average CPU: {self._metrics.avg_cpu_percent:.1f}%")
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        
        # Check against requirements (1000+ records/minute target)
        target_rpm = 1000
        meets_target = self._metrics.records_per_minute >= target_rpm
        print(f"   Target Throughput (≥{target_rpm} rec/min): {'✅ PASS' if meets_target else '❌ FAIL'}")
        
        # Memory efficiency check (should handle 5MB XMLs without issues)
        memory_efficient = self._metrics.peak_memory_mb < 1000  # 1GB limit
        print(f"   Memory Efficiency (<1GB peak): {'✅ PASS' if memory_efficient else '❌ FAIL'}")
        
        # Success rate check
        high_success_rate = (self._metrics.records_successful / self._metrics.records_processed * 100) >= 90
        print(f"   Success Rate (≥90%): {'✅ PASS' if high_success_rate else '❌ FAIL'}")
        
        # Overall assessment
        overall_pass = meets_target and memory_efficient and high_success_rate
        print(f"\n🏆 Overall Assessment: {'✅ PRODUCTION READY' if overall_pass else '⚠️ NEEDS OPTIMIZATION'}")
        
        if not overall_pass:
            print(f"\n🔧 Optimization Recommendations:")
            if not meets_target:
                print(f"   - Optimize processing pipeline for higher throughput")
                print(f"   - Consider parallel processing implementation")
            if not memory_efficient:
                print(f"   - Implement streaming XML processing")
                print(f"   - Add memory management and garbage collection")
            if not high_success_rate:
                print(f"   - Review and fix data mapping issues")
                print(f"   - Improve error handling and recovery")