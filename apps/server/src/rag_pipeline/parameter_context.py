"""
Parameter Context Module
Immutable parameter object that serves as single source of truth for all query parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json


@dataclass(frozen=True)
class ParameterContext:
    """
    Immutable parameter context that holds all extracted query parameters.
    This serves as the single source of truth for all services.
    """
    
    # Core query info
    original_query: str
    query_id: str
    session_id: Optional[str] = None
    
    # Location parameters
    location_name: Optional[str] = None
    location_bounds: Optional[Dict[str, float]] = None  # {lat_min, lat_max, lon_min, lon_max}
    coordinate_precision: Optional[str] = None  # 'exact', 'approximate', 'region'
    location_context: Optional[Dict[str, Any]] = field(default=None)  # Enhanced location intelligence
    
    # Temporal parameters
    date_range: Optional[Tuple[datetime, datetime]] = None
    date_years: Optional[List[int]] = None  # For year comparisons like [2010, 2020]
    temporal_type: Optional[str] = None  # 'range', 'comparison', 'single_year', 'specific_month'
    
    # Depth parameters
    depth_range: Optional[Tuple[Any, Any]] = None  # Can be (min, max) or (operator, value)
    depth_type: Optional[str] = None  # 'range', 'operator', 'exact'
    
    # Data parameters
    float_ids: Optional[List[str]] = None
    parameters: Optional[List[str]] = None  # ['temperature', 'salinity', 'pressure']
    temperature_range: Optional[Tuple[str, float]] = None  # e.g., ('<', 20.0) for temperature < 20°C
    salinity_range: Optional[Tuple[str, float]] = None    # e.g., ('>', 35.0) for salinity > 35

    # Query characteristics
    is_analytical: bool = False
    is_comparative: bool = False
    is_chart_request: bool = False
    complexity_level: str = "simple"  # 'simple', 'moderate', 'complex'
    
    # Session context
    session_context: Optional[Dict] = None
    
    # Metadata
    extraction_method: str = "rule_based"  # 'rule_based', 'llm', 'hybrid'
    confidence_score: float = 1.0
    fallback_applied: bool = False
    fallback_reason: Optional[str] = None
    
    def to_sql_filters(self) -> Dict[str, Any]:
        """Convert parameters to SQL-compatible filters"""
        filters = {}
        
        # Location filters
        if self.location_bounds:
            filters['location'] = {
                'lat_min': self.location_bounds['lat_min'],
                'lat_max': self.location_bounds['lat_max'],
                'lon_min': self.location_bounds['lon_min'],
                'lon_max': self.location_bounds['lon_max']
            }
        
        # Temporal filters
        if self.date_years:
            # Special handling for year comparisons
            filters['date_years'] = self.date_years
        elif self.date_range:
            filters['date_range'] = {
                'start': self.date_range[0].isoformat(),
                'end': self.date_range[1].isoformat()
            }
        
        # Depth filters
        if self.depth_range:
            if self.depth_type == 'operator':
                operator, value = self.depth_range
                filters['depth'] = {'operator': operator, 'value': value}
            else:
                filters['depth'] = {'min': self.depth_range[0], 'max': self.depth_range[1]}
        
        # Data filters
        if self.float_ids:
            filters['float_ids'] = self.float_ids
        if self.parameters:
            filters['parameters'] = self.parameters

        # Parameter threshold filters - FIXED: Add to SQL filters
        if self.temperature_range:
            operator, value = self.temperature_range
            filters['temperature_threshold'] = {'operator': operator, 'value': value}
        if self.salinity_range:
            operator, value = self.salinity_range
            filters['salinity_threshold'] = {'operator': operator, 'value': value}

        return filters
    
    def to_chroma_filters(self) -> Dict[str, Any]:
        """Convert parameters to ChromaDB-compatible metadata filters dynamically.
        
        Builds a unified '$and' list of filters. Supports comparative regions 
        using '$or' blocks, and translates year constraints into 'date' range queries.
        """
        filter_list = []
        
        # 1. Location filters - check for comparative regions (e.g. "location1_vs_location2")
        if self.location_name and "_vs_" in self.location_name:
            locations = self.location_name.split("_vs_")
            from .unified_query_parser import UnifiedQueryParser
            
            try:
                parser = UnifiedQueryParser()
                bounds_dict = parser.location_bounds
            except Exception:
                bounds_dict = {}
                
            loc_filters = []
            for loc in locations:
                bounds = bounds_dict.get(loc.lower().strip())
                if bounds:
                    loc_filters.append({
                        "$and": [
                            {'latitude': {'$gte': float(bounds['lat_min'])}},
                            {'latitude': {'$lte': float(bounds['lat_max'])}},
                            {'longitude': {'$gte': float(bounds['lon_min'])}},
                            {'longitude': {'$lte': float(bounds['lon_max'])}}
                        ]
                    })
            if len(loc_filters) > 1:
                filter_list.append({"$or": loc_filters})
            elif len(loc_filters) == 1:
                filter_list.extend(loc_filters[0]["$and"])
                
        # Single location bounds
        elif self.location_bounds:
            filter_list.append({
                "$and": [
                    {'latitude': {'$gte': float(self.location_bounds['lat_min'])}},
                    {'latitude': {'$lte': float(self.location_bounds['lat_max'])}},
                    {'longitude': {'$gte': float(self.location_bounds['lon_min'])}},
                    {'longitude': {'$lte': float(self.location_bounds['lon_max'])}}
                ]
            })
            
        # 2. Temporal filters
        if self.date_years:
            year_filters = []
            for year in self.date_years:
                year_filters.append({
                    '$and': [
                        {'date': {'$gte': f"{year}-01-01"}},
                        {'date': {'$lte': f"{year}-12-31"}}
                    ]
                })
            if len(year_filters) > 1:
                filter_list.append({'$or': year_filters})
            else:
                filter_list.extend(year_filters[0]['$and'])
        elif self.date_range:
            filter_list.append({
                'date': {
                    '$gte': self.date_range[0].isoformat()[:10],
                    '$lte': self.date_range[1].isoformat()[:10]
                }
            })
            
        # 3. Depth filters
        if self.depth_range:
            if self.depth_type != 'operator':
                filter_list.append({
                    'depth': {
                        '$gte': float(self.depth_range[0]),
                        '$lte': float(self.depth_range[1])
                    }
                })
            else:
                operator, value = self.depth_range
                op_mapping = {
                    '>=': '$gte',
                    '<=': '$lte',
                    '>': '$gt',
                    '<': '$lt'
                }
                chroma_op = op_mapping.get(operator)
                if chroma_op:
                    filter_list.append({'depth': {chroma_op: float(value)}})
                    
        # 4. Float ID filters
        if self.float_ids:
            filter_list.append({'float_id': {'$in': [str(fid) for fid in self.float_ids]}})
            
        # 5. Temperature filters
        if self.temperature_range:
            operator, value = self.temperature_range
            op_mapping = {
                '>=': '$gte',
                '<=': '$lte',
                '>': '$gt',
                '<': '$lt'
            }
            chroma_op = op_mapping.get(operator)
            if chroma_op:
                filter_list.append({'temperature': {chroma_op: float(value)}})
                
        # 6. Salinity filters
        if self.salinity_range:
            operator, value = self.salinity_range
            op_mapping = {
                '>=': '$gte',
                '<=': '$lte',
                '>': '$gt',
                '<': '$lt'
            }
            chroma_op = op_mapping.get(operator)
            if chroma_op:
                filter_list.append({'salinity': {chroma_op: float(value)}})

        # Compile final filters dictionary
        if not filter_list:
            return {}
        if len(filter_list) == 1:
            return filter_list[0]
        return {"$and": filter_list}

    def get_summary(self) -> str:
        """Get human-readable summary of parameters"""
        parts = []
        
        if self.location_name:
            parts.append(f"Location: {self.location_name}")
        elif self.location_bounds:
            bounds = self.location_bounds
            parts.append(f"Area: {bounds['lat_min']}-{bounds['lat_max']}°N, {bounds['lon_min']}-{bounds['lon_max']}°E")
        
        if self.date_years:
            parts.append(f"Years: {', '.join(map(str, self.date_years))}")
        elif self.date_range:
            start_year = self.date_range[0].year
            end_year = self.date_range[1].year
            if start_year == end_year:
                parts.append(f"Year: {start_year}")
            else:
                parts.append(f"Period: {start_year}-{end_year}")
        
        if self.depth_range:
            if self.depth_type == 'operator':
                operator, value = self.depth_range
                parts.append(f"Depth: {operator} {value}m")
            else:
                parts.append(f"Depth: {self.depth_range[0]}-{self.depth_range[1]}m")
        
        if self.parameters:
            parts.append(f"Parameters: {', '.join(self.parameters)}")

        # Add temperature threshold to summary - FIXED
        if self.temperature_range:
            operator, value = self.temperature_range
            parts.append(f"Temperature {operator} {value}°C")

        # Add salinity threshold to summary - FIXED
        if self.salinity_range:
            operator, value = self.salinity_range
            parts.append(f"Salinity {operator} {value}")

        if self.float_ids:
            if len(self.float_ids) == 1:
                parts.append(f"Float: {self.float_ids[0]}")
            else:
                parts.append(f"Floats: {len(self.float_ids)} selected")

        return " | ".join(parts) if parts else "No specific filters"
    
    def validate_consistency(self, data_results: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate that returned data actually matches the requested parameters.
        Returns (is_consistent, list_of_violations)
        """
        violations = []
        
        if not data_results:
            return True, []  # Empty results are consistent (just no matches)
        
        # Check location consistency
        if self.location_bounds:
            bounds = self.location_bounds
            for i, record in enumerate(data_results[:10]):  # Check first 10 records
                lat = record.get('latitude')
                lon = record.get('longitude')
                if lat is not None and lon is not None:
                    if not (bounds['lat_min'] <= lat <= bounds['lat_max'] and 
                           bounds['lon_min'] <= lon <= bounds['lon_max']):
                        violations.append(f"Record {i}: lat={lat}, lon={lon} outside bounds {bounds}")
        
        # Check temporal consistency
        if self.date_years:
            for i, record in enumerate(data_results[:10]):
                date_str = record.get('date')
                if date_str:
                    try:
                        year = datetime.fromisoformat(date_str.replace('Z', '+00:00')).year
                        if year not in self.date_years:
                            violations.append(f"Record {i}: year {year} not in requested years {self.date_years}")
                    except:
                        pass
        elif self.date_range:
            start_date, end_date = self.date_range
            for i, record in enumerate(data_results[:10]):
                date_str = record.get('date')
                if date_str:
                    try:
                        record_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        if not (start_date <= record_date <= end_date):
                            violations.append(f"Record {i}: date {record_date.date()} outside range {start_date.date()}-{end_date.date()}")
                    except:
                        pass
        
        # Check depth consistency
        if self.depth_range and self.depth_type != 'operator':
            min_depth, max_depth = self.depth_range
            for i, record in enumerate(data_results[:10]):
                depth = record.get('depth')
                if depth is not None:
                    if not (min_depth <= depth <= max_depth):
                        violations.append(f"Record {i}: depth {depth}m outside range {min_depth}-{max_depth}m")
        elif self.depth_range and self.depth_type == 'operator':
            operator, value = self.depth_range
            for i, record in enumerate(data_results[:10]):
                depth = record.get('depth')
                if depth is not None:
                    if operator == '>=' and depth < value:
                        violations.append(f"Record {i}: depth {depth}m violates {operator} {value}m")
                    elif operator == '<=' and depth > value:
                        violations.append(f"Record {i}: depth {depth}m violates {operator} {value}m")
        
        # Check temperature threshold consistency - FIXED
        if self.temperature_range:
            operator, value = self.temperature_range
            for i, record in enumerate(data_results[:10]):
                temperature = record.get('temperature')
                if temperature is not None:
                    if operator == '<' and temperature >= value:
                        violations.append(f"Record {i}: temperature {temperature}°C violates < {value}°C")
                    elif operator == '>' and temperature <= value:
                        violations.append(f"Record {i}: temperature {temperature}°C violates > {value}°C")
                    elif operator == '<=' and temperature > value:
                        violations.append(f"Record {i}: temperature {temperature}°C violates <= {value}°C")
                    elif operator == '>=' and temperature < value:
                        violations.append(f"Record {i}: temperature {temperature}°C violates >= {value}°C")

        # Check salinity threshold consistency - FIXED
        if self.salinity_range:
            operator, value = self.salinity_range
            for i, record in enumerate(data_results[:10]):
                salinity = record.get('salinity')
                if salinity is not None:
                    if operator == '<' and salinity >= value:
                        violations.append(f"Record {i}: salinity {salinity} violates < {value}")
                    elif operator == '>' and salinity <= value:
                        violations.append(f"Record {i}: salinity {salinity} violates > {value}")
                    elif operator == '<=' and salinity > value:
                        violations.append(f"Record {i}: salinity {salinity} violates <= {value}")
                    elif operator == '>=' and salinity < value:
                        violations.append(f"Record {i}: salinity {salinity} violates >= {value}")

        # Check float ID consistency
        if self.float_ids:
            for i, record in enumerate(data_results[:10]):
                float_id = record.get('float_id')
                if float_id and float_id not in self.float_ids:
                    violations.append(f"Record {i}: float_id {float_id} not in requested list")

        return len(violations) == 0, violations

    @property
    def needs_data(self) -> bool:
        """Check if the query needs data (has filters or is asking for data)"""
        # If any specific filters are set, it needs data
        if (self.location_bounds or self.date_range or self.date_years or
            self.depth_range or self.float_ids or self.parameters or
            self.temperature_range or self.salinity_range):  # FIXED: Include threshold filters
            return True

        # Check if query is asking for general data exploration
        query_lower = self.original_query.lower()
        data_request_patterns = [
            'knowledge base', 'what data', 'all data', 'available data',
            'show me', 'give me', 'find', 'data you have', 'measurements',
            'what do you have', 'what information', 'database', 'dataset'
        ]

        return any(pattern in query_lower for pattern in data_request_patterns)

    @property
    def is_full_data_request(self) -> bool:
        """Check if the query is asking for full knowledge base or all available data"""
        query_lower = self.original_query.lower()
        full_data_patterns = [
            'knowledge base', 'all data', 'full data', 'entire data', 'complete data',
            'everything', 'all available', 'what data you have', 'all measurements',
            'entire knowledge', 'full knowledge', 'complete knowledge', 'database',
            'all information', 'everything available'
        ]

        return any(pattern in query_lower for pattern in full_data_patterns)

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/serialization"""
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, tuple) and len(value) == 2:
                # Handle date ranges and depth ranges
                if isinstance(value[0], datetime):
                    result[key] = [value[0].isoformat(), value[1].isoformat()]
                else:
                    result[key] = list(value)
            else:
                result[key] = value
        return result
