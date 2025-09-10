"""
Dynamic Example Query Generator
Generates relevant example queries based on the actual data available in the knowledge base.
"""

import os
from typing import List, Dict, Set
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import ArgoMeasurement
from vector_store import VectorStore
from dotenv import load_dotenv

load_dotenv()


class ExampleQueryGenerator:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        
        # Base query templates categorized by complexity
        self.query_templates = {
            "simple": [
                "Show me temperature data near {}",
                "What is the salinity around {}?",
                "Find measurements at depth {}m",
                "Show recent data from {}",
                "Get temperature and salinity for float {}"
            ],
            "temporal": [
                "Show temperature trends from {} to {}",
                "Compare salinity between {} and {}",
                "What changed in {} during {}?",
                "Show seasonal patterns near {}",
                "Find temperature anomalies in {}"
            ],
            "analytical": [
                "What is the average temperature near {} at {}m depth?",
                "Compare temperature profiles between {} and {}",
                "Show the correlation between depth and salinity near {}",
                "Find temperature gradients in {} region",
                "Analyze water mass properties near {}"
            ],
            "spatial": [
                "Show all measurements within 100km of {}",
                "Compare coastal vs offshore temperatures near {}",
                "Find the warmest locations in {} region",
                "Show temperature distribution across {}",
                "Map salinity variations around {}"
            ]
        }
    
    def generate_dynamic_examples(self, db: Session, max_examples: int = 6) -> List[Dict]:
        """Generate dynamic example queries based on available data"""
        
        # Get data characteristics
        data_info = self._analyze_available_data(db)
        
        if not data_info:
            return self._get_fallback_examples()
        
        examples = []
        
        # Generate examples for each category
        categories = ["simple", "analytical", "temporal", "spatial"]
        examples_per_category = max(1, max_examples // len(categories))
        
        for category in categories:
            category_examples = self._generate_category_examples(
                category, data_info, examples_per_category
            )
            examples.extend(category_examples)
        
        # Ensure we don't exceed max_examples
        examples = examples[:max_examples]
        
        # Add metadata for better UX
        for i, example in enumerate(examples):
            example["id"] = f"example_{i+1}"
            example["estimated_results"] = self._estimate_results(example["query"], data_info)
        
        return examples
    
    def _analyze_available_data(self, db: Session) -> Dict:
        """Analyze the available data to understand what can be queried"""
        
        try:
            # Get basic statistics about the data
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_measurements,
                    COUNT(DISTINCT float_id) as unique_floats,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date,
                    MIN(latitude) as min_lat,
                    MAX(latitude) as max_lat,
                    MIN(longitude) as min_lon,
                    MAX(longitude) as max_lon,
                    MIN(depth) as min_depth,
                    MAX(depth) as max_depth,
                    AVG(temperature) as avg_temp,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    AVG(salinity) as avg_salinity,
                    MIN(salinity) as min_salinity,
                    MAX(salinity) as max_salinity
                FROM argo_measurements
                WHERE temperature IS NOT NULL AND salinity IS NOT NULL
            """)
            
            result = db.execute(stats_query).mappings().first()
            
            if not result or result['total_measurements'] == 0:
                return {}
            
            # Get some sample locations for queries
            location_query = text("""
                SELECT DISTINCT 
                    ROUND(latitude::numeric, 0) as rounded_lat,
                    ROUND(longitude::numeric, 0) as rounded_lon,
                    COUNT(*) as measurement_count
                FROM argo_measurements
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                GROUP BY ROUND(latitude::numeric, 0), ROUND(longitude::numeric, 0)
                HAVING COUNT(*) > 10
                ORDER BY measurement_count DESC
                LIMIT 5
            """)
            
            locations = db.execute(location_query).mappings().all()
            
            # Get some sample depths
            depth_query = text("""
                SELECT DISTINCT 
                    CASE 
                        WHEN depth < 50 THEN 'surface'
                        WHEN depth < 200 THEN 'thermocline' 
                        WHEN depth < 1000 THEN 'intermediate'
                        ELSE 'deep'
                    END as depth_category,
                    ROUND(AVG(depth)::numeric, 0) as avg_depth,
                    COUNT(*) as count
                FROM argo_measurements
                WHERE depth IS NOT NULL
                GROUP BY 
                    CASE 
                        WHEN depth < 50 THEN 'surface'
                        WHEN depth < 200 THEN 'thermocline'
                        WHEN depth < 1000 THEN 'intermediate'
                        ELSE 'deep'
                    END
                HAVING COUNT(*) > 5
                ORDER BY avg_depth
            """)
            
            depths = db.execute(depth_query).mappings().all()
            
            # Get time periods
            temporal_query = text("""
                SELECT 
                    EXTRACT(YEAR FROM date) as year,
                    COUNT(*) as count
                FROM argo_measurements
                WHERE date IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM date)
                HAVING COUNT(*) > 50
                ORDER BY year DESC
                LIMIT 3
            """)
            
            years = db.execute(temporal_query).mappings().all()
            
            return {
                "stats": dict(result),
                "locations": [dict(loc) for loc in locations],
                "depths": [dict(d) for d in depths],
                "years": [dict(y) for y in years]
            }
            
        except Exception as e:
            print(f"Error analyzing data: {e}")
            return {}
    
    def _generate_category_examples(self, category: str, data_info: Dict, 
                                  count: int) -> List[Dict]:
        """Generate examples for a specific category"""
        
        examples = []
        templates = self.query_templates.get(category, [])
        
        if not templates or not data_info:
            return examples
        
        stats = data_info.get("stats", {})
        locations = data_info.get("locations", [])
        depths = data_info.get("depths", [])
        years = data_info.get("years", [])
        
        # Generate location-based queries
        if locations:
            primary_location = locations[0]
            location_str = self._format_location(
                primary_location["rounded_lat"], 
                primary_location["rounded_lon"]
            )
            
            if category == "simple":
                examples.append({
                    "query": f"Show me temperature data near {location_str}",
                    "category": "simple",
                    "description": "Find temperature measurements in a specific region"
                })
            elif category == "analytical":
                if depths:
                    depth = int(depths[0]["avg_depth"])
                    examples.append({
                        "query": f"What is the average temperature near {location_str} at {depth}m depth?",
                        "category": "analytical", 
                        "description": "Analyze average temperature at specific location and depth"
                    })
            elif category == "spatial" and len(locations) > 1:
                location2 = self._format_location(
                    locations[1]["rounded_lat"],
                    locations[1]["rounded_lon"] 
                )
                examples.append({
                    "query": f"Compare temperatures between {location_str} and {location2}",
                    "category": "spatial",
                    "description": "Compare oceanographic parameters between regions"
                })
        
        # Generate temporal queries
        if years and category == "temporal":
            if len(years) >= 2:
                year1, year2 = int(years[1]["year"]), int(years[0]["year"])
                examples.append({
                    "query": f"Show temperature trends from {year1} to {year2}",
                    "category": "temporal",
                    "description": "Analyze temporal changes in ocean temperature"
                })
        
        # Generate depth-based queries
        if depths and category in ["simple", "analytical"]:
            surface_depth = next((d for d in depths if d["depth_category"] == "surface"), None)
            if surface_depth:
                depth_val = int(surface_depth["avg_depth"])
                if category == "simple":
                    examples.append({
                        "query": f"Find measurements at {depth_val}m depth",
                        "category": "simple",
                        "description": f"Get all measurements from {depth_val}m depth"
                    })
        
        # Ensure we have at least one example per requested category
        if not examples and templates:
            # Fallback to generic template
            template = templates[0]
            examples.append({
                "query": template.replace("{}", "Arabian Sea"),
                "category": category,
                "description": f"Sample {category} query"
            })
        
        return examples[:count]
    
    def _format_location(self, lat: float, lon: float) -> str:
        """Format coordinates into a readable location string"""
        
        # Map to known regions if close
        known_regions = {
            (19, 73): "Mumbai coast",
            (15, 65): "Arabian Sea",
            (10, 75): "Southern Arabian Sea", 
            (8, 77): "Southwest Indian Ocean",
            (20, 70): "Northern Arabian Sea"
        }
        
        # Find closest known region
        min_distance = float('inf')
        closest_region = None
        
        for (region_lat, region_lon), name in known_regions.items():
            distance = ((lat - region_lat) ** 2 + (lon - region_lon) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_region = name
        
        # Use region name if close, otherwise use coordinates
        if min_distance < 5:  # Within ~5 degrees
            return closest_region
        else:
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            return f"{abs(lat):.0f}°{lat_dir}, {abs(lon):.0f}°{lon_dir}"
    
    def _estimate_results(self, query: str, data_info: Dict) -> str:
        """Estimate how many results this query might return"""
        
        stats = data_info.get("stats", {})
        total = stats.get("total_measurements", 0)
        
        if not total:
            return "Unknown"
        
        # Simple heuristic based on query specificity
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["average", "correlation", "compare"]):
            return "Statistical summary"
        elif "near" in query_lower or "around" in query_lower:
            return f"~{total // 10}-{total // 5} measurements"
        elif any(word in query_lower for word in ["depth", "temperature", "salinity"]):
            return f"~{total // 20}-{total // 10} measurements"
        else:
            return f"~{total // 50}-{total // 20} measurements"
    
    def _get_fallback_examples(self) -> List[Dict]:
        """Provide fallback examples when no data is available"""
        
        return [
            {
                "id": "fallback_1",
                "query": "Show me temperature data near Mumbai",
                "category": "simple",
                "description": "Find temperature measurements near Mumbai coast",
                "estimated_results": "Depends on available data"
            },
            {
                "id": "fallback_2", 
                "query": "What is the average salinity in Arabian Sea?",
                "category": "analytical",
                "description": "Calculate average salinity for Arabian Sea region",
                "estimated_results": "Statistical summary"
            },
            {
                "id": "fallback_3",
                "query": "Show temperature trends from 2022 to 2024",
                "category": "temporal", 
                "description": "Analyze temperature changes over time",
                "estimated_results": "Time series data"
            },
            {
                "id": "fallback_4",
                "query": "Find measurements at 100m depth",
                "category": "simple",
                "description": "Get all measurements from 100m depth level",
                "estimated_results": "Depth-specific data"
            }
        ]