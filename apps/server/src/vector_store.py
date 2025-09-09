import chromadb
import os
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

class VectorStore:
    def __init__(self):
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection("argo_data")
    
    def add_measurements(self, measurements: List[Dict]):
        """Add ARGO measurements to vector store"""
        documents = []
        metadatas = []
        ids = []
        
        for i, measurement in enumerate(measurements):
            # Create text representation for embedding
            doc_text = f"ARGO Float {measurement['float_id']} at lat {measurement['latitude']}, lon {measurement['longitude']} on {measurement['date']}. Depth: {measurement['depth']}m, Temperature: {measurement['temperature']}°C, Salinity: {measurement['salinity']}, Pressure: {measurement['pressure']} dbar"
            
            documents.append(doc_text)
            metadatas.append({
                "float_id": measurement['float_id'],
                "latitude": measurement['latitude'],
                "longitude": measurement['longitude'],
                "date": str(measurement['date']),
                "depth": measurement['depth'],
                "temperature": measurement['temperature'],
                "salinity": measurement['salinity'],
                "pressure": measurement['pressure']
            })
            ids.append(f"{measurement['float_id']}_{i}")
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def search(self, query: str, n_results: int = 10):
        """Search for relevant measurements"""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
    
    def clear_all(self):
        """Clear all data from vector store"""
        self.client.delete_collection("argo_data")
        self.collection = self.client.get_or_create_collection("argo_data")