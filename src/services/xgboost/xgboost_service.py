from src.generatedSimulationProtos import SimulationService
from src.services import XgBoostContextService
from src.domain.features.trainings import training_builder, training_split

class XgboostService:
    def __init__(self, context: XgBoostContextService, simService: SimulationService):
        self._context = context
        self._simService = simService


    def sync_and_get_model(self):
        ...
        #pending_simulations = self._simService.get