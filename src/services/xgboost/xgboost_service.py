from src.domain.features.trainings import training_builder, training_split
from src.di import SimulationServicePort
from src.services.xgboost.xgboost_context_service import XgBoostContextService

class XgboostService:
    def __init__(self, context: XgBoostContextService, simService: SimulationServicePort):
        self._context = context
        self._simService = simService


    def sync_and_get_model(self):
        ...
        #pending_simulations = self._simService.get