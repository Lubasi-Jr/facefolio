# Fixing `asyncpg.InterfaceError: another operation is in progress` in the Celery worker

## The symptom

`process_photo` (a sync Celery task that runs async DB code via `asyncio.run()`)
failed intermittently with:

```
asyncpg.exceptions._base.InterfaceError: cannot perform operation: another operation is in progress
```

The name of the error is misleading — it sounds like two coroutines hit the same
connection at the same time. In this codebase, that wasn't happening: every query
inside `_run_pipeline` is `await`-ed one after another on a single session, and
nothing used `asyncio.gather`/`create_task` to fan out work on that session. The
real cause was subtler and specific to combining sync Celery tasks with `asyncio.run()`.

## Why asyncpg connections are event-loop-bound

An `asyncpg.Connection` isn't just a socket wrapper — it's registered with a
specific `asyncio` event loop. Internally it uses that loop's transport/protocol
machinery (`loop.create_connection`) and schedules its waiters, timeouts, and
cancellation callbacks on that loop. The connection object effectively *is*
part of that loop's state.

This means an asyncpg connection can only safely be awaited from the loop it
was created in. Handing it to a different loop doesn't just risk a race — it's
invalid regardless of whether anything else is running concurrently, because
the connection's internal state machine (which operation is pending, which
waiter to wake) is wired to callbacks on the old loop. Using it from a new
loop leaves it unable to correctly tell "am I free?" from "is something already
running?", which surfaces as exactly this `InterfaceError`.

## Why sync-Celery + `asyncio.run()` creates the trap

Celery tasks are plain sync functions. To call async DB code from one, the
common pattern is:

```python
@celery_app.task
def process_photo(self, photo_id: str) -> None:
    asyncio.run(_process_photo(photo_id))
```

`asyncio.run()` is convenient, but it does two things every time it's called:
it **creates a brand-new event loop**, runs the coroutine to completion, and
then **closes that loop**. Every task execution gets its own, short-lived loop.

The trap: if anything that holds a live asyncpg connection is created *outside*
that boundary — e.g., at **module import time** — it gets bound to whichever
loop happened to be active the first time it was actually used, and then
silently **outlives** that loop. The next task's `asyncio.run()` spins up a
new loop, but the old object is still sitting there, still holding a
loop-A-bound connection, ready to be reused.

Celery's default (prefork) worker pool keeps a child process alive across many
task executions, so a module-level object really does persist across dozens
of `asyncio.run()` calls, each with a different, short-lived loop.

## The specific bug in this codebase

`app/db/session.py` originally had:

```python
engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

at **module scope** — evaluated once, the first time the module is imported.

`app/worker/tasks.py` imported `async_session_factory` from that module and
used it inside `_process_photo`, which runs inside `asyncio.run()`.

Sequence of events in one worker process:

1. Worker process starts, imports `tasks.py` → imports `session.py` → `engine`
   and its connection pool object are constructed (no connection opened yet).
2. Task 1 runs: `asyncio.run()` creates loop A. `_process_photo` opens a
   session, which lazily opens an asyncpg connection *on loop A*. SQLAlchemy's
   async pool (`AsyncAdaptedQueuePool`) checks it back into the pool when the
   session closes, rather than actually closing it — normal, desirable pooling
   behavior for a long-lived engine.
3. `asyncio.run()` returns, closing loop A.
4. Task 2 runs: `asyncio.run()` creates loop B — a *different* loop. But
   `async_session_factory` still points at the same `engine`/pool from step 1,
   which happily hands out the connection it pooled — the one created on
   (now-closed) loop A. Using it under loop B produces the `InterfaceError`.

This is exactly the scenario the module-level `engine` in `app/db/session.py`
sets up: correct and required for FastAPI (one process, one long-lived loop,
so the engine is only ever used from the loop it was created under), but
unsafe for a worker that manufactures a fresh loop per task.

## The fix

Keep the FastAPI side untouched — `engine` / `async_session_factory` /
`get_session()` in `app/db/session.py` are unchanged, since FastAPI's
event loop is long-lived and the module-level engine is exactly right there.

Added a factory function instead of a second module-level engine:

```python
def create_worker_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    worker_engine = create_async_engine(settings.database_url)
    worker_session_factory = async_sessionmaker(worker_engine, expire_on_commit=False)
    return worker_engine, worker_session_factory
```

`app/worker/tasks.py::_process_photo` now calls this **inside** the coroutine
that `asyncio.run()` drives, and disposes the engine in a `finally` block
before that coroutine returns:

```python
async def _process_photo(photo_id: str) -> None:
    engine, session_factory = create_worker_engine()
    try:
        async with session_factory() as session:
            ...
    finally:
        await engine.dispose()
```

Why this works: `create_async_engine()` itself doesn't touch the network or
the event loop — it just builds Python objects. The *first real connection*
gets opened lazily, the first time a query runs, which now always happens
after `asyncio.run()` has already installed the current task's loop as the
running loop. So the connection (and the pool's internal asyncio primitives)
are always created on the loop that's about to use them. `engine.dispose()`
closes every pooled connection before that same loop closes, so nothing is
left over for the next task's loop to accidentally pick up. Each task gets a
fully self-contained engine lifecycle: created, used, and torn down within a
single event loop, start to finish.

An alternative sometimes suggested is `poolclass=NullPool` on a shared
engine, so no connection is ever pooled between calls. That avoids handing
out a stale connection, but SQLAlchemy's async pool machinery still allocates
some asyncio-native objects (queues/locks) at engine-construction time, which
can themselves end up bound to whatever loop existed at import time — so it's
a narrower, more fragile fix than simply scoping engine construction to the
task. Per-task engine creation is the more robust pattern and is what's used
here.

## How to avoid this class of bug going forward

- Anything that holds a live async resource bound to an event loop —
  `asyncpg`/SQLAlchemy async connections, `aiohttp` sessions, async Redis
  clients — must be created **inside** the boundary of the loop that will use
  it, and torn down before that loop closes. Never stash such a resource at
  module scope if it will be used from more than one `asyncio.run()` call.
- A quick way to spot the risk: search for objects assigned at module scope
  that will later be `await`-ed. If the module is imported once but the code
  using it runs inside a function that calls `asyncio.run()` repeatedly, treat
  that as a red flag.
- `app/cv/` and `app/db/queries/` stay engine-agnostic (they take a `session`
  argument) precisely so this fix only had to touch where the session comes
  from, not the query functions themselves.
- If a future worker task needs to run multiple queries concurrently on
  purpose, use *separate sessions/connections* per concurrent operation
  (e.g. one `async with session_factory() as session` per `gather` branch) —
  never share one `AsyncSession`/connection across concurrent awaits, loop
  binding aside. A single asyncpg connection can only run one operation at a
  time regardless of which loop it's on.

## How to verify

1. Restart the worker: `uv run celery -A app.worker.celery_app worker --loglevel=info`
2. Upload/queue several photos back-to-back so multiple `process_photo` task
   executions run one after another in the same worker child process (the
   scenario that used to trigger the bug — it needed more than one task run
   in the same process to surface, since the pool only becomes "stale" after
   the first loop closes).
3. Confirm no `InterfaceError` / `another operation is in progress` in the
   worker logs, and that each photo's `photo.processing.completed` /
   `photo.processing.failed` log line appears with a real duration, not an
   exception.
4. `psql`: `SELECT id, status FROM photos WHERE id = '<photo_id>';` should
   show `processed` for each photo that completed successfully, and the
   `faces` table should have rows for it.
