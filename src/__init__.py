import sys
import os

# Magia, żeby generated importy działały
generated_dir = os.path.join(os.path.dirname(__file__), "generated")
if generated_dir not in sys.path:
    sys.path.append(generated_dir)

from src.core import config, get_logger
from src.adapters.grpc.client.simulation_engine import SimulationEngineClient

__all__ = [
    "SimulationEngineClient",
    "config",
    "get_logger",
]
