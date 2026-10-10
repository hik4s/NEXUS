# Workers

B5 introduces asynchronous processing as a durable DB-backed job model with Redis as the preferred dispatch queue.

Architecture:

```text
HTTP/API
  ↓
BackgroundJob (PostgreSQL/SQLite)
  ↓
Redis queue (preferred)
  ↓
Worker
  ↓
Handler
  ↓
result / retry / dead-letter
```

The database remains the source of truth. If Redis is unavailable, the worker can poll queued jobs directly from the database.
