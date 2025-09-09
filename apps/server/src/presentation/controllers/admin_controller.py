from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from ...application.usecases.upload_usecase import UploadUseCase
from ...application.dtos.upload_dto import UploadResponse, StatsResponse
from ...infrastructure.database.sqlite_measurement_repository import SQLiteMeasurementRepository
from ...infrastructure.vector_store.chroma_vector_repository import ChromaVectorRepository

router = APIRouter(prefix="/admin", tags=["admin"])

def get_upload_usecase():
    measurement_repo = SQLiteMeasurementRepository()
    vector_repo = ChromaVectorRepository()
    return UploadUseCase(measurement_repo, vector_repo)

def get_measurement_repo():
    return SQLiteMeasurementRepository()

@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...), 
    upload_usecase: UploadUseCase = Depends(get_upload_usecase)
):
    try:
        return await upload_usecase.execute(file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.get("/stats", response_model=StatsResponse)
def get_stats(measurement_repo: SQLiteMeasurementRepository = Depends(get_measurement_repo)):
    total_measurements = measurement_repo.get_count()
    unique_floats = measurement_repo.get_unique_float_count()
    
    return StatsResponse(
        total_measurements=total_measurements,
        unique_floats=unique_floats,
        status="active"
    )