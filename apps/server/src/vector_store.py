import chromadb
import os
import hashlib
from dotenv import load_dotenv
from typing import List, Dict, Optional
from datetime import datetime

load_dotenv()

class VectorStore:
    def __init__(self):
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection("argo_data")
    
    def add_measurements(self, measurements: List[Dict], file_hash: str = None):
        """Add ARGO measurements to vector store with duplicate detection"""
        documents = []
        metadatas = []
        ids = []
        
        new_measurements_count = 0
        duplicate_count = 0
        
        for measurement in measurements:
            # Generate unique ID based on measurement content
            measurement_id = self._generate_measurement_id(measurement)
            
            # Check if this measurement already exists
            try:
                existing = self.collection.get(ids=[measurement_id])
                if existing['ids']:
                    duplicate_count += 1
                    continue  # Skip duplicate
            except Exception:
                # If get fails, assume it doesn't exist
                pass
            
            # Create text representation for embedding
            doc_text = f"ARGO Float {measurement['float_id']} at lat {measurement['latitude']:.6f}, lon {measurement['longitude']:.6f} on {measurement['date']}. Depth: {measurement['depth']:.2f}m, Temperature: {measurement['temperature']:.3f}°C, Salinity: {measurement['salinity']:.3f}, Pressure: {measurement['pressure']:.2f} dbar"
            
            documents.append(doc_text)
            metadata = {
                "float_id": str(measurement['float_id']),
                "latitude": float(measurement['latitude']),
                "longitude": float(measurement['longitude']),
                "date": str(measurement['date']),
                "depth": float(measurement['depth']),
                "temperature": float(measurement['temperature']),
                "salinity": float(measurement['salinity']),
                "pressure": float(measurement['pressure']),
                "created_at": datetime.utcnow().isoformat()
            }
            
            if file_hash:
                metadata["file_hash"] = file_hash
                
            metadatas.append(metadata)
            ids.append(measurement_id)
            new_measurements_count += 1
        
        # Add only new measurements
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        return {
            "new_measurements": new_measurements_count,
            "duplicates_skipped": duplicate_count,
            "total_processed": len(measurements)
        }
    
    def _generate_measurement_id(self, measurement: Dict) -> str:
        """Generate a unique ID for a measurement based on key identifying fields"""
        # Use same logic as database hash for consistency
        # Convert date to datetime if it's a string
        date_obj = measurement['date']
        if isinstance(date_obj, str):
            from datetime import datetime
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        
        key_string = f"{measurement['float_id']}_{measurement['latitude']:.6f}_{measurement['longitude']:.6f}_{date_obj.isoformat()}_{measurement['depth']:.2f}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    def search(self, query: str, n_results: int = 10):
        """Search for relevant measurements with error handling"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return results
        except Exception as e:
            print(f"Vector store search failed: {e}")
            # Return empty results structure
            return {
                'documents': [[]],
                'distances': [[]],
                'metadatas': [[]],
                'ids': [[]]
            }
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store collection"""
        try:
            count = self.collection.count()
            return {
                "total_measurements": count,
                "collection_name": "argo_data"
            }
        except Exception as e:
            return {
                "total_measurements": 0,
                "collection_name": "argo_data",
                "error": str(e)
            }
    
    def check_file_exists(self, file_hash: str) -> bool:
        """Check if measurements from a specific file hash already exist"""
        try:
            results = self.collection.query(
                query_texts=[""],  # Empty query to get all results
                n_results=1,
                where={"file_hash": file_hash}
            )
            return len(results['ids'][0]) > 0 if results['ids'] else False
        except Exception:
            return False
    
    def clear_all(self):
        """Clear all data from vector store"""
        try:
            # First try to delete the collection
            self.client.delete_collection("argo_data")
        except Exception as e:
            # Collection might not exist, which is fine
            print(f"Warning: Could not delete collection 'argo_data': {e}")
            pass
        
        # Create fresh collection
        self.collection = self.client.get_or_create_collection("argo_data")
        
        # Verify the collection is empty
        try:
            count = self.collection.count()
            if count > 0:
                print(f"Warning: Collection still contains {count} items after clearing")
                # Try to clear by getting all IDs and deleting them
                all_items = self.collection.get(limit=None)  # Get all items
                if all_items['ids']:
                    self.collection.delete(ids=all_items['ids'])
                    print(f"Manually deleted {len(all_items['ids'])} remaining items")
        except Exception as e:
            print(f"Warning: Could not verify collection clearing: {e}")
            pass
        
    def reinitialize(self):
        """Reinitialize the vector store with fresh connections"""
        try:
            # Close existing client if possible
            if hasattr(self, 'client'):
                del self.client
        except Exception:
            pass
            
        # Create fresh client and collection
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection("argo_data")