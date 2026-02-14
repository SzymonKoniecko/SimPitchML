from typing import Protocol
from src.generatedSimPitchMlProtos.SimPitchMl.Predict import service_pb2_grpc

class PredictServicePort(Protocol):
    """Abstrakcja dla gRPC servicer (żeby dało się łatwo mockować/testować)."""
    pass
