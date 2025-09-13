"""
Fuzzy region matching without regex
"""

import json
import os
from typing import Dict, Optional, Tuple
from rapidfuzz import fuzz, process


class RegionResolver:
    """Resolve region names using fuzzy matching and gazetteer"""
    
    def __init__(self, regions_file: str = None):
        if regions_file is None:
            # Default to data/regions.json relative to project root
            current_dir = os.path.dirname(__file__)
            project_root = os.path.join(current_dir, "..", "..", "..", "..")
            regions_file = os.path.join(project_root, "data", "regions.json")
        
        self.regions = self._load_regions(regions_file)
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
