import os
import sys


libs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
sys.path.insert(0, libs_path)
for _, directories, _ in os.walk(libs_path):
    for directory in directories:
        sys.path.insert(
            0,
            os.path.join(libs_path, directory),
        )
    break
