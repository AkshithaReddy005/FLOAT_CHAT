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
        
        if not db_results:
            return {"type": "empty", "message": "No data available for visualization"}
        
        # Determine visualization types based on query classification
        viz_data = {
            "summary": self._build_summary(db_results),
            "available_visualizations": []
        }
        
        # Always include map if we have location data
        if self._has_location_data(db_results):
            viz_data["map"] = self._build_map_data(db_results)
            viz_data["available_visualizations"].append("map")
        
        # Add depth profile if we have depth and measurement data
        if self._has_depth_data(db_results):
            viz_data["depth_profile"] = self._build_depth_profile(db_results)
            viz_data["available_visualizations"].append("depth_profile")
        
        # Add time series if we have temporal data
        if self._has_time_data(db_results):
            viz_data["time_series"] = self._build_time_series(db_results)
            viz_data["available_visualizations"].append("time_series")
        
        # Add statistical charts for analytical queries
        if query_classification.get("is_analytical", False):
            viz_data["statistics"] = self._build_statistics(db_results)
            viz_data["available_visualizations"].append("statistics")
        
        # Add distribution charts for large datasets
        if len(db_results) > 50:
            viz_data["distributions"] = self._build_distributions(db_results)
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
                point = {
                    "lat": float(r['latitude']),
                    "lon": float(r['longitude']),
                    "float_id": r['float_id'],
                    "date": r.get('date'),
                    "depth": r.get('depth'),
                    "temperature": r.get('temperature'),
                    "salinity": r.get('salinity'),
                    "pressure": r.get('pressure')
                }
                points.append(point)
        
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
                # Round depth to nearest 10m for grouping
                depth_group = round(r['depth'] / 10) * 10
                depth_groups[depth_group].append(r)
        
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
                # Use date string for grouping
                date_key = r['date'][:10] if isinstance(r['date'], str) else str(r['date'])[:10]
                date_groups[date_key].append(r)
        
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
    
    def _has_location_data(self, db_results: List[Dict]) -> bool:
        """Check if results have location data"""
        return any(r.get('latitude') is not None and r.get('longitude') is not None 
                  for r in db_results)
    
    def _has_depth_data(self, db_results: List[Dict]) -> bool:
        """Check if results have depth data"""
        return any(r.get('depth') is not None for r in db_results)
    
    def _has_time_data(self, db_results: List[Dict]) -> bool:
        """Check if results have temporal data"""
        return any(r.get('date') is not None for r in db_results)