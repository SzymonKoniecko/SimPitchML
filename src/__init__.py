# src/__init__.py
import sys
import os

generated_dir = os.path.join(os.path.dirname(__file__), "generated")
if os.path.exists(generated_dir) and generated_dir not in sys.path:
    sys.path.append(generated_dir)

