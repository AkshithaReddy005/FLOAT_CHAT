"""
Enhanced region matching with geographic libraries and oceanographic knowledge
"""

import json
import os
from typing import Dict, Optional, Tuple, List
from rapidfuzz import fuzz, process

try:
    from geopy import Point
    from geopy.distance import geodesic
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

try:
    import pycountry_convert as pc
    PYCOUNTRY_AVAILABLE = True
except ImportError:
    PYCOUNTRY_AVAILABLE = False


class RegionResolver:
    """Enhanced region resolver with oceanographic knowledge and geographic libraries"""

    def __init__(self, regions_file: str = None):
        if regions_file is None:
            # Default to data/regions.json relative to project root
            current_dir = os.path.dirname(__file__)
            project_root = os.path.join(current_dir, "..", "..", "..")
            regions_file = os.path.join(project_root, "..", "data", "regions.json")

        self.regions = self._load_regions(regions_file)
        self._add_oceanographic_knowledge()
        self._build_search_index()
    
    def _load_regions(self, regions_file: str) -> Dict:
        """Load regions from JSON file"""
        try:
            with open(regions_file, 'r') as f:
                data = json.load(f)
                return data.get("regions", {})
        except Exception as e:
            print(f"Warning: Could not load regions file {regions_file}: {e}")
            return {}

    def _add_oceanographic_knowledge(self):
        """Add comprehensive oceanographic region definitions"""

        # Enhanced Indian Ocean regions with proper oceanographic boundaries
        oceanographic_regions = {
            "southern_indian_ocean": {
                "lat_min": -60, "lat_max": -20, "lon_min": 20, "lon_max": 120,
                "aliases": ["southern indian ocean", "southern indian", "south indian ocean",
                          "antarctic indian ocean", "subantarctic indian ocean", "southern ocean indian sector"]
            },
            "equatorial_indian_ocean": {
                "lat_min": -20, "lat_max": 20, "lon_min": 50, "lon_max": 110,
                "aliases": ["equatorial indian ocean", "equatorial indian", "central indian ocean",
                          "tropical indian ocean", "mid indian ocean"]
            },
            "northern_indian_ocean": {
                "lat_min": 0, "lat_max": 30, "lon_min": 40, "lon_max": 100,
                "aliases": ["northern indian ocean", "northern indian", "north indian ocean"]
            },
            "western_indian_ocean": {
                "lat_min": -40, "lat_max": 25, "lon_min": 20, "lon_max": 70,
                "aliases": ["western indian ocean", "western indian", "west indian ocean",
                          "african indian ocean", "madagascar region", "mozambique channel"]
            },
            "eastern_indian_ocean": {
                "lat_min": -40, "lat_max": 25, "lon_min": 70, "lon_max": 120,
                "aliases": ["eastern indian ocean", "eastern indian", "east indian ocean",
                          "australian indian ocean", "indonesian sea region"]
            },
            "arabian_sea_extended": {
                "lat_min": 5, "lat_max": 30, "lon_min": 55, "lon_max": 80,
                "aliases": ["arabian sea", "arabian", "gulf of oman", "persian gulf region",
                          "mumbai waters", "oman sea", "northwest indian ocean"]
            },
            "bay_of_bengal_extended": {
                "lat_min": 5, "lat_max": 25, "lon_min": 75, "lon_max": 100,
                "aliases": ["bay of bengal", "bengal bay", "bengal", "bay bengal",
                          "northeast indian ocean", "bangladesh waters", "sri lanka region"]
            },
            "indian_ocean_complete": {
                "lat_min": -60, "lat_max": 30, "lon_min": 20, "lon_max": 120,
                "aliases": ["indian ocean", "indian", "indo-pacific", "indian ocean basin",
                          "indian waters", "indian sea"]
            }
        }

        # Merge with existing regions, preferring oceanographic definitions
        for region_id, region_data in oceanographic_regions.items():
            if region_id not in self.regions:
                self.regions[region_id] = region_data
            else:
                # Update aliases but keep existing bounds if they exist
                existing_aliases = set(self.regions[region_id].get("aliases", []))
                new_aliases = set(region_data.get("aliases", []))
                self.regions[region_id]["aliases"] = list(existing_aliases.union(new_aliases))

    def _build_search_index(self):
        """Build search index with canonical names and aliases"""
        self.search_index = {}
        
        for canonical_name, region_data in self.regions.items():
            # Add canonical name
            self.search_index[canonical_name] = canonical_name
            
            # Add aliases
            aliases = region_data.get("aliases", [])
            for alias in aliases:
                self.search_index[alias.lower()] = canonical_name
    
    def resolve_region(self, region_text: str, min_score: int = 70) -> Optional[Tuple[str, Dict, float]]:
        """
        Resolve region text to canonical name and bounds
        
        Returns:
            Tuple of (canonical_name, bounds_dict, confidence_score) or None
        """
        if not region_text or not self.search_index:
            return None
        
        region_text = region_text.lower().strip()
        
        # Exact match first
        if region_text in self.search_index:
            canonical = self.search_index[region_text]
            bounds = self.regions[canonical]
            return canonical, bounds, 1.0
        
        # Fuzzy match
        choices = list(self.search_index.keys())
        match = process.extractOne(
            region_text, 
            choices, 
            scorer=fuzz.ratio,
            score_cutoff=min_score
        )
        
        if match:
            matched_key, score = match[0], match[1]
            canonical = self.search_index[matched_key]
            bounds = self.regions[canonical]
            confidence = score / 100.0
            return canonical, bounds, confidence
        
        return None
    
    def get_all_regions(self) -> Dict[str, Dict]:
        """Get all available regions"""
        return self.regions.copy()
