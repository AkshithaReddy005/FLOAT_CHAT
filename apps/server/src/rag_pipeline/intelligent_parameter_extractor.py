"""
Intelligent Parameter Extractor
Uses fuzzy matching and semantic understanding to handle typos and variations
"""

import re
from typing import Optional, Tuple, List, Dict, Any
from difflib import SequenceMatcher
import json

class IntelligentParameterExtractor:
    """Intelligent parameter extraction with typo tolerance and semantic understanding"""
    
    def __init__(self):
        # Semantic keyword groups with variations
        self.semantic_groups = {
            'depth': {
                'keywords': ['depth', 'deep', 'depths', 'meter', 'meters', 'm', 'below', 'above', 'under', 'deeper', 'shallower'],
                'variations': ['dpth', 'deph', 'dept', 'deth', 'mtr', 'mtrs', 'belo', 'abve', 'undr', 'deper', 'shaloer']
            },
            'temperature': {
                'keywords': ['temperature', 'temp', 'temperatures', 'celsius', 'c', 'degree', 'degrees', 'warm', 'cold', 'hot'],
                'variations': ['temprature', 'temperture', 'tempr', 'tmp', 'temperatures', 'degres', 'deg', 'war', 'cld', 'hot']
            },
            'salinity': {
                'keywords': ['salinity', 'sal', 'salt', 'salinities', 'ppt', 'psu'],
                'variations': ['salinty', 'salnity', 'slinity', 'salnities', 'salinaty', 'slt']
            }
        }
        
        # Comparison operators with typo tolerance
        self.comparison_groups = {
            'greater_than': {
                'keywords': ['greater than', 'more than', 'above', 'over', 'higher than', '>', 'gt'],
                'variations': ['grater than', 'greate than', 'greatr than', 'mor than', 'abve', 'ovr', 'highr than', 'gtr']
            },
            'less_than': {
                'keywords': ['less than', 'below', 'under', 'lower than', '<', 'lt'],
                'variations': ['les than', 'lss than', 'lowr than', 'belo', 'undr', 'lwr', 'lt']
            }
        }
        
        # Context indicators
        self.context_indicators = {
            'is': ['is', 'are', 'were', 'was', 'iz', 'ar', 'r'],
            'where': ['where', 'when', 'wher', 'wen', 'at', 'in']
        }
    
    def fuzzy_match(self, text: str, target_group: Dict[str, List[str]], threshold: float = 0.8) -> Optional[str]:
        """Fuzzy match text against a semantic group"""
        text_lower = text.lower()
        
        # Direct keyword match
        for keyword in target_group['keywords']:
            if keyword in text_lower:
                return keyword
        
        # Fuzzy match for variations
        for variation in target_group['variations']:
            if variation in text_lower:
                return variation
        
        # Use SequenceMatcher for fuzzy matching
        for keyword in target_group['keywords']:
            matcher = SequenceMatcher(None, text_lower, keyword)
            similarity = matcher.ratio() / 100.0
            if similarity >= threshold:
                return keyword
        
        return None
    
    def extract_number(self, text: str) -> Optional[float]:
        """Extract numbers from text with various formats"""
        # Handle different number formats
        patterns = [
            r'(\d+(?:\.\d+)?)',  # Standard numbers
            r'(\d+)',            # Integers
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    return float(matches[0])
                except ValueError:
                    continue
        
        return None
    
    def extract_operator(self, text: str) -> Optional[str]:
        """Extract comparison operator with typo tolerance"""
        text_lower = text.lower()
        
        # Check each comparison group
        for operator_type, group in self.comparison_groups.items():
            match = self.fuzzy_match(text_lower, group, threshold=0.7)
            if match:
                if operator_type == 'greater_than':
                    return '>='
                elif operator_type == 'less_than':
                    return '<='
        
        return None
    
    def extract_depth_intelligent(self, query: str) -> Tuple[Optional[Tuple[str, float]], Optional[str]]:
        """Intelligent depth extraction with typo tolerance"""
        query_lower = query.lower()
        
        # Check if this is specifically about depth (not just contains depth words)
        depth_keywords = ['depth', 'dpth', 'deph', 'dept', 'deth', 'meter', 'meters', 'm']
        has_depth_context = any(keyword in query_lower for keyword in depth_keywords)
        
        if not has_depth_context:
            return None, None
        
        # Extract operator
        operator = self.extract_operator(query_lower)
        if not operator:
            return None, None
        
        # Extract number
        number = self.extract_number(query)
        if not number:
            return None, None
        
        return (operator, number), "operator"
    
    def extract_temperature_intelligent(self, query: str) -> Optional[Tuple[str, float]]:
        """Intelligent temperature extraction with typo tolerance"""
        query_lower = query.lower()
        
        # Check if this is specifically about temperature
        temp_keywords = ['temperature', 'temp', 'temprature', 'tempr', 'tmp', 'celsius', 'c', 'degree', 'degrees']
        has_temp_context = any(keyword in query_lower for keyword in temp_keywords)
        
        if not has_temp_context:
            return None
        
        # Extract operator
        operator = self.extract_operator(query_lower)
        if not operator:
            return None
        
        # Extract number
        number = self.extract_number(query)
        if not number:
            return None
        
        return (operator, number)
    
    def extract_salinity_intelligent(self, query: str) -> Optional[Tuple[str, float]]:
        """Intelligent salinity extraction with typo tolerance"""
        query_lower = query.lower()
        
        # Check if this is specifically about salinity
        sal_keywords = ['salinity', 'sal', 'salinty', 'salnity', 'slinity', 'salinaty', 'salt']
        has_sal_context = any(keyword in query_lower for keyword in sal_keywords)
        
        if not has_sal_context:
            return None
        
        # Extract operator
        operator = self.extract_operator(query_lower)
        if not operator:
            return None
        
        # Extract number
        number = self.extract_number(query)
        if not number:
            return None
        
        return (operator, number)
    
    def extract_all_parameters(self, query: str) -> Dict[str, Any]:
        """Extract all parameters intelligently with context prioritization"""
        results = {
            'depth_range': None,
            'depth_type': None,
            'temperature_range': None,
            'salinity_range': None,
            'confidence_scores': {}
        }
        
        query_lower = query.lower()
        
        # Priority 1: Check for explicit parameter mentions
        if any(keyword in query_lower for keyword in ['depth', 'dpth', 'deph', 'dept', 'deth']):
            depth_range, depth_type = self.extract_depth_intelligent(query)
            if depth_range:
                results['depth_range'] = depth_range
                results['depth_type'] = depth_type
                results['confidence_scores']['depth'] = 0.9
                return results  # Return early - explicit depth found
        
        if any(keyword in query_lower for keyword in ['temperature', 'temp', 'temprature', 'tempr', 'tmp']):
            temp_range = self.extract_temperature_intelligent(query)
            if temp_range:
                results['temperature_range'] = temp_range
                results['confidence_scores']['temperature'] = 0.9
                return results  # Return early - explicit temperature found
        
        if any(keyword in query_lower for keyword in ['salinity', 'sal', 'salinty', 'salnity', 'slinity']):
            sal_range = self.extract_salinity_intelligent(query)
            if sal_range:
                results['salinity_range'] = sal_range
                results['confidence_scores']['salinity'] = 0.9
                return results  # Return early - explicit salinity found
        
        # Priority 2: Fallback to general extraction (lower confidence)
        depth_range, depth_type = self.extract_depth_intelligent(query)
        if depth_range:
            results['depth_range'] = depth_range
            results['depth_type'] = depth_type
            results['confidence_scores']['depth'] = 0.6
        
        temp_range = self.extract_temperature_intelligent(query)
        if temp_range:
            results['temperature_range'] = temp_range
            results['confidence_scores']['temperature'] = 0.6
        
        sal_range = self.extract_salinity_intelligent(query)
        if sal_range:
            results['salinity_range'] = sal_range
            results['confidence_scores']['salinity'] = 0.6
        
        return results
    
    def demonstrate_extraction(self, queries: List[str]):
        """Demonstrate the extraction on various queries with typos"""
        print("=== Intelligent Parameter Extraction Demo ===")
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            params = self.extract_all_parameters(query)
            
            if params['depth_range']:
                print(f"  Depth: {params['depth_range']} (confidence: {params['confidence_scores'].get('depth', 0)})")
            if params['temperature_range']:
                print(f"  Temperature: {params['temperature_range']} (confidence: {params['confidence_scores'].get('temperature', 0)})")
            if params['salinity_range']:
                print(f"  Salinity: {params['salinity_range']} (confidence: {params['confidence_scores'].get('salinity', 0)})")
            
            if not any([params['depth_range'], params['temperature_range'], params['salinity_range']]):
                print("  No parameters extracted")

# Test the intelligent extractor
if __name__ == "__main__":
    extractor = IntelligentParameterExtractor()
    
    test_queries = [
        "Give me data where depth is more than 100 in indian ocean region",
        "Show me temp where dpth is grater than 200",
        "Find salnity less than 35 in southern ocean",
        "Temprature above 25 degrees in arabian sea",
        "Depth undr 500 meters in indian ocean",
        "Where temprature is mor than 30 and salinty is les than 34",
        "Data where dpth > 1000 and temp < 15"
    ]
    
    extractor.demonstrate_extraction(test_queries)
