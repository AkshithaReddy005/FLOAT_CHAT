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
        """Add ARGO measurements to vector store with comprehensive duplicate detection"""
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
                # Batch check for existing IDs
                ids_to_check = [item[1] for item in measurement_data]
                existing_results = self.collection.get(ids=ids_to_check)
                existing_ids = set(existing_results['ids']) if existing_results['ids'] else set()
                
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
                    
                    self.collection.add(
                        documents=final_documents,
                        metadatas=final_metadatas,
                        ids=final_ids
                    )
                    print("Successfully added to ChromaDB")
                elif not final_documents:
                    print("No documents to add after deduplication")
                else:
                    print(f"BLOCKING ChromaDB add due to remaining duplicates: {len(final_ids)} items, {len(set(final_ids))} unique")
                    
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
        """Create intelligent text representation with oceanographic context for better embeddings"""
        
        # Basic measurement info
        base_text = f"ARGO Float {measurement['float_id']} at latitude {measurement['latitude']:.6f}, longitude {measurement['longitude']:.6f} on {measurement['date']}"
        
        # Add depth and water layer context
        depth = measurement['depth']
        depth_category = self._categorize_depth(depth)
        base_text += f". Ocean depth: {depth:.2f}m ({depth_category} water layer)"
        
        # Add temperature with thermal characteristics
        temp = measurement['temperature']
        temp_category = self._categorize_temperature(temp)
        base_text += f". Temperature: {temp:.3f}°C ({temp_category} water)"
        
        # Add salinity with characteristics
        sal = measurement['salinity']
        sal_category = self._categorize_salinity(sal)
        base_text += f". Salinity: {sal:.3f} ({sal_category} water)"
        
        # Add pressure
        base_text += f". Pressure: {measurement['pressure']:.2f} dbar"
        
        # Add oceanographic context based on location and depth
        oceano_context = self._get_oceanographic_context(measurement)
        if oceano_context:
            base_text += f". Oceanographic characteristics: {oceano_context}"
        
        # Add seasonal context if available
        seasonal_context = self._get_seasonal_context(measurement['date'])
        if seasonal_context:
            base_text += f". {seasonal_context}"
        
        # Add water mass identification
        water_mass = self._identify_water_mass(measurement)
        if water_mass:
            base_text += f". Water mass type: {water_mass}"
        
        return base_text
    
    def _create_enhanced_metadata(self, measurement: Dict) -> Dict:
        """Create enhanced metadata with analytics features"""
        
        metadata = {
            # Basic measurement data
            "float_id": str(measurement['float_id']),
            "latitude": float(measurement['latitude']),
            "longitude": float(measurement['longitude']),
            "date": str(measurement['date']),
            "depth": float(measurement['depth']),
            "temperature": float(measurement['temperature']),
            "salinity": float(measurement['salinity']),
            "pressure": float(measurement['pressure']),
            "created_at": datetime.utcnow().isoformat(),
            
            # Enhanced analytics features
            "depth_category": self._categorize_depth(measurement['depth']),
            "temperature_category": self._categorize_temperature(measurement['temperature']),
            "salinity_category": self._categorize_salinity(measurement['salinity']),
            "water_mass_type": self._identify_water_mass(measurement),
            "oceanic_region": self._identify_oceanic_region(measurement['latitude'], measurement['longitude']),
            "season": self._get_season_from_date(measurement['date']),
            
            # Gradients and analytics hints
            "is_thermocline_depth": 50 <= measurement['depth'] <= 200,
            "is_surface_measurement": measurement['depth'] < 50,
            "is_deep_measurement": measurement['depth'] > 1000,
            "temperature_anomaly": self._calculate_temperature_anomaly(measurement),
            "salinity_gradient_zone": self._is_salinity_gradient_zone(measurement),
            
            # Visualization hints
            "suitable_for_depth_profile": True,
            "suitable_for_geographic_mapping": True,
            "suitable_for_temperature_analysis": measurement['temperature'] is not None,
            "suitable_for_salinity_analysis": measurement['salinity'] is not None
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
    
    def _generate_measurement_id(self, measurement: Dict) -> str:
        """Generate a unique ID for a measurement based on key identifying fields"""
        # Use same logic as database hash for consistency
        # Convert date to datetime if it's a string
        date_obj = measurement['date']
        if isinstance(date_obj, str):
            from datetime import datetime
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        
        # Include temperature, salinity, and pressure to make IDs more unique
        # This reduces the chance of hash collisions for measurements at same location/time/depth
        temp_val = measurement.get('temperature')
        sal_val = measurement.get('salinity')
        press_val = measurement.get('pressure')
        
        # Fixed f-string formatting issue
        key_string = (f"{measurement['float_id']}_"
                     f"{measurement['latitude']:.6f}_"
                     f"{measurement['longitude']:.6f}_"
                     f"{date_obj.isoformat()}_"
                     f"{measurement['depth']:.2f}_"
                     f"{'null' if temp_val is None else f'{temp_val:.3f}'}_"
                     f"{'null' if sal_val is None else f'{sal_val:.3f}'}_"
                     f"{'null' if press_val is None else f'{press_val:.2f}'}")
        
        # Use full hash (64 chars) for better uniqueness but take only 32 for ChromaDB compatibility
        full_hash = hashlib.sha256(key_string.encode()).hexdigest()
        return full_hash[:32]
    
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
        """Enhanced search with analytics-aware filtering"""
        try:
            # If we have specific filters (from parameter context), use them directly
            if filters:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=filters
                )
                return results
            
            # First, try enhanced search with filtering
            enhanced_results = self.enhanced_search(query, n_results)
            if enhanced_results['documents'][0]:  # If we got results
                return enhanced_results
            
            # Fallback to basic search
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
    
    def enhanced_search(self, query: str, n_results: int = 10) -> Dict:
        """Perform analytics-aware search with intelligent filtering"""
        try:
            query_lower = query.lower()
            where_filter = {}
            
            # Build intelligent filters based on query content
            
            # Depth-based filtering
            if any(word in query_lower for word in ['surface', 'shallow']):
                where_filter['is_surface_measurement'] = True
            elif any(word in query_lower for word in ['deep', 'bottom', 'abyssal']):
                where_filter['is_deep_measurement'] = True
            elif any(word in query_lower for word in ['thermocline', 'intermediate']):
                where_filter['is_thermocline_depth'] = True
            
            # Region-based filtering
            if 'arabian' in query_lower or 'mumbai' in query_lower:
                where_filter['oceanic_region'] = 'arabian_sea'
            elif 'equatorial' in query_lower:
                where_filter['oceanic_region'] = 'equatorial_indian_ocean'
            elif 'southern' in query_lower:
                where_filter['oceanic_region'] = 'southern_indian_ocean'
            elif 'western' in query_lower:
                where_filter['oceanic_region'] = 'western_indian_ocean'
            
            # Parameter-specific filtering
            if 'temperature' in query_lower and 'salinity' not in query_lower:
                where_filter['suitable_for_temperature_analysis'] = True
            elif 'salinity' in query_lower and 'temperature' not in query_lower:
                where_filter['suitable_for_salinity_analysis'] = True
            
            # Water mass filtering
            if any(word in query_lower for word in ['warm', 'hot', 'tropical']):
                where_filter['temperature_category'] = 'tropical'
            elif any(word in query_lower for word in ['cold', 'cool']):
                where_filter['temperature_category'] = 'cold'
            
            # Seasonal filtering
            seasons = ['winter', 'spring', 'summer', 'autumn']
            for season in seasons:
                if season in query_lower:
                    where_filter['season'] = season
                    break
            
            # Execute filtered search
            if where_filter:
                print(f"Enhanced search with filters: {where_filter}")
                results = self.collection.query(
                    query_texts=[query],
                    n_results=min(n_results * 2, 20),  # Get more results to filter from
                    where=where_filter
                )
                
                # If filtered search returns results, limit to requested number
                if results['documents'][0]:
                    for key in results.keys():
                        if isinstance(results[key], list) and len(results[key]) > 0:
                            results[key][0] = results[key][0][:n_results]
                    return results
            
            # If no specific filters or filtered search failed, do semantic search
            return self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
        except Exception as e:
            print(f"Enhanced search failed: {e}, falling back to basic search")
            return self.collection.query(
                query_texts=[query],
                n_results=n_results
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
                where=where_filters if where_filters else None
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