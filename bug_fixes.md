# Bug Fix Log

## Runtime Error on Startup

**Date:** 2025-11-08

### Bug Description

The application was failing to start inside its Docker container, throwing a `RuntimeError: There is no current event loop in thread 'MainThread'`.

The root cause was that the `pyrogram` library attempts to access the `asyncio` event loop as soon as it is imported. In a standard script, this happens before the application has a chance to configure or initialize the event loop, leading to a crash. Previous attempts to fix this by installing `uvloop` at the top of the script were insufficient because the import order still caused a race condition.

### The Launcher Script Solution

A more robust solution was implemented to ensure the `asyncio` event loop is correctly configured *before* any part of the application, especially `pyrogram`, is imported.

1.  **Created `launch.py`:** A new entry point script, `launch.py`, was created in the root directory. Its sole initial responsibility is to set the appropriate `asyncio` event loop policy for the operating system. Only after the policy is set does it proceed to import the bot's modules and start the application.

2.  **Simplified `bot/__main__.py`:** The original entry point was simplified to a small script that adds the project's root directory to the system path and then calls the `launch.py` script. This maintains the `python -m bot` command structure while ensuring the correct startup sequence.

3.  **Removed `uvloop`:** To avoid potential conflicts and simplify the environment, the `uvloop` dependency was removed from `requirements.txt`. The default `asyncio` event loop is now used.

4.  **Updated `Dockerfile`:** The `Dockerfile` was updated to use `python3 launch.py` as its `CMD`, making the new launcher the official entry point for the container.

This approach guarantees that the event loop is ready before any library can try to access it, definitively resolving the startup error.

### Timeline

-   **2025-11-08:** Bug was reported and investigated.
-   **2025-11-08:** Initial fixes were attempted (`uvloop.install()`, updating `update.py`) but did not resolve the underlying import-order issue.
-   **2025-11-08:** Root cause was correctly identified as an import-time event loop conflict with Pyrogram.
-   **2025-11-08:** The robust launcher script solution was implemented and tested.
