from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.argo_measurement import ArgoMeasurement

class MeasurementRepository(ABC):
    @abstractmethod
    def save_batch(self, measurements: List[ArgoMeasurement]) -> None:
        pass
    
    @abstractmethod
    def get_count(self) -> int:
        pass
    
    @abstractmethod
    def get_unique_float_count(self) -> int:
        pass
    
    @abstractmethod
    def get_latest(self) -> Optional[ArgoMeasurement]:
        pass