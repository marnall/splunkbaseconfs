#!/usr/bin/env python3
"""
Convenience wrapper for dump_records CLI.

This allows running the tool directly:
    python dump_records.py [args]

Instead of:
    python -m cli.dump_records [args]
"""

if __name__ == '__main__':
    import runpy
    import sys
    
    # Run the module as if it were executed with python -m
    sys.argv[0] = 'cli.dump_records'
    runpy.run_module('cli.dump_records', run_name='__main__')

