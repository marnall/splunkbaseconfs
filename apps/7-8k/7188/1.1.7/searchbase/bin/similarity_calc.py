#!/usr/bin/env python3
"""
Convenience wrapper for similarity calculator.

This allows running the calculator directly:
    python similarity_calc.py [args]

Instead of:
    python -m core.similarity.calculator [args]
"""

if __name__ == '__main__':
    import runpy
    import sys
    
    # Run the module as if it were executed with python -m
    sys.argv[0] = 'core.similarity.calculator'
    runpy.run_module('core.similarity.calculator', run_name='__main__')

