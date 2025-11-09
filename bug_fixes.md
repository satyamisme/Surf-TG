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

The fix involved two steps:

1.  **Updating the `UPSTREAM_REPO` in `update.py`:** The `update.py` script was configured to pull updates from the original `weebzone/Surf-TG` repository, which would overwrite any local changes. This was changed to `https://github.com/satyamisme/Surf-TG` to prevent the fix from being overwritten.
2.  **Installing `uvloop` at startup:** The `uvloop` event loop is now explicitly installed at the very beginning of the application's entry point (`bot/__main__.py`). This ensures that `uvloop` is installed before any other `asyncio`-dependent libraries are imported, preventing the `RuntimeError`.

```python
import uvloop
uvloop.install()
```

### Timeline

- **2025-11-08:** Initial bug was reported and investigated.
- **2025-11-08:** First fix was implemented, but was overwritten by the `update.py` script.
- **2025-11-08:** The `update.py` script was fixed to point to the correct repository.
- **2025-11-08:** The `uvloop` fix was re-applied.
