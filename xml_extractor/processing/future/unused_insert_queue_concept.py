"""
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Python InsertQueue for multiprocessing - REVERTED, sweet idea, but...
Found out multiprocessing.Manager().Queue() has too much overhead for our use case,
making the entire Phase II.3b architecture slower (47% slower in testing).
Keeping code here to remember the approach -- didn't work for this implementation.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Python `InsertQueue` infrastructure for non-blocking architecture used by `parallel_coordinator.py`.
Allows workers to queue inserts asynchronously while background thread processes.

MULTIPROCESSING ARCHITECTURE:
=============================
The queue needs to work across process boundaries:
- Main process: Starts BackgroundInsertThread (runs as daemon thread in main process)
- Worker processes: Call _queue_mapped_data() to enqueue items

Since main process uses threading.Thread and we need cross-process access,
we use multiprocessing.Manager().Queue() which is designed for this.

Why multiprocessing.Manager().Queue()?
- Unlike queue.Queue(): Works across process boundaries
- Unlike multiprocessing.Queue(): More flexible, works with daemon threads in manager context
- Thread-safe: Multiple workers can enqueue simultaneously
- Process-safe: Automatically serializes/deserializes items
"""

import multiprocessing as mp
import queue
import threading
import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InsertQueueItem:
    """Item to be inserted into queue."""
    table_name: str
    records: List[Dict[str, Any]]
    app_id: str
    timestamp: datetime
    enable_identity_insert: bool = False
    transaction_group_id: str = None  # Group items from same XML together


