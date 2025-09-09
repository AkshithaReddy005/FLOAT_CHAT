
from ..dtos.upload_dto import QueryRequest, QueryResponse, ArgoMeasurementDTO
from ...domain.repositories.measurement_repository import MeasurementRepository
from ...domain.repositories.vector_repository import VectorRepository

class QueryUseCase:
    def __init__(self, measurement_repo: MeasurementRepository, vector_repo: VectorRepository):
        self.measurement_repo = measurement_repo
        self.vector_repo = vector_repo
    
    def execute(self, request: QueryRequest) -> QueryResponse:
        search_results = self.vector_repo.search(request.query, limit=20)
        
        if not search_results:
            return QueryResponse(
                results=[],
                message="No relevant data found for your query."
            )
        
        # Convert raw search results to ArgoMeasurementDTO
        formatted_results = []
        for result in search_results:
            if isinstance(result, dict):
                # Ensure all required fields are present and properly typed
                dto_data = {
                    'float_id': str(result.get('float_id', '')),
                    'latitude': float(result.get('latitude', 0.0)),
                    'longitude': float(result.get('longitude', 0.0)),
                    'date': str(result.get('date', '')),
                    'depth': float(result.get('depth', 0.0)),
                    'temperature': float(result.get('temperature', 0.0)),
                    'salinity': float(result.get('salinity', 0.0)),
                    'pressure': float(result.get('pressure', 0.0))
                }
                formatted_results.append(ArgoMeasurementDTO(**dto_data))
            else:
                # If result is an ArgoMeasurement object
                formatted_results.append(ArgoMeasurementDTO(**result.to_dto_dict()))
        
        latest_measurement = self.measurement_repo.get_latest()
        last_update = latest_measurement.created_at if latest_measurement else "No data available"
        
        return QueryResponse(
            results=formatted_results,
            message=f"Found {len(formatted_results)} relevant measurements. Data current as of {last_update}"
        )