import tempfile
import os
from fastapi import UploadFile
from ..dtos.upload_dto import UploadResponse
from ...domain.services.netcdf_processor import NetCDFProcessor
from ...domain.repositories.measurement_repository import MeasurementRepository
from ...domain.repositories.vector_repository import VectorRepository

class UploadUseCase:
    def __init__(self, measurement_repo: MeasurementRepository, vector_repo: VectorRepository):
        self.measurement_repo = measurement_repo
        self.vector_repo = vector_repo
    
    async def execute(self, file: UploadFile) -> UploadResponse:
        if not file.filename.endswith(('.nc', '.netcdf')):
            raise ValueError("Invalid file format. Only NetCDF files are allowed.")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.nc') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            if not NetCDFProcessor.validate_file(temp_file_path):
                raise ValueError("Invalid NetCDF file format.")
            
            measurements = NetCDFProcessor.extract_measurements(temp_file_path)
            
            if not measurements:
                raise ValueError("No valid measurements found in file.")
            
            self.measurement_repo.save_batch(measurements)
            self.vector_repo.store_measurements(measurements)
            
            return UploadResponse(
                message=f"Successfully processed {len(measurements)} measurements",
                measurements_count=len(measurements),
                status="completed"
            )
        finally:
            os.unlink(temp_file_path)