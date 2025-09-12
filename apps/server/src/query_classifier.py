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
        
        # Specific chart type keywords
        self.chart_type_keywords = {
            'time_series': ['time series', 'over time', 'trend', 'timeline', 'temporal', 'time plot', 'time chart'],
            'scatter': ['scatter', 'correlation', 'relationship', 'vs', 'against', 'compare', 'plot against'],
            'line': ['line chart', 'line graph', 'line plot', 'trend line', 'connect'],
            'histogram': ['histogram', 'distribution', 'frequency', 'bins', 'spread'],
            'bar': ['bar chart', 'bar graph', 'comparison', 'compare between'],
            'multi_axis': ['both', 'together', 'combined', 'same chart', 'dual axis']
        }
    
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
    
    def classify_chart_request(self, user_query: str) -> Dict:
        """Detect and classify specific chart generation requests"""
        try:
            if not user_query or not isinstance(user_query, str):
                return {"is_chart_request": False}
                
            query_lower = user_query.lower()
            
            # Enhanced chart indicators - be more comprehensive
            primary_chart_indicators = ['plot', 'chart', 'graph', 'visualize', 'draw', 'create chart', 'generate chart', 'make a chart']
            secondary_chart_indicators = ['show me', 'display', 'versus', 'vs', 'against', 'compare', 'correlation']
            parameter_combinations = ['temperature vs', 'salinity vs', 'depth vs', 'over time', 'with depth']
            
            # Primary detection - strong chart indicators
            has_primary_indicator = any(indicator in query_lower for indicator in primary_chart_indicators)
            
            # Secondary detection - contextual indicators with parameters
            has_secondary_with_params = (
                any(indicator in query_lower for indicator in secondary_chart_indicators) and
                any(combo in query_lower for combo in parameter_combinations)
            )
            
            # Parameter-based detection - specific oceanographic chart patterns
            has_specific_pattern = any([
                'temperature vs salinity' in query_lower,
                'temperature vs depth' in query_lower,
                'salinity vs depth' in query_lower,
                'over time' in query_lower and any(param in query_lower for param in ['temperature', 'salinity', 'depth']),
                'profile' in query_lower and any(param in query_lower for param in ['temperature', 'salinity'])
            ])
            
            is_chart_request = has_primary_indicator or has_secondary_with_params or has_specific_pattern
            
            if not is_chart_request:
                return {"is_chart_request": False}
            
            # Determine chart type
            detected_chart_type = None
            chart_type_confidence = 0.0
            
            for chart_type, keywords in self.chart_type_keywords.items():
                matches = sum(1 for keyword in keywords if keyword in query_lower)
                confidence = matches / len(keywords)
                
                if confidence > chart_type_confidence:
                    chart_type_confidence = confidence
                    detected_chart_type = chart_type
            
            # Extract parameters of interest
            parameters = []
            if 'temperature' in query_lower or 'temp' in query_lower:
                parameters.append('temperature')
            if 'salinity' in query_lower or 'salt' in query_lower:
                parameters.append('salinity')
            if 'pressure' in query_lower:
                parameters.append('pressure')
            if 'depth' in query_lower:
                parameters.append('depth')
            
            # Determine axes (for scatter plots and comparisons)
            x_axis = None
            y_axis = None
            
            # Look for X vs Y patterns
            vs_patterns = ['vs', 'versus', 'against', 'over']
            for pattern in vs_patterns:
                if pattern in query_lower:
                    parts = query_lower.split(pattern)
                    if len(parts) == 2:
                        before = parts[0].strip().split()
                        after = parts[1].strip().split()
                        
                        # Extract parameter from before 'vs'
                        for param in ['temperature', 'temp', 'salinity', 'salt', 'pressure', 'depth']:
                            if param in parts[0]:
                                y_axis = param if param != 'temp' else 'temperature'
                                if param == 'salt':
                                    y_axis = 'salinity'
                                break
                        
                        # Extract parameter from after 'vs'
                        for param in ['time', 'depth', 'temperature', 'temp', 'salinity', 'salt', 'pressure']:
                            if param in parts[1]:
                                x_axis = param if param not in ['temp', 'salt'] else ('temperature' if param == 'temp' else 'salinity')
                                break
            
            # Special case for time series
            if 'time' in query_lower and ('over' in query_lower or 'vs' in query_lower):
                detected_chart_type = 'time_series'
                x_axis = 'time'
                if not y_axis and parameters:
                    y_axis = parameters[0]
            
            # Default chart type based on parameters
            if not detected_chart_type:
                if len(parameters) >= 2:
                    detected_chart_type = 'scatter'
                elif 'time' in query_lower or any(word in query_lower for word in ['trend', 'over time', 'timeline']):
                    detected_chart_type = 'time_series'
                elif any(word in query_lower for word in ['distribution', 'histogram', 'frequency']):
                    detected_chart_type = 'histogram'
                else:
                    detected_chart_type = 'line'  # Default fallback
            
            return {
                "is_chart_request": True,
                "chart_type": detected_chart_type,
                "parameters": parameters,
                "x_axis": x_axis,
                "y_axis": y_axis,
                "confidence": max(0.6, chart_type_confidence) if is_chart_request else 0.0,
                "raw_keywords_found": [kw for kw in chart_indicators if kw in query_lower]
            }
            
        except Exception as e:
            print(f"Chart request classification error: {e}")
            return {"is_chart_request": False}