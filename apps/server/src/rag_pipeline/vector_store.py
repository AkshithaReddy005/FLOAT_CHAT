import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import os
import hashlib
from dotenv import load_dotenv
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np

load_dotenv()

# ChromaDB batch size limit - conservative limit to avoid errors
CHROMA_MAX_BATCH_SIZE = 5000

class VectorStore:
    def __init__(self):
        self.persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        # Enhanced embedding function for better scientific data representation
        self._setup_enhanced_embedding()

        # Handle embedding function conflicts
        try:
            self.collection = self.client.get_or_create_collection(
                "argo_data_enhanced",
                embedding_function=self.embedding_function
            )
            print("Using enhanced collection: argo_data_enhanced")
        except ValueError as e:
            if "embedding function" in str(e).lower():
                print("Embedding function conflict detected, creating new enhanced collection")
                # Delete old collection and create new one with enhanced embedding
                try:
                    self.client.delete_collection("argo_data_enhanced")
                except:
                    pass
                self.collection = self.client.get_or_create_collection(
                    "argo_data_enhanced",
                    embedding_function=self.embedding_function
                )
                print("Created new enhanced collection")
            else:
                raise e

    def _setup_enhanced_embedding(self):
        """Setup enhanced embedding function optimized for scientific oceanographic data"""
        try:
            # Try to use a better embedding model for scientific text if available
            # sentence-transformers models are excellent for domain-specific content
            try:
                # Use all-MiniLM-L6-v2 which balances performance and quality for scientific text
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
                print("Using enhanced SentenceTransformer embedding model: all-MiniLM-L6-v2")
            except Exception as st_error:
                print(f"SentenceTransformer not available: {st_error}")
                try:
                    # Fallback to HuggingFace embedding if available
                    self.embedding_function = embedding_functions.HuggingFaceEmbeddingFunction(
                        api_key=os.getenv("HUGGINGFACE_API_KEY"),
                        model_name="sentence-transformers/all-MiniLM-L6-v2"
                    )
                    print("Using HuggingFace embedding model: all-MiniLM-L6-v2")
                except Exception as hf_error:
                    print(f"HuggingFace embedding not available: {hf_error}")
                    # Use default ChromaDB embedding as final fallback
                    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
                    print("Using default ChromaDB embedding function")
        except Exception as e:
            print(f"Error setting up embedding function: {e}")
            self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
            print("Falling back to default ChromaDB embedding function")

        # Enhanced analytics patterns for intelligent embedding
        self.analytics_patterns = {
            'temperature_ranges': {
                'tropical': (25, 35),
                'temperate': (15, 25),
                'cold': (0, 15),
                'deep_water': (-2, 5)
            },
            'salinity_ranges': {
                'fresh': (30, 34),
                'normal': (34, 36),
                'hypersaline': (36, 40)
            },
            'depth_categories': {
                'surface': (0, 50),
                'thermocline': (50, 200),
                'intermediate': (200, 1000),
                'deep': (1000, 4000),
                'abyssal': (4000, 11000)
            },
            'oceanographic_features': {
                'upwelling_zones': ['high_productivity', 'cold_surface', 'nutrient_rich'],
                'thermocline_patterns': ['strong_gradient', 'mixed_layer', 'stratification'],
                'water_masses': ['surface_water', 'intermediate_water', 'deep_water', 'bottom_water']
            }
        }
    
    def add_measurements(self, measurements: List[Dict], file_hash: str = None):
        """Add ARGO measurements to vector store with batch processing and comprehensive duplicate detection"""
        # Ensure collection exists (handle case where collection was deleted)
        try:
            self.collection.count()
        except Exception as e:
            if "does not exists" in str(e) or "does not exist" in str(e):
                print(f"Collection missing, recreating: {e}")
                self.collection = self.client.get_or_create_collection("argo_data_enhanced")
            else:
                raise e

        if not measurements:
            return {"new_measurements": 0, "duplicates_skipped": 0, "total_processed": 0}

        # If measurements exceed batch size, process in chunks
        if len(measurements) > CHROMA_MAX_BATCH_SIZE:
            print(f"Processing {len(measurements)} measurements in batches of {CHROMA_MAX_BATCH_SIZE}")
            return self._add_measurements_in_batches(measurements, file_hash)
        else:
            # Process single batch
            return self._add_single_batch(measurements, file_hash)

    def _add_measurements_in_batches(self, measurements: List[Dict], file_hash: str = None):
        """Process measurements in batches to avoid ChromaDB batch size limits"""
        total_new = 0
        total_duplicates = 0
        total_batches = (len(measurements) + CHROMA_MAX_BATCH_SIZE - 1) // CHROMA_MAX_BATCH_SIZE

        print(f"Processing {len(measurements)} measurements in {total_batches} batches")

        for batch_num in range(total_batches):
            start_idx = batch_num * CHROMA_MAX_BATCH_SIZE
            end_idx = min(start_idx + CHROMA_MAX_BATCH_SIZE, len(measurements))
            batch = measurements[start_idx:end_idx]

            print(f"Processing batch {batch_num + 1}/{total_batches}: {len(batch)} measurements")

            try:
                batch_result = self._add_single_batch(batch, file_hash)
                total_new += batch_result.get("new_measurements", 0)
                total_duplicates += batch_result.get("duplicates_skipped", 0)

                print(f"Batch {batch_num + 1} completed: {batch_result.get('new_measurements', 0)} new, "
                      f"{batch_result.get('duplicates_skipped', 0)} duplicates")

            except Exception as e:
                print(f"Batch {batch_num + 1} failed: {e}")
                print("Warning: Vector store operation failed for this batch, but processing continues")
                # Count failed batch measurements as duplicates to not lose track
                total_duplicates += len(batch)

        print(f"Batch processing completed: {total_new} total new measurements, "
              f"{total_duplicates} total duplicates across {total_batches} batches")

        return {
            "new_measurements": total_new,
            "duplicates_skipped": total_duplicates,
            "total_processed": len(measurements)
        }

    def _add_single_batch(self, measurements: List[Dict], file_hash: str = None):
        """Process a single batch of measurements with comprehensive duplicate detection"""
        documents = []
        metadatas = []
        ids = []

        new_measurements_count = 0
        duplicate_count = 0
        batch_ids_seen = set()  # Track IDs within current batch

        # First pass: Generate all IDs and check for batch duplicates
        measurement_data = []
        batch_duplicate_details = []

        for i, measurement in enumerate(measurements):
            measurement_id = self._generate_measurement_id(measurement)

            # Debug: Log first few measurements for diagnostic purposes
            if i < 3:
                temp_debug = measurement.get('temperature')
                temp_str = f"{temp_debug:.3f}" if temp_debug is not None else "null"
                print(f"Measurement {i}: ID={measurement_id}, Float={measurement['float_id']}, "
                      f"Lat={measurement['latitude']:.6f}, Lon={measurement['longitude']:.6f}, "
                      f"Depth={measurement['depth']:.2f}, Temp={temp_str}")

            # Check for duplicates within current batch
            if measurement_id in batch_ids_seen:
                duplicate_count += 1
                batch_duplicate_details.append(f"Float {measurement['float_id']} at {measurement['latitude']:.3f},{measurement['longitude']:.3f} (ID: {measurement_id[:8]}...)")
                print(f"DUPLICATE FOUND in batch: Measurement {i} has same ID ({measurement_id}) as previous measurement")

                # Find the previous measurement with same ID for detailed comparison
                prev_measurement = None
                for prev_i, (prev_meas, prev_id) in enumerate(measurement_data):
                    if prev_id == measurement_id:
                        prev_measurement = prev_meas
                        break

                if prev_measurement:
                    print(f"  Current:  Float={measurement['float_id']}, Lat={measurement['latitude']:.6f}, Lon={measurement['longitude']:.6f}, Depth={measurement['depth']:.2f}")
                    print(f"  Previous: Float={prev_measurement['float_id']}, Lat={prev_measurement['latitude']:.6f}, Lon={prev_measurement['longitude']:.6f}, Depth={prev_measurement['depth']:.2f}")
                    print(f"  Dates: {measurement['date']} vs {prev_measurement['date']}")

                continue

            batch_ids_seen.add(measurement_id)
            measurement_data.append((measurement, measurement_id))

        if batch_duplicate_details:
            print(f"Found {len(batch_duplicate_details)} duplicates within batch: {batch_duplicate_details[:3]}{'...' if len(batch_duplicate_details) > 3 else ''}")

        # Second pass: Check against existing data in vector store
        if measurement_data:
            # Collect only truly new measurements
            new_measurement_data = []

            try:
                # Batch check for existing IDs - with collection existence check
                ids_to_check = [item[1] for item in measurement_data]
                try:
                    existing_results = self.collection.get(ids=ids_to_check)
                    existing_ids = set(existing_results['ids']) if existing_results['ids'] else set()
                except Exception as collection_error:
                    if "does not exists" in str(collection_error):
                        print(f"Collection recreated during batch check, retrying")
                        self.collection = self.client.get_or_create_collection("argo_data_enhanced")
                        existing_results = self.collection.get(ids=ids_to_check)
                        existing_ids = set(existing_results['ids']) if existing_results['ids'] else set()
                    else:
                        raise collection_error

                # Filter out existing measurements
                for measurement, measurement_id in measurement_data:
                    if measurement_id in existing_ids:
                        duplicate_count += 1
                        continue
                    new_measurement_data.append((measurement, measurement_id))

            except Exception as e:
                print(f"Batch duplicate check failed: {e}, falling back to individual checks")
                # Fallback to individual checking
                for measurement, measurement_id in measurement_data:
                    try:
                        existing = self.collection.get(ids=[measurement_id])
                        if existing['ids']:
                            duplicate_count += 1
                            continue
                    except Exception:
                        # If individual check fails, assume it doesn't exist
                        pass
                    new_measurement_data.append((measurement, measurement_id))

            # Now process only the truly new measurements
            for measurement, measurement_id in new_measurement_data:
                # Create intelligent text representation with analytics context
                doc_text = self._create_enhanced_document_text(measurement)

                documents.append(doc_text)

                # Create enhanced metadata with analytics features
                metadata = self._create_enhanced_metadata(measurement)

                if file_hash:
                    metadata["file_hash"] = file_hash

                metadatas.append(metadata)
                ids.append(measurement_id)
                new_measurements_count += 1

        # Add only new measurements with final uniqueness check
        if documents:
            try:
                # CRITICAL: Final uniqueness check and validation
                print(f"About to add {len(documents)} documents to ChromaDB")

                # Create a mapping to track uniqueness
                unique_data = {}
                duplicate_ids_found = []

                for i, id_val in enumerate(ids):
                    if id_val in unique_data:
                        duplicate_ids_found.append(id_val)
                        print(f"CRITICAL: Found duplicate ID in final batch: {id_val}")
                    else:
                        unique_data[id_val] = {
                            'document': documents[i],
                            'metadata': metadatas[i],
                            'index': i
                        }

                # Extract only unique data
                final_documents = [data['document'] for data in unique_data.values()]
                final_metadatas = [data['metadata'] for data in unique_data.values()]
                final_ids = list(unique_data.keys())

                # Log any issues found
                if duplicate_ids_found:
                    print(f"REMOVED {len(duplicate_ids_found)} duplicate IDs from final batch: {duplicate_ids_found[:5]}{'...' if len(duplicate_ids_found) > 5 else ''}")
                    duplicate_count += len(duplicate_ids_found)
                    new_measurements_count = len(final_ids)

                # Triple check: verify no duplicates in final_ids
                if len(set(final_ids)) != len(final_ids):
                    print("CRITICAL ERROR: Still have duplicates after deduplication!")
                    # Emergency deduplication
                    seen = set()
                    emergency_docs, emergency_metas, emergency_ids = [], [], []
                    for i, id_val in enumerate(final_ids):
                        if id_val not in seen:
                            seen.add(id_val)
                            emergency_docs.append(final_documents[i])
                            emergency_metas.append(final_metadatas[i])
                            emergency_ids.append(id_val)

                    final_documents, final_metadatas, final_ids = emergency_docs, emergency_metas, emergency_ids
                    print(f"Emergency deduplication reduced to {len(final_ids)} unique items")

                # Only proceed if we have data and all IDs are unique
                if final_documents and len(set(final_ids)) == len(final_ids):
                    print(f"Adding {len(final_ids)} unique documents to ChromaDB")
                    print(f"Sample IDs being added: {final_ids[:5]}{'...' if len(final_ids) > 5 else ''}")

                    # Final validation: absolutely ensure no duplicates
                    id_counter = {}
                    for id_val in final_ids:
                        id_counter[id_val] = id_counter.get(id_val, 0) + 1

                    duplicates_found = {id_val: count for id_val, count in id_counter.items() if count > 1}
                    if duplicates_found:
                        print(f"CRITICAL: Found duplicates in final_ids: {duplicates_found}")
                        # This should never happen, but if it does, we'll fix it
                        unique_final_ids = list(dict.fromkeys(final_ids))  # Preserves order, removes duplicates
                        final_documents = final_documents[:len(unique_final_ids)]
                        final_metadatas = final_metadatas[:len(unique_final_ids)]
                        final_ids = unique_final_ids
                        print(f"Corrected to {len(final_ids)} unique items")
                        # Update the actual count to reflect what we're adding
                        new_measurements_count = len(final_ids)

                    try:
                        self.collection.add(
                            documents=final_documents,
                            metadatas=final_metadatas,
                            ids=final_ids
                        )
                        print(f"Successfully added {len(final_ids)} documents to ChromaDB")
                    except Exception as add_error:
                        if "does not exists" in str(add_error) or "does not exist" in str(add_error):
                            print(f"Collection missing during add, recreating and retrying: {add_error}")
                            self.collection = self.client.get_or_create_collection("argo_data_enhanced")
                            self.collection.add(
                                documents=final_documents,
                                metadatas=final_metadatas,
                                ids=final_ids
                            )
                            print(f"Successfully added {len(final_ids)} documents to recreated ChromaDB collection")
                        else:
                            raise add_error

                        # Verify the addition worked
                        try:
                            post_add_count = self.collection.count()
                            print(f"ChromaDB collection now contains {post_add_count} total measurements")
                        except Exception as verify_e:
                            print(f"Could not verify ChromaDB count after addition: {verify_e}")

                    except Exception as add_e:
                        print(f"CRITICAL: Failed to add documents to ChromaDB: {add_e}")
                        # Reset the count since addition failed
                        new_measurements_count = 0
                        duplicate_count += len(final_ids)  # Count as duplicates since they weren't added

                elif not final_documents:
                    print("No documents to add after deduplication")
                else:
                    print(f"BLOCKING ChromaDB add due to remaining duplicates: {len(final_ids)} items, {len(set(final_ids))} unique")
                    new_measurements_count = 0
                    duplicate_count += len(documents)  # Count as duplicates since they weren't added

            except Exception as e:
                # If even this fails, try to identify the specific issue
                if "Expected IDs to be unique" in str(e):
                    print(f"ChromaDB duplicate ID error detected. Performing strict deduplication.")
                    # Remove any remaining duplicates more aggressively
                    seen_ids = set()
                    clean_documents = []
                    clean_metadatas = []
                    clean_ids = []

                    for i, id_val in enumerate(ids):
                        if id_val not in seen_ids:
                            seen_ids.add(id_val)
                            clean_documents.append(documents[i])
                            clean_metadatas.append(metadatas[i])
                            clean_ids.append(id_val)
                        else:
                            duplicate_count += 1
                            new_measurements_count -= 1

                    if clean_documents:
                        try:
                            self.collection.add(
                                documents=clean_documents,
                                metadatas=clean_metadatas,
                                ids=clean_ids
                            )
                        except Exception as final_e:
                            print(f"Final ChromaDB add attempt failed: {final_e}")
                            # Continue processing - don't block the upload
                            print("Warning: Some measurements may not have been added to vector store, but processing continues")
                else:
                    print(f"ChromaDB error: {e}")
                    print("Warning: Vector store operation failed, but processing continues")

        return {
            "new_measurements": new_measurements_count,
            "duplicates_skipped": duplicate_count,
            "total_processed": len(measurements)
        }
    
    def _create_enhanced_document_text(self, measurement: Dict) -> str:
        """Create simplified, focused document text for search relevance"""

        # SIMPLIFIED: Focus only on core searchable content
        parts = []

        # Basic measurement data
        parts.append(f"ARGO float {measurement['float_id']}")

        # Location
        lat, lon = measurement['latitude'], measurement['longitude']
        oceanic_region = self._identify_oceanic_region(lat, lon)
        parts.append(f"location {lat:.2f}°N {lon:.2f}°E {oceanic_region}")

        # Core parameters with simple categorization
        temp = measurement['temperature']
        parts.append(f"temperature {temp:.1f}°C")

        sal = measurement['salinity']
        parts.append(f"salinity {sal:.2f}")

        depth = measurement['depth']
        parts.append(f"depth {depth:.0f}m")

        # Date
        date_str = str(measurement['date'])
        parts.append(f"date {date_str}")

        # Simple threshold keywords for searchability
        if temp > 25:
            parts.append("warm hot")
        elif temp < 10:
            parts.append("cold cool")

        if depth > 1000:
            parts.append("deep")
        elif depth < 100:
            parts.append("surface shallow")

        return " ".join(parts)
    
    def _create_enhanced_metadata(self, measurement: Dict) -> Dict:
        """Create simplified metadata focusing on essential fields for filtering"""

        # SIMPLIFIED: Focus only on fields used for actual filtering and search
        metadata = {
            # Core measurement data - always needed
            "float_id": str(measurement['float_id']),
            "latitude": float(measurement['latitude']),
            "longitude": float(measurement['longitude']),
            "date": str(measurement['date']),
            "depth": float(measurement['depth']),
            "temperature": float(measurement['temperature']),
            "salinity": float(measurement['salinity']),
            "pressure": float(measurement['pressure']),

            # Essential categorization only
            "oceanic_region": str(self._identify_oceanic_region(measurement['latitude'], measurement['longitude'])),
            "depth_category": str(self._categorize_depth(measurement['depth'])),

            # Simple boolean flags for common queries
            "is_surface": True if measurement['depth'] < 100 else False,
            "is_deep": True if measurement['depth'] > 1000 else False,
            "is_warm": True if measurement['temperature'] > 25 else False,
            "is_cold": True if measurement['temperature'] < 10 else False,
        }

        return metadata
    
    def _categorize_depth(self, depth: float) -> str:
        """Categorize depth into oceanographic layers"""
        for category, (min_depth, max_depth) in self.analytics_patterns['depth_categories'].items():
            if min_depth <= depth < max_depth:
                return category
        return 'unknown'
    
    def _categorize_temperature(self, temp: float) -> str:
        """Categorize temperature into thermal zones"""
        for category, (min_temp, max_temp) in self.analytics_patterns['temperature_ranges'].items():
            if min_temp <= temp < max_temp:
                return category
        return 'unknown'
    
    def _categorize_salinity(self, sal: float) -> str:
        """Categorize salinity levels"""
        for category, (min_sal, max_sal) in self.analytics_patterns['salinity_ranges'].items():
            if min_sal <= sal < max_sal:
                return category
        return 'unknown'
    
    def _get_oceanographic_context(self, measurement: Dict) -> str:
        """Generate oceanographic context based on measurement characteristics"""
        contexts = []
        
        depth = measurement['depth']
        temp = measurement['temperature']
        sal = measurement['salinity']
        
        # Thermocline detection
        if 50 <= depth <= 200 and 10 <= temp <= 20:
            contexts.append("thermocline layer")
        
        # Mixed layer detection
        if depth < 50 and temp > 20:
            contexts.append("ocean mixed layer")
        
        # Deep water characteristics
        if depth > 1000 and temp < 5:
            contexts.append("deep ocean water")
        
        # Salinity features
        if sal > 36.5:
            contexts.append("high salinity water mass")
        elif sal < 34.0:
            contexts.append("fresh water influence")
        
        return ", ".join(contexts) if contexts else ""
    
    def _get_seasonal_context(self, date_str: str) -> str:
        """Add seasonal context to measurements"""
        try:
            if isinstance(date_str, str):
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date_obj = date_str
            
            month = date_obj.month
            if month in [12, 1, 2]:
                return "Winter season measurement"
            elif month in [3, 4, 5]:
                return "Spring season measurement"
            elif month in [6, 7, 8]:
                return "Summer season measurement"
            elif month in [9, 10, 11]:
                return "Autumn season measurement"
        except:
            pass
        return ""
    
    def _identify_water_mass(self, measurement: Dict) -> str:
        """Identify water mass based on temperature-salinity characteristics"""
        temp = measurement['temperature']
        sal = measurement['salinity']
        depth = measurement['depth']
        
        # Simplified water mass identification
        if depth < 100:
            return "surface_water"
        elif depth < 1000:
            if temp > 8 and sal > 35.0:
                return "intermediate_water_warm"
            else:
                return "intermediate_water_cool"
        else:
            return "deep_water"
    
    def _identify_oceanic_region(self, lat: float, lon: float) -> str:
        """Identify oceanic region based on coordinates"""
        # Indian Ocean focus for ARGO data
        if 10 <= lat <= 30 and 60 <= lon <= 80:
            return "arabian_sea"
        elif -10 <= lat <= 10 and 60 <= lon <= 100:
            return "equatorial_indian_ocean"
        elif -30 <= lat <= -10 and 60 <= lon <= 120:
            return "southern_indian_ocean"
        elif -15 <= lat <= 15 and 40 <= lon <= 65:
            return "western_indian_ocean"
        else:
            return "indian_ocean_general"
    
    def _get_season_from_date(self, date_str: str) -> str:
        """Extract season from date string"""
        try:
            if isinstance(date_str, str):
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                date_obj = date_str
            
            month = date_obj.month
            if month in [12, 1, 2]:
                return "winter"
            elif month in [3, 4, 5]:
                return "spring"
            elif month in [6, 7, 8]:
                return "summer"
            else:
                return "autumn"
        except:
            return "unknown"
    
    def _calculate_temperature_anomaly(self, measurement: Dict) -> str:
        """Calculate if temperature is anomalous for depth"""
        depth = measurement['depth']
        temp = measurement['temperature']
        
        # Expected temperature ranges by depth
        if depth < 50:
            expected_range = (20, 30)
        elif depth < 200:
            expected_range = (15, 25)
        elif depth < 1000:
            expected_range = (5, 15)
        else:
            expected_range = (2, 8)
        
        min_expected, max_expected = expected_range
        if temp < min_expected:
            return "cold_anomaly"
        elif temp > max_expected:
            return "warm_anomaly"
        else:
            return "normal"
    
    def _is_salinity_gradient_zone(self, measurement: Dict) -> bool:
        """Determine if measurement is in a salinity gradient zone"""
        depth = measurement['depth']
        sal = measurement['salinity']
        
        # Simplified gradient zone detection
        return 50 <= depth <= 500 and 34.5 <= sal <= 36.0

    def _get_physical_processes_context(self, measurement: Dict) -> str:
        """Identify physical oceanographic processes indicated by the measurement"""
        contexts = []
        depth = measurement['depth']
        temp = measurement['temperature']
        sal = measurement['salinity']

        # Mixing processes
        if depth < 100 and 25 <= temp <= 30:
            contexts.append("active surface mixing")

        # Stratification detection
        if 100 <= depth <= 300 and 15 <= temp <= 25:
            contexts.append("water column stratification")

        # Upwelling indicators
        if depth < 50 and temp < 20 and sal > 35:
            contexts.append("potential upwelling signature")

        # Deep water formation
        if depth > 1000 and temp < 4 and sal > 34.6:
            contexts.append("deep water mass formation")

        # Thermocline characteristics
        if 50 <= depth <= 200:
            contexts.append("thermocline dynamics")

        return ", ".join(contexts) if contexts else ""

    def _get_data_quality_context(self, measurement: Dict) -> str:
        """Provide context about data quality and measurement characteristics"""
        contexts = []

        # Temperature data quality
        temp = measurement['temperature']
        if 0 <= temp <= 40:
            contexts.append("high quality temperature data")

        # Salinity data quality
        sal = measurement['salinity']
        if 30 <= sal <= 40:
            contexts.append("reliable salinity measurements")

        # Depth coverage
        depth = measurement['depth']
        if depth < 100:
            contexts.append("surface layer coverage")
        elif depth > 1000:
            contexts.append("deep ocean coverage")

        return ", ".join(contexts) if contexts else ""

    def _get_regional_significance(self, measurement: Dict) -> str:
        """Identify regional oceanographic significance"""
        lat, lon = measurement['latitude'], measurement['longitude']
        depth = measurement['depth']
        temp = measurement['temperature']

        contexts = []

        # Arabian Sea specific features
        if 10 <= lat <= 25 and 60 <= lon <= 75:
            contexts.append("Arabian Sea monsoon influence")
            if temp > 26:
                contexts.append("warm pool dynamics")

        # Equatorial region features
        if -5 <= lat <= 5:
            contexts.append("equatorial current system")
            if depth < 200:
                contexts.append("equatorial upwelling zone")

        # Southern Ocean features
        if lat < -20:
            contexts.append("Southern Ocean water mass")
            if depth > 500:
                contexts.append("Antarctic influence")

        # Bay of Bengal characteristics
        if 5 <= lat <= 22 and 80 <= lon <= 95:
            contexts.append("Bay of Bengal dynamics")
            if measurement['salinity'] < 34.5:
                contexts.append("freshwater influence")

        return ", ".join(contexts) if contexts else ""

    def _get_latitude_zone(self, lat: float) -> str:
        """Categorize latitude into zones"""
        if lat >= 30:
            return "northern"
        elif lat >= 0:
            return "tropical_northern"
        elif lat >= -30:
            return "tropical_southern"
        else:
            return "southern"

    def _get_longitude_zone(self, lon: float) -> str:
        """Categorize longitude into Indian Ocean zones"""
        if lon < 50:
            return "western_indian"
        elif lon < 80:
            return "central_indian"
        elif lon < 100:
            return "eastern_indian"
        else:
            return "indo_pacific"

    def _calculate_density_sigma(self, measurement: Dict) -> float:
        """Calculate simplified density sigma-t"""
        # Simplified density calculation for metadata
        # Real calculation would use full equation of state
        temp = measurement['temperature']
        sal = measurement['salinity']
        # Approximate sigma-t calculation
        sigma_t = sal - 35.0 + (temp - 20.0) * (-0.2)
        return round(sigma_t, 3)

    def _get_depth_bin(self, depth: float) -> str:
        """Bin depth for better filtering"""
        if depth < 10:
            return "0-10m"
        elif depth < 50:
            return "10-50m"
        elif depth < 100:
            return "50-100m"
        elif depth < 200:
            return "100-200m"
        elif depth < 500:
            return "200-500m"
        elif depth < 1000:
            return "500-1000m"
        elif depth < 2000:
            return "1000-2000m"
        else:
            return "2000m+"

    def _get_temperature_bin(self, temp: float) -> str:
        """Bin temperature for better filtering"""
        if temp < 5:
            return "0-5°C"
        elif temp < 10:
            return "5-10°C"
        elif temp < 15:
            return "10-15°C"
        elif temp < 20:
            return "15-20°C"
        elif temp < 25:
            return "20-25°C"
        elif temp < 30:
            return "25-30°C"
        else:
            return "30°C+"

    def _get_salinity_bin(self, sal: float) -> str:
        """Bin salinity for better filtering"""
        if sal < 33:
            return "<33 PSU"
        elif sal < 34:
            return "33-34 PSU"
        elif sal < 35:
            return "34-35 PSU"
        elif sal < 36:
            return "35-36 PSU"
        elif sal < 37:
            return "36-37 PSU"
        else:
            return "37+ PSU"
    
    def _generate_measurement_id(self, measurement: Dict) -> str:
        """Generate a unique ID for a measurement based on key identifying fields"""
        try:
            # Use SAME logic as database hash for consistency
            # This MUST match ArgoMeasurement.generate_measurement_hash exactly
            date_obj = measurement['date']
            if isinstance(date_obj, str):
                from datetime import datetime
                date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))

            # Use ONLY the core fields to match database logic exactly
            key_string = f"{measurement['float_id']}_{measurement['latitude']:.6f}_{measurement['longitude']:.6f}_{date_obj.isoformat()}_{measurement['depth']:.2f}"

            # Use full hash (64 chars) and take only 32 chars to match database
            full_hash = hashlib.sha256(key_string.encode()).hexdigest()
            measurement_id = full_hash[:32]

            # Verify this matches the measurement_hash from the measurement dict if available
            if 'measurement_hash' in measurement:
                if measurement['measurement_hash'] != measurement_id:
                    print(f"WARNING: Vector store ID mismatch! Generated: {measurement_id}, Expected: {measurement['measurement_hash']}")
                    # Use the measurement_hash from the measurement to ensure consistency
                    return measurement['measurement_hash']

            return measurement_id

        except Exception as e:
            print(f"ERROR generating measurement ID: {e}")
            # Fallback to simple hash
            fallback_string = f"{measurement.get('float_id', 'unknown')}_{measurement.get('latitude', 0)}_{measurement.get('longitude', 0)}_{measurement.get('depth', 0)}"
            return hashlib.sha256(fallback_string.encode()).hexdigest()[:32]
    
    def search(self, query: str, n_results: int = 10, filters: Dict = None) -> Dict:
        """Search with optional metadata filters (legacy method)"""
        return self._search_internal(query, n_results, filters)
    
    def search_with_context(self, parameter_context, n_results: int = 10) -> Dict:
        """Search using unified parameter context for consistent filtering"""
        
        # Convert parameter context to ChromaDB filters
        chroma_filters = parameter_context.to_chroma_filters()
        
        # Use the original query for semantic search
        query_text = parameter_context.original_query
        
        return self._search_internal(query_text, n_results, chroma_filters)
    
    def _search_internal(self, query: str, n_results: int = 10, filters: Dict = None) -> Dict:
        """Simplified search: semantic search with basic metadata filtering fallback"""
        try:
            # Strategy 1: Try with filters if provided
            if filters:
                try:
                    print(f"ChromaDB search with filters: {filters}")
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results,
                        where=filters,
                        include=["documents", "metadatas", "distances"]
                    )

                    # If we got results, return them
                    if results.get('documents') and results['documents'][0]:
                        print(f"Filtered search successful: {len(results['documents'][0])} documents")
                        return results
                    else:
                        print("Filtered search returned no results, trying basic semantic search")
                except Exception as filter_error:
                    print(f"Filtered search failed: {filter_error}, trying basic semantic search")

            # Strategy 2: Basic semantic search without filters
            print("Using basic semantic search")
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            print(f"Basic search returned: {len(results['documents'][0]) if results.get('documents') and results['documents'][0] else 0} documents")
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
    
    def enhanced_search(self, query: str, n_results: int = 10) -> Dict:
        """Simplified enhanced search with basic keyword-based filtering"""
        try:
            query_lower = query.lower()

            # Simple keyword-based filters using simplified metadata
            where_filter = {}

            # Basic depth filtering
            if any(word in query_lower for word in ['surface', 'shallow']):
                where_filter['is_surface'] = True
            elif any(word in query_lower for word in ['deep', 'bottom']):
                where_filter['is_deep'] = True

            # Basic temperature filtering
            if any(word in query_lower for word in ['warm', 'hot']):
                where_filter['is_warm'] = True
            elif any(word in query_lower for word in ['cold', 'cool']):
                where_filter['is_cold'] = True

            # Region filtering
            if 'arabian' in query_lower:
                where_filter['oceanic_region'] = 'arabian_sea'
            elif 'indian' in query_lower and 'ocean' in query_lower:
                where_filter['oceanic_region'] = 'indian_ocean_general'

            # Try with simple filter if available
            if where_filter:
                print(f"Enhanced search with simple filter: {where_filter}")
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )

                if results.get('documents') and results['documents'][0]:
                    return results

            # Fallback to basic semantic search
            return self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )

        except Exception as e:
            print(f"Enhanced search failed: {e}, using basic search")
            return self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
    
    def search_by_analytics_features(self, analytics_request: Dict, n_results: int = 15) -> Dict:
        """Search specifically for data that supports certain types of analytics"""
        try:
            where_filters = {}
            
            # Filter by visualization requirements
            if analytics_request.get('needs_depth_profile'):
                where_filters['suitable_for_depth_profile'] = True
            
            if analytics_request.get('needs_geographic_mapping'):
                where_filters['suitable_for_geographic_mapping'] = True
            
            if analytics_request.get('needs_temperature_analysis'):
                where_filters['suitable_for_temperature_analysis'] = True
            
            if analytics_request.get('needs_salinity_analysis'):
                where_filters['suitable_for_salinity_analysis'] = True
            
            # Filter by specific oceanographic features
            if analytics_request.get('focus_region'):
                where_filters['oceanic_region'] = analytics_request['focus_region']
            
            if analytics_request.get('depth_category'):
                where_filters['depth_category'] = analytics_request['depth_category']
            
            if analytics_request.get('water_mass_type'):
                where_filters['water_mass_type'] = analytics_request['water_mass_type']
            
            # Build query text from analytics requirements
            query_parts = []
            if analytics_request.get('parameters'):
                query_parts.extend(analytics_request['parameters'])
            if analytics_request.get('analysis_type'):
                query_parts.append(analytics_request['analysis_type'])
            if analytics_request.get('focus_region'):
                query_parts.append(analytics_request['focus_region'])
            
            query_text = ' '.join(query_parts) if query_parts else "oceanographic measurements"
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where_filters if where_filters else None,
                include=["documents", "metadatas", "distances"]
            )
            
            return results
            
        except Exception as e:
            print(f"Analytics-based search failed: {e}")
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
                "collection_name": "argo_data_enhanced"
            }
        except Exception as e:
            return {
                "total_measurements": 0,
                "collection_name": "argo_data_enhanced",
                "error": str(e)
            }

    def verify_data_consistency(self, postgres_sample_data: List[Dict] = None) -> Dict:
        """Verify data consistency between ChromaDB and PostgreSQL database"""
        consistency_report = {
            "total_postgres_provided": 0,
            "found_in_vector_store": 0,
            "missing_in_vector_store": 0,
            "hash_mismatches": 0,
            "vector_store_total": 0,
            "consistency_percentage": 0.0,
            "issues": []
        }

        try:
            # Get vector store stats
            vector_stats = self.get_collection_stats()
            consistency_report["vector_store_total"] = vector_stats.get("total_measurements", 0)

            if postgres_sample_data and len(postgres_sample_data) > 0:
                consistency_report["total_postgres_provided"] = len(postgres_sample_data)

                found_count = 0
                missing_count = 0
                hash_mismatches = 0

                for i, row_data in enumerate(postgres_sample_data):
                    try:
                        # Extract measurement hash or generate it
                        measurement_hash = row_data.get('measurement_hash')
                        if not measurement_hash:
                            # Generate hash if not provided (fallback)
                            measurement_hash = self._generate_measurement_id(row_data)

                        # Check if exists in vector store by hash
                        try:
                            hash_search = self.collection.get(ids=[measurement_hash])
                            if hash_search and hash_search.get('ids'):
                                found_count += 1
                            else:
                                missing_count += 1
                                if i < 5:  # Log first few missing items for debugging
                                    consistency_report["issues"].append(f"Missing: Float {row_data.get('float_id')} at {row_data.get('latitude')},{row_data.get('longitude')}")
                        except Exception as search_error:
                            missing_count += 1
                            consistency_report["issues"].append(f"Search failed for hash {measurement_hash[:8]}...")

                    except Exception as row_error:
                        missing_count += 1
                        consistency_report["issues"].append(f"Row processing error: {str(row_error)[:100]}")

                consistency_report["found_in_vector_store"] = found_count
                consistency_report["missing_in_vector_store"] = missing_count
                consistency_report["hash_mismatches"] = hash_mismatches

                # Calculate consistency percentage
                if consistency_report["total_postgres_provided"] > 0:
                    consistency_report["consistency_percentage"] = (found_count / consistency_report["total_postgres_provided"]) * 100

            else:
                consistency_report["issues"].append("No PostgreSQL sample data provided for verification")

        except Exception as e:
            consistency_report["issues"].append(f"Consistency check failed: {str(e)}")

        return consistency_report
    
    def check_file_exists(self, file_hash: str) -> bool:
        """Check if measurements from a specific file hash already exist"""
        try:
            results = self.collection.query(
                query_texts=[""],  # Empty query to get all results
                n_results=1,
                where={"file_hash": file_hash},
                include=["documents", "metadatas", "distances"]
            )
            return len(results['ids'][0]) > 0 if results['ids'] else False
        except Exception:
            return False
    
    def clear_all(self):
        """Clear all data from vector store"""
        try:
            # First try to delete the collection
            self.client.delete_collection("argo_data_enhanced")
        except Exception as e:
            # Collection might not exist, which is fine
            print(f"Warning: Could not delete collection 'argo_data_enhanced': {e}")
            pass

        # Create fresh collection
        self.collection = self.client.get_or_create_collection("argo_data_enhanced", embedding_function=self.embedding_function)
        
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
        self._setup_enhanced_embedding()
        self.collection = self.client.get_or_create_collection("argo_data_enhanced", embedding_function=self.embedding_function)