class InsertQueue:
    """
    Thread-safe, process-safe queue for batching database inserts.
    
    Uses multiprocessing.Manager().Queue() to enable cross-process access:
    - Main process can create and manage the queue
    - Worker processes can enqueue items
    - Background thread can dequeue items
    
    All operations are atomic and safe for concurrent access.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize queue using multiprocessing.Manager().
        
        Uses Manager().Queue() to enable cross-process access.
        Args:
            max_size: Maximum queue size (note: MP Queue doesn't enforce max_size,
                     we track it manually with stats for compatibility)
        """
        # Create a managed queue for cross-process access
        # Note: multiprocessing.Manager().Queue() doesn't support maxsize parameter
        # so we track it in stats for logging/warnings
        self.manager = mp.Manager()
        self.queue = self.manager.Queue()
        self.max_size = max_size
        self.logger = logging.getLogger('InsertQueue')
        
        # Stats are managed by the manager for process-safe access
        self.stats_lock = self.manager.Lock()
        self.stats = self.manager.dict({
            'enqueued': 0,
            'dequeued': 0,
            'failed': 0,
            'total_records': 0
        })
    
    def enqueue(self, item: InsertQueueItem) -> bool:
        """
        Non-blocking enqueue of insert item.
        
        Returns immediately (< 1ms) after adding to queue.
        This is what enables the non-blocking architecture!
        
        Args:
            item: InsertQueueItem to enqueue
            
        Returns:
            bool: True if enqueued successfully, False if queue at max capacity
        """
        try:
            # MP Queue uses put_nowait() which raises queue.Full if queue "full"
            # Since MP Queue has no maxsize, we check our manual counter
            with self.stats_lock:
                current_size = self.stats['enqueued'] - self.stats['dequeued']
                if current_size >= self.max_size:
                    self.logger.warning(
                        f"Insert queue at capacity ({current_size}/{self.max_size}), "
                        f"rejecting enqueue"
                    )
                    self.stats['failed'] += 1
                    return False
                
                # Add to stats first
                self.stats['enqueued'] += 1
                self.stats['total_records'] += len(item.records)
            
            # Now enqueue - should never block
            self.queue.put_nowait(item)
            return True
        except queue.Full:
            # Shouldn't happen with MP Queue, but handle it
            with self.stats_lock:
                self.stats['failed'] += 1
            self.logger.warning("Insert queue full (queue.Full exception)")
            return False
        except Exception as e:
            self.logger.error(f"Error enqueueing item: {e}")
            with self.stats_lock:
                self.stats['failed'] += 1
            return False
    
    def dequeue_batch(self, batch_size: int, timeout: float = 0.1) -> List[InsertQueueItem]:
        """
        Dequeue a batch of items for bulk insertion.
        
        Called by BackgroundInsertThread to get items to insert.
        Blocks until first item available or timeout.
        
        Args:
            batch_size: Number of items to dequeue
            timeout: Max time to wait for first item (seconds)
            
        Returns:
            List of InsertQueueItem (may be less than batch_size if queue empties)
        """
        batch = []
        try:
            # Block on first item with timeout
            first_item = self.queue.get(timeout=timeout)
            batch.append(first_item)
            
            # Get remaining items without blocking
            while len(batch) < batch_size:
                try:
                    item = self.queue.get_nowait()
                    batch.append(item)
                except queue.Empty:
                    break
            
            # Update stats
            with self.stats_lock:
                self.stats['dequeued'] += len(batch)
        except queue.Empty:
            # Timeout with no items - return empty batch
            pass
        except Exception as e:
            self.logger.error(f"Error dequeueing batch: {e}")
        
        return batch
    
    def get_stats(self) -> Dict[str, int]:
        """
        Return queue statistics.
        
        Returns:
            Dict with enqueued, dequeued, failed, total_records counts
        """
        with self.stats_lock:
            return dict(self.stats)
    
    def qsize(self) -> int:
        """
        Get current queue size (approximate).
        
        Note: With multiprocessing.Manager().Queue(), size is approximate
        due to inter-process communication latency.
        """
        try:
            return self.queue.qsize()
        except Exception:
            return 0
    
    def flush(self, timeout: float = 60) -> bool:
        """
        Block until queue is empty (all items dequeued).
        
        CRITICAL: Call this before processing results to ensure background thread
        has processed all queued items. Prevents data loss when background thread
        is a daemon and could be terminated prematurely.
        
        Args:
            timeout: Maximum seconds to wait for queue to empty (default 60)
            
        Returns:
            bool: True if queue emptied within timeout, False if timeout exceeded
        """
        import time
        start_time = time.time()
        
        while True:
            with self.stats_lock:
                current_size = self.stats['enqueued'] - self.stats['dequeued']
                if current_size == 0:
                    self.logger.info("Insert queue flushed successfully")
                    return True
            
            elapsed = time.time() - start_time
            if elapsed > timeout:
                remaining = self.qsize()
                self.logger.error(
                    f"Queue flush timeout after {timeout}s with {remaining} items remaining. "
                    f"Background thread may have crashed or is too slow."
                )
                return False
            
            time.sleep(0.01)  # Small sleep to avoid busy-waiting


