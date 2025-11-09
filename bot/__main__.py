#!/usr/bin/env python3
import os
import sys

# This just redirects to the launcher
if __name__ == "__main__":
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from launch import main
    import asyncio
    asyncio.run(main())
