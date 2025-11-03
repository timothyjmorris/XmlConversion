# Retry Counter Implementation for Failed Records

## Overview
Implement a retry mechanism that allows transient failures to be retried a limited number of times while preventing permanent failures (bad data, schema issues) from being repeatedly processed.

## Solution: Retry Counter Column

Add a `retry_count` column to `processing_log` table to track how many times a record has failed and been retried.

### Database Schema Change

```sql
ALTER TABLE [sandbox].[processing_log]
ADD retry_count INT DEFAULT 0;
```

### Query Logic

**When fetching records to process:**
```sql
AND NOT EXISTS (
    SELECT 1 
    FROM [sandbox].[processing_log] pl 
    WHERE 
        pl.app_id = ax.app_id 
        AND (
            pl.status = 'success'
            OR (pl.status = 'failed' AND pl.retry_count >= @MaxRetries)
        )
)
```

This excludes:
- Records marked as 'success' (already processed successfully)
- Records marked as 'failed' AND have reached max retries (permanent failures)
- Allows 'failed' records with retry_count < max_retries to be reprocessed

### Configuration

Add CLI parameter:
```python
parser.add_argument("--max-retries", type=int, default=1,
                   help="Maximum number of retries for failed records (default: 1)")
```

### Implementation in process_batch()

When logging a failed record:
```python
def _log_processing_result(self, app_id: int, success: bool, failure_reason: str = None, increment_retry: bool = False) -> None:
    """
    Log processing result. If increment_retry=True and status='failed', increment retry_count.
    """
    try:
        migration_engine = MigrationEngine(self.connection_string)
        with migration_engine.get_connection() as conn:
            cursor = conn.cursor()
            
            status = 'success' if success else 'failed'
            qualified_log_table = f"[{self.target_schema}].[processing_log]"
            
            if success:
                # Clear retry count on success
                cursor.execute(f"""
                    INSERT INTO {qualified_log_table} 
                    (app_id, status, failure_reason, session_id, instance_id, instance_count, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (app_id, status, failure_reason, self.session_id, self.instance_id, self.instance_count))
            else:
                # Increment retry count on failure
                cursor.execute(f"""
                    INSERT INTO {qualified_log_table} 
                    (app_id, status, failure_reason, session_id, instance_id, instance_count, retry_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (app_id, status, failure_reason, self.session_id, self.instance_id, self.instance_count))
            
            conn.commit()
    except Exception as e:
        self.logger.warning(f"Failed to log processing result for app_id {app_id}: {e}")
```

## Benefits

1. **Transient Error Recovery**: Retries records that fail due to temporary issues (connection timeouts, locks)
2. **Permanent Failure Prevention**: Stops retrying records with permanent issues (bad data, schema violations)
3. **Audit Trail**: `retry_count` provides visibility into which records have problematic data
4. **Configurable**: `max_retries` parameter allows tuning per deployment

## Rollout Strategy

1. Add `retry_count` column (nullable initially for backward compatibility)
2. Deploy with `--max-retries 1` as default
3. Monitor failures over time to identify permanent vs transient issues
4. Adjust `max_retries` if needed based on production data