class BackgroundInsertThread(threading.Thread):
    """
    Background thread that processes insert queue.
    
    PHASE II.3b Architecture:
    - Runs in main process as a daemon thread
    - Continuously dequeues items from InsertQueue
    - Groups by table and performs bulk inserts in dependency order
    - Allows worker processes to remain non-blocking
    
    CRITICAL: Respects FK dependency order to prevent FK violations:
    1. app_base (parent for all app_*_cc tables)
    2. contact_base (FK to app_base)
    3. app_operational_cc, app_transactional_cc, app_pricing_cc, app_solicited_cc (FK to app_base)
    4. contact_address, contact_employment (FK to contact_base)
    
    The thread manages its own database connection (created in run()),
    so we need a connection_string to initialize MigrationEngine.
    """
    
    # Define insert order to respect foreign key constraints
    TABLE_INSERT_ORDER = [
        'app_base',                # Parent table for all app_*_cc
        'contact_base',            # Parent table for contact_address and contact_employment
        'app_operational_cc',      # Child of app_base
        'app_transactional_cc',    # Child of app_base
        'app_pricing_cc',          # Child of app_base
        'app_solicited_cc',        # Child of app_base
        'contact_address',         # Child of contact_base
        'contact_employment',      # Child of contact_base
    ]
    
    def __init__(self, insert_queue: InsertQueue, batch_size: int = 500, connection_string: str = None, migration_engine=None):
        """
        Initialize background thread.
        
        Args:
            insert_queue: InsertQueue instance to consume from
            batch_size: Number of items to dequeue per batch (default 500)
            connection_string: Database connection string (required unless migration_engine provided)
            migration_engine: Optional pre-created engine (for testing); if not provided, creates from connection_string
        """
        super().__init__(daemon=True, name='BackgroundInsertThread')
        
        self.queue = insert_queue
        self.migration_engine = migration_engine
        self.connection_string = connection_string
        self.batch_size = batch_size
        self.logger = logging.getLogger('BackgroundInsertThread')
        
        self.running = False
        self.processed_batches = 0
        self.total_inserted = 0
        self.start_time = None
    
    def run(self):
        """Main thread loop - processes dequeued items in FK-safe order within transactions."""
        self.running = True
        self.start_time = datetime.now()
        
        # Create MigrationEngine if not provided (normal production case)
        if self.migration_engine is None and self.connection_string:
            from ...database.migration_engine import MigrationEngine
            self.migration_engine = MigrationEngine(self.connection_string)
        
        self.logger.info("Background insert thread started")
        
        try:
            while self.running:
                batch = self.queue.dequeue_batch(batch_size=self.batch_size)
                
                if not batch:
                    threading.Event().wait(0.01)
                    continue
                
                # Group items by transaction_group_id (each XML is one transaction group)
                # This ensures all tables for a single XML are inserted atomically
                transaction_groups = {}
                for item in batch:
                    group_id = item.transaction_group_id or item.app_id
                    if group_id not in transaction_groups:
                        transaction_groups[group_id] = []
                    transaction_groups[group_id].append(item)
                
                # Process each transaction group separately to maintain atomicity
                for group_id, group_items in transaction_groups.items():
                    try:
                        # Group items by table within this transaction
                        table_groups = {}
                        for item in group_items:
                            if item.table_name not in table_groups:
                                table_groups[item.table_name] = []
                            table_groups[item.table_name].append(item)
                        
                        # Insert tables in FK dependency order (CRITICAL for avoiding FK violations)
                        # This ensures parent records are inserted before child records
                        for table_name in self.TABLE_INSERT_ORDER:
                            if table_name not in table_groups:
                                continue  # Skip tables not in this batch
                            
                            items = table_groups[table_name]
                            try:
                                all_records = []
                                for item in items:
                                    all_records.extend(item.records)
                                
                                enable_identity = table_name in ["app_base", "contact_base"]
                                inserted = self.migration_engine.execute_bulk_insert(
                                    all_records,
                                    table_name,
                                    enable_identity_insert=enable_identity
                                )
                                self.total_inserted += inserted
                                self.logger.debug(
                                    f"Inserted {inserted} records to {table_name} "
                                    f"(transaction_group={group_id})"
                                )
                            except Exception as e:
                                self.logger.error(
                                    f"Error inserting to {table_name} in transaction {group_id}: {e}"
                                )
                                raise  # Propagate to abort this transaction group
                    except Exception as e:
                        # Log error for this transaction group but continue processing others
                        self.logger.error(f"Transaction group {group_id} failed: {e}", exc_info=True)
                
                self.processed_batches += 1
                
        except Exception as e:
            self.logger.error(f"Background thread error: {e}", exc_info=True)
        finally:
            self.logger.info(f"Background insert thread stopped")
            self.running = False
    
    def stop(self):
        """Signal thread to stop."""
        self.running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """Return thread statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        return {
            'processed_batches': self.processed_batches,
            'total_inserted': self.total_inserted,
            'elapsed_seconds': elapsed,
            'is_alive': self.is_alive()
        }