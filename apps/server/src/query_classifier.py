"""
Query Classification Module
Classifies user queries to determine if they need ARGO data and what type of analysis is required.
"""

from typing import Dict


class QueryClassifier:
    def __init__(self):
        # Keywords that indicate ARGO data queries
        self.argo_keywords = [
            'temperature', 'temp', 'salinity', 'salt', 'pressure', 'depth', 'float',
            'argo', 'ocean', 'sea', 'marine', 'profile', 'measurement', 'data',
            'latitude', 'longitude', 'location', 'mumbai', 'arabian', 'indian',
            'show', 'find', 'get', 'retrieve', 'analysis', 'trend', 'pattern'
        ]
        
        # Temporal keywords
        self.temporal_keywords = [
            'march', 'april', 'may', 'june', 'july', 'august', 'september',
            'october', 'november', 'december', 'january', 'february',
            '2020', '2021', '2022', '2023', '2024', 'year', 'month', 'recent', 'last'
        ]
        
        # Spatial keywords  
        self.spatial_keywords = [
            'near', 'around', 'region', 'area', 'coast', 'offshore', 'latitude', 'longitude'
        ]
        
        # Analytical keywords
        self.analytical_keywords = [
            'average', 'mean', 'maximum', 'minimum', 'trend', 'pattern', 'correlation',
            'analysis', 'compare', 'comparison', 'statistical', 'aggregate', 'group',
            'distribution', 'variance', 'standard deviation'
        ]
        
        # Visualization keywords
        self.visualization_keywords = [
            'plot', 'chart', 'graph', 'visualize', 'show', 'display', 'map'
        ]
    
    def classify_query(self, user_query: str) -> Dict:
        """Classify query type and determine what processing is needed"""
        try:
            if not user_query or not isinstance(user_query, str):
                return self._get_default_classification()
                
            query_lower = user_query.lower()
            
            # Count keyword matches
            argo_score = sum(1 for keyword in self.argo_keywords if keyword in query_lower)
            temporal_score = sum(1 for keyword in self.temporal_keywords if keyword in query_lower)
            spatial_score = sum(1 for keyword in self.spatial_keywords if keyword in query_lower)
            analytical_score = sum(1 for keyword in self.analytical_keywords if keyword in query_lower)
            viz_score = sum(1 for keyword in self.visualization_keywords if keyword in query_lower)
            
            # More permissive data detection - err on the side of being helpful
            needs_data = (
                argo_score > 0 or 
                temporal_score > 0 or 
                spatial_score > 0 or 
                any(word in query_lower for word in ["find", "show", "get", "search", "data", "tell", "what", "how", "where"]) or
                len(query_lower.split()) > 3  # Longer queries likely need data
            )
            
            # More balanced complexity assessment
            is_complex = (
                analytical_score > 1 or 
                (analytical_score > 0 and (temporal_score > 0 or spatial_score > 0)) or
                (argo_score > 2 and temporal_score > 0 and spatial_score > 0) or
                any(word in query_lower for word in ["compare", "correlation", "trend", "pattern", "analysis"])
            )
            
            # Be more generous with visualizations - they help understanding
            needs_visualization = (
                viz_score > 0 or 
                (needs_data and argo_score > 0) or
                any(word in query_lower for word in ["where", "location", "depth", "profile"])
            )
            
            # More forgiving confidence scoring
            total_score = argo_score + temporal_score + spatial_score + analytical_score
            confidence = min(1.0, max(0.3, total_score / 4))  # Minimum confidence boost
            
            # Simplified complexity levels - favor simple/moderate over complex
            complexity_level = "simple"
            if analytical_score > 2 or (analytical_score > 1 and (temporal_score > 1 or spatial_score > 1)):
                complexity_level = "complex"
            elif analytical_score > 0 or argo_score > 1 or (temporal_score > 0 and spatial_score > 0):
                complexity_level = "moderate"
            
            return {
                "needs_data": needs_data,
                "is_complex": is_complex,
                "is_analytical": analytical_score > 0,
                "has_temporal": temporal_score > 0,
                "has_spatial": spatial_score > 0,
                "needs_visualization": needs_visualization,
                "complexity_level": complexity_level,
                "confidence": confidence,
                "scores": {
                    "argo": argo_score,
                    "temporal": temporal_score,
                    "spatial": spatial_score, 
                    "analytical": analytical_score,
                    "visualization": viz_score
                }
            }
        except Exception as e:
            print(f"Query classification error: {e}")
            return self._get_default_classification()

    def _get_default_classification(self) -> Dict:
        """Return a safe default classification when classification fails"""
        return {
            "needs_data": True,
            "is_complex": False,
            "is_analytical": False,
            "has_temporal": False,
            "has_spatial": False,
            "needs_visualization": True,
            "complexity_level": "simple",
            "confidence": 0.5,
            "scores": {
                "argo": 1,
                "temporal": 0,
                "spatial": 0,
                "analytical": 0,
                "visualization": 1
            }
        }
    
    def get_query_intent(self, user_query: str) -> str:
        """Determine the primary intent of the query"""
        try:
            if not user_query or not isinstance(user_query, str):
                return "general"
                
            query_lower = user_query.lower()
            
            if any(word in query_lower for word in ['what', 'explain', 'tell me about']):
                return "explanation"
            elif any(word in query_lower for word in ['show', 'display', 'plot', 'chart']):
                return "visualization"
            elif any(word in query_lower for word in ['find', 'get', 'retrieve', 'search']):
                return "data_retrieval"
            elif any(word in query_lower for word in ['analyze', 'analysis', 'compare', 'trend']):
                return "analysis"
            else:
                return "general"
        except Exception as e:
            print(f"Error determining query intent: {e}")
            return "general"