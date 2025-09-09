from fastapi import APIRouter, HTTPException, Depends
from ...application.usecases.query_usecase import QueryUseCase
from ...application.dtos.upload_dto import QueryRequest, QueryResponse
from ...infrastructure.database.sqlite_measurement_repository import SQLiteMeasurementRepository
from ...infrastructure.vector_store.chroma_vector_repository import ChromaVectorRepository

router = APIRouter(prefix="/researcher", tags=["researcher"])

def get_query_usecase():
    measurement_repo = SQLiteMeasurementRepository()
    vector_repo = ChromaVectorRepository()
    return QueryUseCase(measurement_repo, vector_repo)

@router.post("/query", response_model=QueryResponse)
def query_data(
    request: QueryRequest, 
    query_usecase: QueryUseCase = Depends(get_query_usecase)
):
    try:
        return query_usecase.execute(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")