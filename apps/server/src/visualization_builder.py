"""
Visualization Builder Module
Prepares data for various types of visualizations based on query results and classification.
"""

from typing import Dict, List, Any
import statistics
from collections import defaultdict


class VisualizationBuilder:
    def __init__(self):
        pass
    
    def build_visualization(self, db_results: List[Dict], query_classification: Dict) -> Dict:
        """Build comprehensive visualization data based on results and query type"""
        
        try:
            if not db_results:
                return {
                    "type": "empty", 
                    "message": "No data available for visualization", 
                    "available_visualizations": [],
                    "map": {"type": "scatter", "points": []},
                    "depth_profile": {"type": "line", "data": []}
                }
            
            # Determine visualization types based on query classification
            viz_data = {
                "summary": self._build_summary(db_results),
                "available_visualizations": []
            }
            
            # Always try to provide basic map and depth profile structures
            viz_data["map"] = {"type": "scatter", "points": []}
            viz_data["depth_profile"] = {"type": "line", "data": []}
            
            try:
                # Only include map if we have sufficient valid location data
                if self._has_valid_location_data(db_results):
                    map_data = self._build_map_data(db_results)
                    if map_data.get("total_points", 0) > 0:
                        viz_data["map"] = map_data
                        viz_data["available_visualizations"].append("map")
            except Exception as e:
                print(f"Map data building failed: {e}")
            
            try:
                # Only add depth profile if we have sufficient depth and measurement data
                if self._has_sufficient_depth_data(db_results):
                    depth_data = self._build_depth_profile(db_results)
                    if depth_data.get("data") and len(depth_data["data"]) > 0:
                        viz_data["depth_profile"] = depth_data
                        viz_data["available_visualizations"].append("depth_profile")
            except Exception as e:
                print(f"Depth profile building failed: {e}")
            
            try:
                # Only add time series if we have meaningful temporal data
                if self._has_meaningful_time_data(db_results):
                    time_data = self._build_time_series(db_results)
                    if time_data.get("data") and len(time_data["data"]) > 1:  # Need at least 2 time points
                        viz_data["time_series"] = time_data
                        viz_data["available_visualizations"].append("time_series")
            except Exception as e:
                print(f"Time series building failed: {e}")
            
            try:
                # Only add statistical charts for analytical queries with sufficient data
                if query_classification.get("is_analytical", False) and len(db_results) >= 10:
                    stats_data = self._build_statistics(db_results)
                    if stats_data:
                        viz_data["statistics"] = stats_data
                        viz_data["available_visualizations"].append("statistics")
            except Exception as e:
                print(f"Statistics building failed: {e}")
            
            return viz_data
            
        except Exception as e:
            print(f"Visualization building completely failed: {e}")
            # Return minimal safe structure
            return {
                "type": "error",
                "message": "Visualization data could not be generated",
                "available_visualizations": [],
                "map": {"type": "scatter", "points": []},
                "depth_profile": {"type": "line", "data": []}
            }
            if self._has_valid_statistics(stats_data):
                viz_data["statistics"] = stats_data
                viz_data["available_visualizations"].append("statistics")
        
        # Only add distribution charts for large datasets with meaningful spread
        if len(db_results) >= 100:  # Increased threshold for meaningful distributions
            dist_data = self._build_distributions(db_results)
            if self._has_meaningful_distributions(dist_data):
                viz_data["distributions"] = dist_data
                viz_data["available_visualizations"].append("distributions")
        
        return viz_data
    
    def _build_summary(self, db_results: List[Dict]) -> Dict:
        """Build summary statistics"""
        if not db_results:
            return {}
        
        # Basic counts
        total_measurements = len(db_results)
        unique_floats = len(set(r['float_id'] for r in db_results))
        
        # Temperature stats
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        temp_stats = self._calculate_stats(temps) if temps else {}
        
        # Salinity stats  
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        salinity_stats = self._calculate_stats(salinities) if salinities else {}
        
        # Depth stats
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        depth_stats = self._calculate_stats(depths) if depths else {}
        
        # Date range
        dates = [r['date'] for r in db_results if r['date']]
        date_range = {}
        if dates:
            # Handle both datetime objects and ISO strings
            from datetime import datetime
            parsed_dates = []
            for date in dates:
                if isinstance(date, str):
                    # Parse ISO format string
                    parsed_dates.append(datetime.fromisoformat(date.replace('Z', '+00:00')))
                else:
                    parsed_dates.append(date)
            
            if parsed_dates:
                min_date = min(parsed_dates)
                max_date = max(parsed_dates)
                date_range = {
                    "start": min_date.isoformat(),
                    "end": max_date.isoformat(),
                    "span_days": (max_date - min_date).days if len(set(parsed_dates)) > 1 else 0
                }
        
        return {
            "total_measurements": total_measurements,
            "unique_floats": unique_floats,
            "temperature": temp_stats,
            "salinity": salinity_stats,
            "depth": depth_stats,
            "date_range": date_range
        }
    
    def _build_map_data(self, db_results: List[Dict]) -> Dict:
        """Build map visualization data"""
        points = []
        
        for r in db_results:
            if r.get('latitude') is not None and r.get('longitude') is not None:
                try:
                    lat = float(r['latitude'])
                    lon = float(r['longitude'])
                    
                    # Validate coordinate ranges
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        continue
                    
                    # Only include points with at least some measurement data
                    if not any([r.get('temperature'), r.get('salinity'), r.get('pressure')]):
                        continue
                    
                    point = {
                        "lat": lat,
                        "lon": lon,
                        "float_id": str(r['float_id']),
                        "date": r.get('date'),
                        "depth": float(r['depth']) if r.get('depth') is not None else None,
                        "temperature": float(r['temperature']) if r.get('temperature') is not None else None,
                        "salinity": float(r['salinity']) if r.get('salinity') is not None else None,
                        "pressure": float(r['pressure']) if r.get('pressure') is not None else None
                    }
                    points.append(point)
                except (ValueError, TypeError):
                    # Skip invalid coordinate data
                    continue
        
        # Calculate map bounds
        if points:
            lats = [p['lat'] for p in points]
            lons = [p['lon'] for p in points]
            
            bounds = {
                "north": max(lats),
                "south": min(lats), 
                "east": max(lons),
                "west": min(lons),
                "center": {
                    "lat": sum(lats) / len(lats),
                    "lon": sum(lons) / len(lons)
                }
            }
        else:
            bounds = {}
        
        return {
            "type": "map",
            "points": points,
            "bounds": bounds,
            "total_points": len(points)
        }
    
    def _build_depth_profile(self, db_results: List[Dict]) -> Dict:
        """Build depth profile visualization"""
        
        # Group data by depth ranges for cleaner visualization
        depth_groups = defaultdict(list)
        
        for r in db_results:
            if r.get('depth') is not None:
                try:
                    depth = float(r['depth'])
                    # Skip invalid depths
                    if depth < 0 or depth > 11000:  # Deeper than Mariana Trench
                        continue
                    
                    # Only include if we have actual measurement data
                    if not any([r.get('temperature'), r.get('salinity'), r.get('pressure')]):
                        continue
                    
                    # Round depth to nearest 10m for grouping
                    depth_group = round(depth / 10) * 10
                    depth_groups[depth_group].append(r)
                except (ValueError, TypeError):
                    continue
        
        profile_data = []
        for depth in sorted(depth_groups.keys()):
            measurements = depth_groups[depth]
            
            # Calculate averages for this depth
            temps = [m['temperature'] for m in measurements if m['temperature'] is not None]
            salinities = [m['salinity'] for m in measurements if m['salinity'] is not None]
            pressures = [m['pressure'] for m in measurements if m['pressure'] is not None]
            
            profile_point = {
                "depth": depth,
                "count": len(measurements),
                "temperature": {
                    "avg": statistics.mean(temps) if temps else None,
                    "min": min(temps) if temps else None,
                    "max": max(temps) if temps else None
                },
                "salinity": {
                    "avg": statistics.mean(salinities) if salinities else None,
                    "min": min(salinities) if salinities else None,
                    "max": max(salinities) if salinities else None
                },
                "pressure": {
                    "avg": statistics.mean(pressures) if pressures else None,
                    "min": min(pressures) if pressures else None,
                    "max": max(pressures) if pressures else None
                }
            }
            profile_data.append(profile_point)
        
        return {
            "type": "depth_profile",
            "data": profile_data,
            "depth_range": {
                "min": min(profile_data, key=lambda x: x['depth'])['depth'] if profile_data else 0,
                "max": max(profile_data, key=lambda x: x['depth'])['depth'] if profile_data else 0
            }
        }
    
    def _build_time_series(self, db_results: List[Dict]) -> Dict:
        """Build time series visualization"""
        
        # Group by date for time series
        date_groups = defaultdict(list)
        
        for r in db_results:
            if r.get('date'):
                try:
                    # Only include if we have actual measurement data
                    if not any([r.get('temperature'), r.get('salinity'), r.get('pressure')]):
                        continue
                    
                    # Use date string for grouping
                    date_key = r['date'][:10] if isinstance(r['date'], str) else str(r['date'])[:10]
                    
                    # Basic date validation
                    if len(date_key) != 10 or date_key.count('-') != 2:
                        continue
                    
                    date_groups[date_key].append(r)
                except (ValueError, TypeError, AttributeError):
                    continue
        
        time_series_data = []
        for date_key in sorted(date_groups.keys()):
            measurements = date_groups[date_key]
            
            # Calculate daily averages
            temps = [m['temperature'] for m in measurements if m['temperature'] is not None]
            salinities = [m['salinity'] for m in measurements if m['salinity'] is not None]
            
            time_point = {
                "date": date_key,
                "measurements_count": len(measurements),
                "temperature_avg": statistics.mean(temps) if temps else None,
                "salinity_avg": statistics.mean(salinities) if salinities else None,
                "floats": list(set(m['float_id'] for m in measurements))
            }
            time_series_data.append(time_point)
        
        return {
            "type": "time_series",
            "data": time_series_data,
            "date_range": {
                "start": min(date_groups.keys()) if date_groups else None,
                "end": max(date_groups.keys()) if date_groups else None
            }
        }
    
    def _build_statistics(self, db_results: List[Dict]) -> Dict:
        """Build statistical analysis data"""
        
        # Parameter distributions
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        
        stats = {
            "temperature": self._calculate_detailed_stats(temps) if temps else None,
            "salinity": self._calculate_detailed_stats(salinities) if salinities else None,
            "depth": self._calculate_detailed_stats(depths) if depths else None
        }
        
        # Correlation analysis (simplified)
        correlations = {}
        if len(temps) > 10 and len(depths) > 10:
            correlations["temp_depth"] = self._simple_correlation(temps, depths)
        if len(salinities) > 10 and len(depths) > 10:
            correlations["sal_depth"] = self._simple_correlation(salinities, depths)
        
        return {
            "type": "statistics",
            "parameters": stats,
            "correlations": correlations
        }
    
    def _build_distributions(self, db_results: List[Dict]) -> Dict:
        """Build distribution histograms"""
        
        distributions = {}
        
        # Temperature distribution
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        if temps:
            distributions["temperature"] = self._create_histogram(temps, "Temperature (°C)")
        
        # Salinity distribution
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        if salinities:
            distributions["salinity"] = self._create_histogram(salinities, "Salinity")
        
        # Depth distribution
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        if depths:
            distributions["depth"] = self._create_histogram(depths, "Depth (m)")
        
        return {
            "type": "distributions",
            "histograms": distributions
        }
    
    def _calculate_stats(self, values: List[float]) -> Dict:
        """Calculate basic statistics"""
        if not values:
            return {}
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values)
        }
    
    def _calculate_detailed_stats(self, values: List[float]) -> Dict:
        """Calculate detailed statistics"""
        if not values:
            return {}
        
        stats = self._calculate_stats(values)
        if len(values) > 1:
            stats["std_dev"] = statistics.stdev(values)
            stats["variance"] = statistics.variance(values)
        
        return stats
    
    def _simple_correlation(self, x_values: List[float], y_values: List[float]) -> float:
        """Calculate simple correlation coefficient"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        try:
            return statistics.correlation(x_values, y_values)
        except:
            return 0.0
    
    def _create_histogram(self, values: List[float], label: str, bins: int = 20) -> Dict:
        """Create histogram data"""
        if not values:
            return {}
        
        min_val = min(values)
        max_val = max(values)
        bin_width = (max_val - min_val) / bins
        
        histogram = [0] * bins
        bin_centers = []
        
        for i in range(bins):
            bin_center = min_val + (i + 0.5) * bin_width
            bin_centers.append(bin_center)
        
        # Count values in each bin
        for value in values:
            bin_index = min(int((value - min_val) / bin_width), bins - 1)
            histogram[bin_index] += 1
        
        return {
            "label": label,
            "bins": bin_centers,
            "counts": histogram,
            "total_values": len(values)
        }
    
    def _has_valid_location_data(self, db_results: List[Dict]) -> bool:
        """Check if results have sufficient valid location data"""
        valid_locations = [r for r in db_results 
                          if (r.get('latitude') is not None and r.get('longitude') is not None 
                             and -90 <= float(r['latitude']) <= 90 
                             and -180 <= float(r['longitude']) <= 180)]
        return len(valid_locations) >= 2  # Need at least 2 points for meaningful map
    
    def _has_sufficient_depth_data(self, db_results: List[Dict]) -> bool:
        """Check if results have sufficient depth and measurement data"""
        depth_data = [r for r in db_results if r.get('depth') is not None and r.get('depth') >= 0]
        if len(depth_data) < 5:  # Need minimum 5 points for profile
            return False
        
        # Check if we have actual measurements at different depths
        depths = set(r['depth'] for r in depth_data)
        return len(depths) >= 3  # Need at least 3 different depths
    
    def _has_meaningful_time_data(self, db_results: List[Dict]) -> bool:
        """Check if results have meaningful temporal data"""
        dates = [r.get('date') for r in db_results if r.get('date') is not None]
        if len(dates) < 2:
            return False
        
        # Check for temporal spread - need data from at least 2 different dates
        unique_dates = set(str(date)[:10] if isinstance(date, str) else str(date)[:10] for date in dates)
        return len(unique_dates) >= 2
    
    def _has_valid_statistics(self, stats_data: Dict) -> bool:
        """Check if statistical data is meaningful"""
        if not stats_data or stats_data.get("type") != "statistics":
            return False
        
        params = stats_data.get("parameters", {})
        # Check if we have at least one parameter with valid statistics
        for param_name, param_stats in params.items():
            if param_stats and param_stats.get("count", 0) >= 10:
                return True
        
        return False
    
    def _has_meaningful_distributions(self, dist_data: Dict) -> bool:
        """Check if distribution data shows meaningful patterns"""
        if not dist_data or dist_data.get("type") != "distributions":
            return False
        
        histograms = dist_data.get("histograms", {})
        # Check if at least one histogram has meaningful data spread
        for param_name, hist_data in histograms.items():
            if hist_data and hist_data.get("total_values", 0) >= 100:
                counts = hist_data.get("counts", [])
                # Check for spread - not all data in one bin
                if len(counts) > 1 and max(counts) < sum(counts) * 0.8:
                    return True
        
        return False
    
    def _has_location_data(self, db_results: List[Dict]) -> bool:
        """Legacy method - use _has_valid_location_data instead"""
        return self._has_valid_location_data(db_results)
    
    def _has_depth_data(self, db_results: List[Dict]) -> bool:
        """Legacy method - use _has_sufficient_depth_data instead"""
        return self._has_sufficient_depth_data(db_results)
    
    def _has_time_data(self, db_results: List[Dict]) -> bool:
        """Legacy method - use _has_meaningful_time_data instead"""
        return self._has_meaningful_time_data(db_results)