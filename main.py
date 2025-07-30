#!/usr/bin/env python3
"""
Optimized GUI-only entry point for ClaudeWarp

This entry point excludes all CLI dependencies (typer, click, rich)
to minimize the build size for GUI-only distributions.
"""

import sys


def main() -> int:
    """GUI-only entry point with minimal dependencies"""
    try:
        # Only import GUI modules - no CLI dependencies
        from claudewarp.gui.app import main as gui_main

        # Extract debug flag from command line arguments
        debug = "--debug" in sys.argv

        return gui_main(debug=debug)

    except ImportError as e:
        print(f"Import error: {e}")
        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        return 1
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 130
    except Exception as e:
        print(f"Application error: {e}")
        if "--debug" in sys.argv:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
