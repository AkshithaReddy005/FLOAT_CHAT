from abc import ABC, abstractmethod
from typing import List, Dict
from ..entities.argo_measurement import ArgoMeasurement

class VectorRepository(ABC):
    @abstractmethod
    def store_measurements(self, measurements: List[ArgoMeasurement]) -> None:
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        pass