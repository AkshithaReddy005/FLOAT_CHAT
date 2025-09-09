import chromadb
import os
from dotenv import load_dotenv
from typing import List, Dict
from ...domain.entities.argo_measurement import ArgoMeasurement
from ...domain.repositories.vector_repository import VectorRepository

load_dotenv()

class ChromaVectorRepository(VectorRepository):
    def __init__(self):
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection("argo_data")
    
    def store_measurements(self, measurements: List[ArgoMeasurement]) -> None:
        documents = []
        metadatas = []
        ids = []
        
        for i, measurement in enumerate(measurements):
            doc_text = f"ARGO Float {measurement.float_id} at lat {measurement.latitude}, lon {measurement.longitude} on {measurement.date}. Depth: {measurement.depth}m, Temperature: {measurement.temperature}°C, Salinity: {measurement.salinity}, Pressure: {measurement.pressure} dbar"
            
            documents.append(doc_text)
            metadatas.append({
                "float_id": measurement.float_id,
                "latitude": measurement.latitude,
                "longitude": measurement.longitude,
                "date": str(measurement.date),
                "depth": measurement.depth,
                "temperature": measurement.temperature,
                "salinity": measurement.salinity,
                "pressure": measurement.pressure
            })
            ids.append(f"{measurement.float_id}_{i}")
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        if not results['documents'] or not results['metadatas']:
            return []
        
        search_results = []
        for metadata in results['metadatas'][0]:
            search_results.append({
                'float_id': metadata['float_id'],
                'latitude': metadata['latitude'],
                'longitude': metadata['longitude'],
                'date': metadata['date'],
                'depth': metadata['depth'],
                'temperature': metadata['temperature'],
                'salinity': metadata['salinity'],
                'pressure': metadata['pressure']
            })
        
        return search_results
    
    def clear_all(self) -> None:
        self.client.delete_collection("argo_data")
        self.collection = self.client.get_or_create_collection("argo_data")