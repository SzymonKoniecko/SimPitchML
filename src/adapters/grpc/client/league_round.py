"""
Klient gRPC do serwisu LeagueRound
"""

from __future__ import annotations
from typing import Optional
import os
import grpc
from src.adapters.grpc.client.base import BaseGrpcClient
from src.generated import commonTypes_pb2