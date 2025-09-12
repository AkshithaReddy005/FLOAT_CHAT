"""
Visualization Builder Module
Prepares data for various types of visualizations based on query results and classification.
"""

from typing import Dict, List, Any, Optional, Tuple
import statistics
from collections import defaultdict
import math
from chart_request_processor import ChartRequestProcessor


class VisualizationBuilder:
    def __init__(self):
        self.chart_request_processor = ChartRequestProcessor()
        self.chart_decision_thresholds = {
            'min_points_for_map': 10,          
            'min_points_for_heatmap': 50,       
            'min_depth_levels': 8,               
            'min_time_points': 5,               
            'max_single_series_points': 100,    
            'geographic_spread_threshold': 1.0,  
            'min_data_quality_score': 0.6       #Minimum data quality threshold
        }
    
    def _analyze_data_patterns(self, db_results: List[Dict], query_classification: Dict) -> Dict:
        """Analyze data patterns to make intelligent visualization decisions"""
        analysis = {
            'total_points': len(db_results),
            'has_geographic_data': False,
            'has_depth_data': False,
            'has_temporal_data': False,
            'geographic_spread': 0.0,
            'depth_range': None,
            'time_span_days': 0,
            'data_types': [],
            'unique_floats': 0,
            'query_intent': self._extract_query_intent(query_classification)
        }
        
        # Analyze geographic spread
        lats = [float(r['latitude']) for r in db_results if r.get('latitude') is not None]
        lons = [float(r['longitude']) for r in db_results if r.get('longitude') is not None]
        
        if len(lats) >= 2 and len(lons) >= 2:
            analysis['has_geographic_data'] = True
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            analysis['geographic_spread'] = math.sqrt(lat_range**2 + lon_range**2)
        
        # Analyze depth patterns
        depths = [float(r['depth']) for r in db_results if r.get('depth') is not None and r.get('depth') >= 0]
        if len(depths) >= self.chart_decision_thresholds['min_depth_levels']:
            analysis['has_depth_data'] = True
            analysis['depth_range'] = (min(depths), max(depths))
        
        # Analyze temporal patterns
        dates = [r.get('date') for r in db_results if r.get('date')]
        if len(dates) >= 2:
            analysis['has_temporal_data'] = True
            unique_dates = set(str(d)[:10] for d in dates)
            if len(unique_dates) > 1:
                # Calculate time span (simplified)
                analysis['time_span_days'] = len(unique_dates)
        
        # Identify available data types
        if any(r.get('temperature') is not None for r in db_results):
            analysis['data_types'].append('temperature')
        if any(r.get('salinity') is not None for r in db_results):
            analysis['data_types'].append('salinity')
        if any(r.get('pressure') is not None for r in db_results):
            analysis['data_types'].append('pressure')
        
        analysis['unique_floats'] = len(set(r.get('float_id', '') for r in db_results))
        
        return analysis
    
    def _extract_query_intent(self, query_classification: Dict) -> str:
        """Extract the primary intent from query classification"""
        if query_classification.get('has_spatial'):
            return 'geographic_analysis'
        elif query_classification.get('has_temporal'):
            return 'temporal_analysis'
        elif query_classification.get('is_analytical'):
            return 'statistical_analysis'
        elif query_classification.get('complexity_level') == 'complex':
            return 'comprehensive_analysis'
        else:
            return 'data_exploration'
    
    def _analyze_query_context(self, user_query: str = None, context_results: Dict = None) -> Dict:
        """Analyze query and context to make smarter visualization decisions"""
        analysis = {
            'query_intent': 'exploration',
            'visualization_preferences': [],
            'focus_parameters': [],
            'context_relevance': 0.0
        }
        
        if user_query:
            query_lower = user_query.lower()
            
            # Determine primary intent from query text
            if any(word in query_lower for word in ['map', 'location', 'where', 'area', 'region']):
                analysis['query_intent'] = 'geographic'
                analysis['visualization_preferences'].append('map')
            elif any(word in query_lower for word in ['depth', 'profile', 'vertical', 'deep', 'shallow']):
                analysis['query_intent'] = 'depth_analysis'
                analysis['visualization_preferences'].append('depth_profile')
            elif any(word in query_lower for word in ['time', 'trend', 'over time', 'temporal', 'recent']):
                analysis['query_intent'] = 'temporal'
                analysis['visualization_preferences'].append('time_series')
            elif any(word in query_lower for word in ['statistics', 'average', 'mean', 'compare', 'analysis']):
                analysis['query_intent'] = 'statistical'
                analysis['visualization_preferences'].append('statistics')
            
            # Extract focus parameters
            if 'temperature' in query_lower:
                analysis['focus_parameters'].append('temperature')
            if 'salinity' in query_lower:
                analysis['focus_parameters'].append('salinity')
            if 'pressure' in query_lower:
                analysis['focus_parameters'].append('pressure')
        
        # Analyze context relevance from ChromaDB
        if context_results and context_results.get('documents'):
            documents = context_results.get('documents', [[]])[0]
            if documents:
                # Calculate relevance based on context quality
                total_length = sum(len(doc) for doc in documents)
                meaningful_docs = [doc for doc in documents if len(doc) > 50]
                
                if meaningful_docs and total_length > 200:
                    analysis['context_relevance'] = min(1.0, len(meaningful_docs) / 5.0)
                    
                    # Extract visualization hints from context
                    context_text = ' '.join(documents).lower()
                    if 'spatial' in context_text or 'geographic' in context_text:
                        analysis['visualization_preferences'].append('map')
                    if 'depth' in context_text or 'profile' in context_text:
                        analysis['visualization_preferences'].append('depth_profile')
                    if 'temporal' in context_text or 'time series' in context_text:
                        analysis['visualization_preferences'].append('time_series')
        
        return analysis
    
    def _make_smart_visualization_decisions(self, data_analysis: Dict, query_classification: Dict, query_context: Dict) -> Dict:
        """Make intelligent decisions about visualizations using data patterns, query classification, and context"""
        decisions = {
            'selected_charts': [],
            'reasoning': '',
            'recommendations': [],
            'priority_order': []
        }
        
        reasoning_parts = []
        chart_scores = {}  # Track relevance scores for each chart type
        
        # Get query preferences from context analysis
        preferred_visualizations = set(query_context.get('visualization_preferences', []))
        query_intent = query_context.get('query_intent', 'exploration')
        context_relevance = query_context.get('context_relevance', 0.0)
        
        # Score each visualization type based on multiple factors
        
        # MAP SCORING
        map_score = 0.0
        if data_analysis['has_geographic_data']:
            map_score += 0.6  # Base score for having geographic data
            if data_analysis['geographic_spread'] > self.chart_decision_thresholds['geographic_spread_threshold']:
                map_score += 0.3  # Bonus for wide spread
            if data_analysis['total_points'] >= self.chart_decision_thresholds['min_points_for_map']:
                map_score += 0.2  # Bonus for sufficient points
                
        # Query/context bonuses for map
        if 'map' in preferred_visualizations:
            map_score += 0.4
        if query_intent == 'geographic':
            map_score += 0.3
        if any(word in str(query_classification).lower() for word in ['spatial', 'location', 'geographic']):
            map_score += 0.2
            
        chart_scores['map'] = map_score
        
        # DEPTH PROFILE SCORING  
        depth_score = 0.0
        if data_analysis['has_depth_data']:
            depth_score += 0.5  # Base score
            if data_analysis.get('depth_range') and (data_analysis['depth_range'][1] - data_analysis['depth_range'][0]) > 100:
                depth_score += 0.3  # Bonus for good range
                
        # Query/context bonuses for depth profile
        if 'depth_profile' in preferred_visualizations:
            depth_score += 0.4
        if query_intent == 'depth_analysis':
            depth_score += 0.4
        if 'temperature' in query_context.get('focus_parameters', []):
            depth_score += 0.2  # Temperature profiles are very common
            
        chart_scores['depth_profile'] = depth_score
        
        # TIME SERIES SCORING
        time_score = 0.0
        if data_analysis['has_temporal_data']:
            time_score += 0.5  # Base score
            if data_analysis['time_span_days'] >= self.chart_decision_thresholds['min_time_points']:
                time_score += 0.3
                
        # Query/context bonuses for time series
        if 'time_series' in preferred_visualizations:
            time_score += 0.4
        if query_intent == 'temporal' or query_classification.get('has_temporal'):
            time_score += 0.4
            
        chart_scores['time_series'] = time_score
        
        # STATISTICS SCORING
        stats_score = 0.0
        if query_classification.get('is_analytical'):
            stats_score += 0.6  # Strong base for analytical queries
        if data_analysis['total_points'] >= 20:  # Need reasonable sample size
            stats_score += 0.3
            
        # Query/context bonuses for statistics
        if 'statistics' in preferred_visualizations:
            stats_score += 0.3
        if query_intent == 'statistical':
            stats_score += 0.4
            
        chart_scores['statistics'] = stats_score
        
        # Apply context relevance boost
        if context_relevance > 0.5:
            for chart_type in preferred_visualizations:
                if chart_type in chart_scores:
                    chart_scores[chart_type] += 0.2 * context_relevance
        
        # Select charts based on scores, with intelligent thresholds
        selected_charts = []
        chart_threshold = 0.4  # Minimum score to include a chart
        
        # Always select top-scoring chart if it meets minimum requirements
        if chart_scores:
            top_chart = max(chart_scores, key=chart_scores.get)
            if chart_scores[top_chart] >= chart_threshold:
                selected_charts.append(top_chart)
                reasoning_parts.append(f"{top_chart.replace('_', ' ').title()} selected (score: {chart_scores[top_chart]:.2f}) - primary visualization for this query")
        
        # Add additional charts if they score well and provide different perspectives
        max_charts = 3 if query_classification.get('complexity_level') == 'complex' else 2
        
        for chart_type, score in sorted(chart_scores.items(), key=lambda x: x[1], reverse=True):
            if (chart_type not in selected_charts and 
                score >= chart_threshold and 
                len(selected_charts) < max_charts):
                
                # Check if this chart adds value (different dimension)
                adds_value = True
                if chart_type == 'statistics' and any(c in selected_charts for c in ['map', 'depth_profile', 'time_series']):
                    adds_value = score >= 0.6  # Higher bar for stats if other viz present
                elif chart_type == 'time_series' and 'depth_profile' in selected_charts:
                    adds_value = score >= 0.7  # Avoid redundancy
                    
                if adds_value:
                    selected_charts.append(chart_type)
                    reasoning_parts.append(f"{chart_type.replace('_', ' ').title()} added (score: {score:.2f}) - provides additional analytical perspective")
        
        # Fall back to at least one visualization if data quality is sufficient
        if not selected_charts and data_analysis['total_points'] >= 5:
            quality_score = self._calculate_data_quality_score(data_analysis)
            if quality_score >= 0.3:  # Lower threshold for fallback
                if data_analysis['has_geographic_data']:
                    selected_charts.append('map')
                    reasoning_parts.append("Map selected as fallback - geographic data available")
                elif data_analysis['has_depth_data']:
                    selected_charts.append('depth_profile')
                    reasoning_parts.append("Depth profile selected as fallback - depth measurements available")
        
        # Build final decisions
        decisions['selected_charts'] = selected_charts
        decisions['reasoning'] = ' • '.join(reasoning_parts) if reasoning_parts else 'No suitable visualizations identified'
        decisions['priority_order'] = sorted(selected_charts, key=lambda x: chart_scores.get(x, 0), reverse=True)
        
        # Build recommendations with detailed reasoning
        for chart_type in selected_charts:
            chart_info = {
                'type': chart_type,
                'score': chart_scores.get(chart_type, 0),
                'reason': self._get_chart_justification(chart_type, data_analysis, query_context)
            }
            decisions['recommendations'].append(chart_info)
        
        return decisions
    
    def _get_chart_justification(self, chart_type: str, data_analysis: Dict, query_context: Dict) -> str:
        """Provide detailed justification for why a chart was selected"""
        
        justifications = {
            'map': f"Geographic visualization with {data_analysis['total_points']} points across {data_analysis['geographic_spread']:.1f}° geographic spread",
            'depth_profile': f"Vertical ocean analysis with depth range {data_analysis.get('depth_range', (0, 0))[0]:.0f}m to {data_analysis.get('depth_range', (0, 0))[1]:.0f}m",
            'time_series': f"Temporal analysis spanning {data_analysis['time_span_days']} time periods showing trends over time",
            'statistics': f"Statistical summary of {data_analysis['total_points']} measurements with {len(data_analysis['data_types'])} parameter types"
        }
        
        base_reason = justifications.get(chart_type, f"{chart_type} visualization")
        
        # Add query-specific context
        if query_context.get('query_intent') and chart_type in query_context.get('visualization_preferences', []):
            base_reason += f" - directly requested for {query_context['query_intent']} analysis"
        elif query_context.get('focus_parameters'):
            params = ', '.join(query_context['focus_parameters'])
            base_reason += f" - optimal for exploring {params} patterns"
            
        return base_reason
    
    def _make_visualization_decisions(self, data_analysis: Dict, query_classification: Dict) -> Dict:
        """Make intelligent decisions about which visualizations to create"""
        decisions = {
            'selected_charts': [],
            'reasoning': '',
            'recommendations': []
        }
        
        reasoning_parts = []
        
        # Geographic data decision logic
        if data_analysis['has_geographic_data']:
            if data_analysis['geographic_spread'] > self.chart_decision_thresholds['geographic_spread_threshold']:
                if data_analysis['total_points'] >= self.chart_decision_thresholds['min_points_for_heatmap']:
                    decisions['selected_charts'].append('map')
                    decisions['recommendations'].append({
                        'type': 'map',
                        'chart_type': 'heatmap',
                        'reason': f"Geographic data with wide spread ({data_analysis['geographic_spread']:.1f}°) and {data_analysis['total_points']} points suitable for heatmap visualization"
                    })
                    reasoning_parts.append(f"Map visualization selected: Wide geographic distribution ({data_analysis['geographic_spread']:.1f}° spread) with {data_analysis['total_points']} measurement points")
                elif data_analysis['total_points'] >= self.chart_decision_thresholds['min_points_for_map']:
                    decisions['selected_charts'].append('map')
                    decisions['recommendations'].append({
                        'type': 'map',
                        'chart_type': 'scatter',
                        'reason': f"Geographic data with {data_analysis['total_points']} points suitable for scatter map"
                    })
                    reasoning_parts.append(f"Map visualization selected: {data_analysis['total_points']} geographic points showing measurement locations")
            else:
                reasoning_parts.append(f"Map skipped: Geographic spread too small ({data_analysis['geographic_spread']:.1f}°) - points are too clustered for meaningful visualization")
        else:
            reasoning_parts.append("Map skipped: Insufficient geographic coordinate data")
        
        # Depth profile decision logic
        if data_analysis['has_depth_data'] and data_analysis['query_intent'] in ['data_exploration', 'statistical_analysis', 'comprehensive_analysis']:
            if data_analysis['depth_range'] and (data_analysis['depth_range'][1] - data_analysis['depth_range'][0]) > 50:
                decisions['selected_charts'].append('depth_profile')
                decisions['recommendations'].append({
                    'type': 'depth_profile',
                    'chart_type': 'line',
                    'reason': f"Depth range {data_analysis['depth_range'][0]:.0f}m - {data_analysis['depth_range'][1]:.0f}m suitable for profile analysis"
                })
                reasoning_parts.append(f"Depth profile selected: Measurements span {data_analysis['depth_range'][0]:.0f}m to {data_analysis['depth_range'][1]:.0f}m depth")
            else:
                reasoning_parts.append("Depth profile skipped: Insufficient depth variation for meaningful profile")
        elif not data_analysis['has_depth_data']:
            reasoning_parts.append("Depth profile skipped: No sufficient depth measurements available")
        
        # Time series decision logic
        if data_analysis['has_temporal_data'] and data_analysis['query_intent'] in ['temporal_analysis', 'comprehensive_analysis']:
            if data_analysis['time_span_days'] >= self.chart_decision_thresholds['min_time_points']:
                decisions['selected_charts'].append('time_series')
                decisions['recommendations'].append({
                    'type': 'time_series',
                    'chart_type': 'line',
                    'reason': f"Temporal data spanning {data_analysis['time_span_days']} time periods suitable for trend analysis"
                })
                reasoning_parts.append(f"Time series selected: Data spans {data_analysis['time_span_days']} time periods for trend analysis")
            else:
                reasoning_parts.append("Time series skipped: Insufficient temporal variation")
        elif data_analysis['query_intent'] != 'temporal_analysis':
            reasoning_parts.append("Time series skipped: Query doesn't focus on temporal patterns")
        
        # Statistical analysis decision logic
        if query_classification.get('is_analytical') and data_analysis['total_points'] >= 10:
            decisions['selected_charts'].append('statistics')
            decisions['recommendations'].append({
                'type': 'statistics',
                'chart_type': 'statistical_summary',
                'reason': f"Analytical query with {data_analysis['total_points']} points suitable for statistical analysis"
            })
            reasoning_parts.append(f"Statistical analysis selected: Analytical query with {data_analysis['total_points']} data points")
        
        # Ensure at least one visualization is selected ONLY if data quality is sufficient
        if not decisions['selected_charts'] and data_analysis['total_points'] > self.chart_decision_thresholds['min_points_for_map']:
            # Calculate data quality score
            quality_score = self._calculate_data_quality_score(data_analysis)
            
            if quality_score >= self.chart_decision_thresholds['min_data_quality_score']:
                if data_analysis['has_geographic_data']:
                    decisions['selected_charts'].append('map')
                    reasoning_parts.append(f"Map selected as fallback: Geographic data with quality score {quality_score:.2f}")
                elif data_analysis['has_depth_data']:
                    decisions['selected_charts'].append('depth_profile')
                    reasoning_parts.append(f"Depth profile selected as fallback: Depth data with quality score {quality_score:.2f}")
            else:
                reasoning_parts.append(f"No visualizations selected: Data quality score {quality_score:.2f} below threshold {self.chart_decision_thresholds['min_data_quality_score']}")
        elif not decisions['selected_charts']:
            reasoning_parts.append(f"No visualizations selected: Insufficient data points ({data_analysis['total_points']} < {self.chart_decision_thresholds['min_points_for_map']})")
        
        decisions['reasoning'] = ' • '.join(reasoning_parts) if reasoning_parts else 'No suitable visualizations identified for this data'
        
        return decisions
    
    def _calculate_data_quality_score(self, data_analysis: Dict) -> float:
        """Calculate a data quality score (0-1) based on data completeness and diversity"""
        score = 0.0
        
        # Points for having data
        if data_analysis['total_points'] > 0:
            score += 0.2
        
        # Points for geographic diversity
        if data_analysis['has_geographic_data']:
            score += 0.3
            if data_analysis['geographic_spread'] > 1.0:
                score += 0.1  # Bonus for wide geographic distribution
        
        # Points for depth diversity  
        if data_analysis['has_depth_data']:
            score += 0.2
            if data_analysis.get('depth_range') and (data_analysis['depth_range'][1] - data_analysis['depth_range'][0]) > 100:
                score += 0.1  # Bonus for significant depth range
        
        # Points for temporal diversity
        if data_analysis['has_temporal_data']:
            score += 0.2
            if data_analysis['time_span_days'] > 30:
                score += 0.1  # Bonus for longer time spans
        
        # Penalty for very small datasets
        if data_analysis['total_points'] < 5:
            score *= 0.5
        
        return min(1.0, score)
    
    def _build_smart_map_data(self, db_results: List[Dict], data_analysis: Dict) -> Dict:
        """Build map data with intelligent chart type selection"""
        map_data = self._build_map_data(db_results)
        
        if not map_data or map_data.get('total_points', 0) == 0:
            return map_data
        
        # Determine optimal map visualization type
        if data_analysis['total_points'] >= self.chart_decision_thresholds['min_points_for_heatmap']:
            if data_analysis['geographic_spread'] > 2.0:  # Large geographic spread
                map_data['recommended_type'] = 'heatmap'
                map_data['reason'] = 'Large dataset with wide geographic distribution'
            else:
                map_data['recommended_type'] = 'clustered_markers'
                map_data['reason'] = 'Dense point distribution in geographic area'
        else:
            map_data['recommended_type'] = 'scatter_markers'
            map_data['reason'] = 'Individual measurement locations'
        
        return map_data
    
    async def build_visualization(self, db_results: List[Dict], query_classification: Dict, user_query: str = None, context_results: Dict = None) -> Dict:
        """Build intelligent visualization data based on results, query type, and data patterns"""
        
        try:
            if not db_results:
                return {
                    "type": "empty", 
                    "message": "No data available for visualization", 
                    "available_visualizations": [],
                    "reasoning": "No data returned from query",
                    "map": {"type": "scatter", "points": []},
                    "depth_profile": {"type": "line", "data": []}
                }
            
            # First, check if this is a custom chart request
            if user_query:
                print(f"Visualization Builder: Checking if '{user_query}' is a custom chart request")
                custom_chart_result = await self._handle_custom_chart_request(user_query, db_results, query_classification, context_results)
                print(f"Visualization Builder: Custom chart result: {custom_chart_result.get('is_custom_chart', False)}")
                if custom_chart_result.get("is_custom_chart", False):
                    print(f"Visualization Builder: Returning custom chart result")
                    # For custom charts, ensure we still include fallback structures for compatibility
                    if "map" not in custom_chart_result:
                        custom_chart_result["map"] = {"type": "scatter", "points": []}
                    if "depth_profile" not in custom_chart_result:
                        custom_chart_result["depth_profile"] = {"type": "line", "data": []}
                    return custom_chart_result
                else:
                    print(f"Visualization Builder: Not a custom chart, continuing with standard visualization")
            
            # Continue with existing intelligent visualization logic
            # Analyze query and context for intelligent visualization selection
            query_context = self._analyze_query_context(user_query, context_results)
            
            # Analyze data patterns for intelligent chart selection
            data_analysis = self._analyze_data_patterns(db_results, query_classification)
            
            # Make intelligent visualization decisions using both data and context
            visualization_decisions = self._make_smart_visualization_decisions(data_analysis, query_classification, query_context)
            
            # Build visualization data structure
            viz_data = {
                "summary": self._build_summary(db_results),
                "available_visualizations": [],
                "reasoning": visualization_decisions["reasoning"],
                "chart_recommendations": visualization_decisions["recommendations"]
            }
            
            # Build only the recommended visualizations
            for viz_type in visualization_decisions["selected_charts"]:
                try:
                    if viz_type == "map":
                        map_data = self._build_smart_map_data(db_results, data_analysis)
                        if map_data and map_data.get("total_points", 0) > 0:
                            viz_data["map"] = map_data
                            viz_data["available_visualizations"].append("map")
                    
                    elif viz_type == "depth_profile":
                        depth_data = self._build_depth_profile(db_results)
                        if depth_data and depth_data.get("data"):
                            viz_data["depth_profile"] = depth_data
                            viz_data["available_visualizations"].append("depth_profile")
                    
                    elif viz_type == "time_series":
                        time_data = self._build_time_series(db_results)
                        if time_data and time_data.get("data"):
                            viz_data["time_series"] = time_data
                            viz_data["available_visualizations"].append("time_series")
                    
                    elif viz_type == "statistics":
                        stats_data = self._build_statistics(db_results)
                        if stats_data:
                            viz_data["statistics"] = stats_data
                            viz_data["available_visualizations"].append("statistics")
                    
                    elif viz_type == "distributions":
                        dist_data = self._build_distributions(db_results)
                        if dist_data:
                            viz_data["distributions"] = dist_data
                            viz_data["available_visualizations"].append("distributions")
                            
                except Exception as e:
                    print(f"Failed to build {viz_type} visualization: {e}")
            
            # Ensure fallback structures exist
            if "map" not in viz_data:
                viz_data["map"] = {"type": "scatter", "points": []}
            if "depth_profile" not in viz_data:
                viz_data["depth_profile"] = {"type": "line", "data": []}
            
            return viz_data
            
        except Exception as e:
            print(f"Visualization building completely failed: {e}")
            return {
                "type": "error",
                "message": "Visualization data could not be generated",
                "available_visualizations": [],
                "reasoning": "Technical error in visualization processing",
                "map": {"type": "scatter", "points": []},
                "depth_profile": {"type": "line", "data": []}
            }
    
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
                    
                    # Validate coordinate ranges and ensure not fake coordinates
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        continue
                    
                    # Skip fake/zero coordinates
                    if lat == 0.0 and lon == 0.0:
                        continue
                        
                    # Skip fake float IDs
                    float_id = r.get('float_id', '')
                    if (not float_id or 
                        float_id.startswith('float_') or 
                        float_id.startswith('FLOAT_00000')):
                        continue
                    
                    # Only include points with at least some real measurement data (not zero)
                    has_real_measurements = any([
                        r.get('temperature') is not None and r.get('temperature') != 0,
                        r.get('salinity') is not None and r.get('salinity') != 0,
                        r.get('pressure') is not None and r.get('pressure') != 0
                    ])
                    if not has_real_measurements:
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
                    # Skip invalid depths and fake zero depths
                    if depth < 0 or depth > 11000 or depth == 0:  
                        continue
                    
                    # Skip fake float IDs
                    float_id = r.get('float_id', '')
                    if (not float_id or 
                        float_id.startswith('float_') or 
                        float_id.startswith('FLOAT_00000')):
                        continue
                    
                    # Only include if we have actual measurement data (not zero)
                    has_real_measurements = any([
                        r.get('temperature') is not None and r.get('temperature') != 0,
                        r.get('salinity') is not None and r.get('salinity') != 0,
                        r.get('pressure') is not None and r.get('pressure') != 0
                    ])
                    if not has_real_measurements:
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
        for hist_data in histograms.items():
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
    
    async def _handle_custom_chart_request(self, user_query: str, db_results: List[Dict], 
                                          query_classification: Dict, context_results: Dict = None) -> Dict:
        """Handle custom chart requests from users"""
        
        print(f"=== _handle_custom_chart_request called ===")
        print(f"user_query: {user_query}")
        print(f"db_results count: {len(db_results) if db_results else 0}")
        
        # Import here to avoid circular dependency issues
        from query_classifier import QueryClassifier
        
        # Check if this is a chart request
        classifier = QueryClassifier()
        chart_classification = classifier.classify_chart_request(user_query)
        print(f"Chart classification for '{user_query}': {chart_classification}")
        
        if not chart_classification.get("is_chart_request", False):
            print(f"Not detected as chart request, returning False")
            return {"is_custom_chart": False}
        
        print(f"Detected as chart request! Processing with chart processor...")
        print(f"Available data: {len(db_results)} results")
        
        try:
            # Process the chart request
            session_context = getattr(context_results, 'session_context', None) if context_results else None
            chart_result = await self.chart_request_processor.process_chart_request(
                user_query, chart_classification, db_results, session_context
            )
            
            if not chart_result.get("success", False):
                # Return error message but continue with standard visualizations
                return {
                    "is_custom_chart": True,
                    "type": "custom_chart_error",
                    "message": chart_result.get("message", "Could not generate requested chart"),
                    "available_visualizations": [],
                    "reasoning": f"Custom chart request failed: {chart_result.get('reason', 'Unknown error')}",
                    "map": {"type": "scatter", "points": []},
                    "depth_profile": {"type": "line", "data": []}
                }
            
            # Successfully generated custom chart
            chart_config = chart_result["chart_config"]
            chart_message = chart_result.get("message", "Custom chart generated")
            
            return {
                "is_custom_chart": True,
                "type": "custom_chart",
                "message": chart_message,
                "available_visualizations": ["custom_chart"],
                "reasoning": f"Generated custom chart: {chart_result['refined_request'].get('explanation', 'Chart created as requested')}",
                "custom_chart": chart_config,
                "chart_request_info": chart_result["refined_request"],
                # Include fallback structures
                "map": {"type": "scatter", "points": []},
                "depth_profile": {"type": "line", "data": []}
            }
            
        except Exception as e:
            print(f"Custom chart processing error: {e}")
            return {
                "is_custom_chart": True,
                "type": "custom_chart_error",
                "message": f"I encountered an issue creating your custom chart: {str(e)}. Let me show you the standard visualizations instead.",
                "available_visualizations": [],
                "reasoning": f"Custom chart generation failed with error: {str(e)}",
                "map": {"type": "scatter", "points": []},
                "depth_profile": {"type": "line", "data": []}
            }