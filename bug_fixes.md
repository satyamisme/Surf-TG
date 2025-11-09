# Bug Fix Log

## Runtime Error on Startup

**Date:** 2025-11-08

### Bug Description

The application was failing to start, throwing the following error:

```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/app/bot/__main__.py", line 5, in <module>
    from pyrogram import idle
  File "/usr/local/lib/python3.12/site-packages/pyrogram/__init__.py", line 42, in <module>
    from .sync import idle, compose  # pylint: disable=wrong-import-position
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/pyrogram/sync.py", line 100, in <module>
    wrap(Methods)
  File "/usr/local/lib/python3.12/site-packages/pyrogram/sync.py", line 96, in wrap
    async_to_sync(source, name)
  File "/usr/local/lib/python3.12/site-packages/pyrogram/sync.py", line 32, in async_to_sync
    main_loop = asyncio.get_event_loop()
                ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.12/site-packages/uvloop/__init__.py", line 206, in get_event_loop
    raise RuntimeError(
RuntimeError: There is no current event loop in thread 'MainThread'.
```

This issue was caused by an incompatibility between recent versions of Python (3.10+), `asyncio`, `pyrogram`, and `uvloop`. The `pyrogram` library attempts to access the `asyncio` event loop before it has been properly initialized by `uvloop`, leading to a `RuntimeError`.

### Fix

The fix involved explicitly installing the `uvloop` event loop at the very beginning of the application's entry point (`bot/__main__.py`). By adding the following lines to the top of the file, we ensure that `uvloop` is installed before any other `asyncio`-dependent libraries are imported:

```python
import uvloop
uvloop.install()
```

### Timeline

- **2025-11-08:** Bug was reported and investigated.
- **2025-11-08:** Root cause was identified as an event loop initialization issue.
- **2025-11-08:** The fix was implemented and tested.
