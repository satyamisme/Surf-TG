# Bug Fix Log

## Docker Build Failure, `config.env` Error, and Runtime Error on Startup

**Date:** 2025-11-08

### Bug Description

The application was failing to build and run for a combination of reasons:

1.  **Docker `config.env` Error:** The application was failing to start due to a Docker error: `invalid env file (config.env): variable 'API_ID ' contains whitespaces`. This was because the `config_sample.env` file contained spaces around the `=` signs, which is not allowed by Docker's `--env-file` option.

2.  **`update.py` Overwriting Fixes:** The `surf-tg.sh` script, which is the container's entry point, runs an `update.py` script that would reset the repository to an upstream fork, deleting any applied fixes on every startup.

3.  **`RuntimeError`:** The application would crash on startup with a `RuntimeError: There is no current event loop in thread 'MainThread'`. This was caused by an import order issue where `pyrogram` was imported before the `asyncio` event loop could be initialized.

### The Final Solution

A comprehensive, multi-part solution was implemented to address all of these issues.

1.  **Fixed `config_sample.env`:** The `config_sample.env` file was corrected by removing the spaces around the `=` signs. This resolves the Docker `invalid env file` error.

2.  **Fixed `update.py`:** The `update.py` script was modified to point to the user's preferred fork (`https://github.com/satyamisme/Surf-TG`), preventing the fixes from being overwritten on container startup.

3.  **Corrected Import Order in `bot/__main__.py`:** The import order in `bot/__main__.py` was corrected to ensure that `from bot import LOGGER` is called *before* any `pyrogram` imports. This triggers the event loop initialization at the correct time.

4.  **Event Loop Initialization in `bot/__init__.py`:** The `bot/__init__.py` file was modified to explicitly create and set the `asyncio` event loop at the very beginning of the script. This guarantees that a valid event loop exists before any other part of the application is loaded, definitively resolving the runtime error.

### Timeline

-   **2025-11-08:** Initial bug was reported and investigated.
-   **2025-11-08:** The Docker `config.env` error was identified as the primary cause of the webview not showing.
-   **2025-11-08:** The `update.py` script was identified as the cause of fixes being overwritten.
-   **2025-11-08:** The import order in `bot/__main__.py` was identified as the cause of the `RuntimeError`.
-   **2025-11-08:** The final, correct fix for all identified issues was implemented.
