"""
Chart Request Processor Module
Processes user chart requests and generates intelligent chart configurations for oceanographic data.
"""

import os
import math
from typing import Dict, List
from dotenv import load_dotenv

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

load_dotenv()


class ChartRequestProcessor:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash")
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel(self.gemini_model)
                self.use_gemini = True
                print(f"Chart Request Processor: Gemini enabled with model {self.gemini_model}")
            except Exception as e:
                print(f"Chart Request Processor: Failed to initialize Gemini: {e}")
                self.use_gemini = False
        else:
            self.use_gemini = False
            print("Chart Request Processor: Using rule-based processing only")

        # Chart type specifications
        self.supported_chart_types = {
            'time_series': {
                'description': 'Show how parameters change over time',
                'required_fields': ['time', 'parameter'],
                'plotly_type': 'scatter',
                'mode': 'lines+markers'
            },
            'scatter': {
                'description': 'Compare two parameters against each other',
                'required_fields': ['x_parameter', 'y_parameter'],
                'plotly_type': 'scatter',
                'mode': 'markers'
            },
            'line': {
                'description': 'Show trends or connections between data points',
                'required_fields': ['x_parameter', 'y_parameter'],
                'plotly_type': 'scatter',
                'mode': 'lines+markers'
            },
            'histogram': {
                'description': 'Show distribution of a parameter',
                'required_fields': ['parameter'],
                'plotly_type': 'histogram',
                'mode': None
            },
            'bar': {
                'description': 'Compare values between categories',
                'required_fields': ['category', 'value'],
                'plotly_type': 'bar',
                'mode': None
            }
        }

    async def process_chart_request(self, user_query: str, chart_classification: Dict, 
                                  db_results: List[Dict], session_context: dict = None) -> Dict:
        """Process a chart request and generate chart configuration"""
        
        if not chart_classification.get("is_chart_request", False):
            return {"success": False, "reason": "Not a chart request"}
        
        if not db_results:
            return {
                "success": False, 
                "reason": "No data available for chart generation",
                "message": "I'd love to create a chart for you, but I don't have any data to work with. Try asking me to find some oceanographic data first."
            }

        try:
            # Use AI to understand and refine the chart request
            if self.use_gemini:
                refined_request = await self._refine_request_with_ai(
                    user_query, chart_classification, db_results, session_context
                )
            else:
                refined_request = self._refine_request_rule_based(
                    user_query, chart_classification, db_results
                )

            if not refined_request.get("success", False):
                return refined_request

            # Generate chart configuration
            chart_config = self._generate_chart_config(refined_request, db_results)
            
            return {
                "success": True,
                "chart_config": chart_config,
                "refined_request": refined_request,
                "message": refined_request.get("explanation", "Chart generated successfully")
            }

        except Exception as e:
            print(f"Chart request processing error: {e}")
            return {
                "success": False,
                "reason": "Processing error",
                "message": f"I encountered an issue creating your chart: {str(e)}. Could you try rephrasing your request?"
            }

    async def _refine_request_with_ai(self, user_query: str, chart_classification: Dict, 
                                     db_results: List[Dict], session_context: dict = None) -> Dict:
        """Use AI to understand and refine the chart request"""
        
        # Prepare context about available data
        data_summary = self._prepare_data_summary(db_results)
        chart_info = self._format_chart_classification(chart_classification)
        session_info = self._format_session_context(session_context) if session_context else ""
        
        # Build prompt for AI
        prompt = f"""You are an expert oceanographer and data visualization specialist. A user wants to create a chart from ARGO oceanographic data.

User Request: "{user_query}"

Chart Classification: {chart_info}

Available Data Summary:
{data_summary}

{session_info}

Your task is to:
1. Understand exactly what chart the user wants
2. Determine if it's possible with the available data
3. Suggest the best chart type and configuration

Respond in JSON format with these fields:
{{
    "success": boolean,
    "chart_type": "time_series|scatter|line|histogram|bar",
    "x_axis": "parameter name or 'time' or 'depth'",
    "y_axis": "parameter name",
    "title": "Clear, descriptive chart title",
    "explanation": "Brief explanation of what you'll show",
    "filters": {{"any specific data filters needed"}},
    "reason": "if success is false, explain why"
}}

Focus on creating charts that oceanographers would find valuable. Common patterns:
- Temperature vs time (time series)
- Temperature vs salinity (T-S diagrams - scatter)
- Temperature vs depth (profiles - line)
- Parameter distributions (histograms)

If the data doesn't support the requested chart, suggest alternatives."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )
            
            # Enhanced response validation and safety handling
            if response:
                # Check if response was blocked or filtered
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        if finish_reason in [2, 3, 4]:  # SAFETY, RECITATION, OTHER
                            print(f"Chart Request Processor: Response blocked (reason: {finish_reason}), using rule-based approach")
                            return self._refine_request_rule_based(user_query, chart_classification, db_results)
                
                # Try to get text, handle various response structures
                response_text = None
                try:
                    if hasattr(response, 'text') and response.text:
                        response_text = response.text
                    elif hasattr(response, 'candidates') and response.candidates:
                        # Try to get text from first candidate
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        response_text = part.text
                                        break
                except Exception as text_extract_error:
                    print(f"Chart Request Processor: Error extracting text from response: {text_extract_error}")
                
                # Parse JSON response if we have text
                if response_text and len(response_text.strip()) > 5:
                    import json
                    try:
                        # Clean up the response text
                        cleaned_response = response_text.strip()
                        
                        # Remove any markdown code blocks if present
                        if cleaned_response.startswith('```json'):
                            cleaned_response = cleaned_response[7:]
                        if cleaned_response.endswith('```'):
                            cleaned_response = cleaned_response[:-3]
                        cleaned_response = cleaned_response.strip()
                        
                        result = json.loads(cleaned_response)
                        return result
                    except json.JSONDecodeError as json_error:
                        # Fallback to rule-based if JSON parsing fails
                        print(f"AI response was not valid JSON: {json_error}, falling back to rule-based")
                        print(f"Response text was: {response_text[:200]}...")
                        return self._refine_request_rule_based(user_query, chart_classification, db_results)
                else:
                    print("Chart Request Processor: Empty or very short response, using rule-based approach")
                    return self._refine_request_rule_based(user_query, chart_classification, db_results)
            else:
                print("Chart Request Processor: No response from Gemini, using rule-based approach")
                return self._refine_request_rule_based(user_query, chart_classification, db_results)
                
        except Exception as e:
            print(f"AI refinement failed: {e}")
            return self._refine_request_rule_based(user_query, chart_classification, db_results)

    def _refine_request_rule_based(self, user_query: str, chart_classification: Dict, 
                                  db_results: List[Dict]) -> Dict:
        """Fallback rule-based chart request refinement"""
        
        chart_type = chart_classification.get("chart_type", "line")
        parameters = chart_classification.get("parameters", [])
        x_axis = chart_classification.get("x_axis")
        y_axis = chart_classification.get("y_axis")
        
        # Validate data availability
        available_params = self._get_available_parameters(db_results)
        
        # Handle time series requests
        if chart_type == "time_series" or x_axis == "time":
            if not self._has_temporal_data(db_results):
                return {
                    "success": False,
                    "reason": "No temporal data available",
                    "message": "I can't create a time series chart because the data doesn't have sufficient time information. Would you like to see a different type of visualization?"
                }
            
            y_param = y_axis or (parameters[0] if parameters else 'temperature')
            if y_param not in available_params:
                y_param = available_params[0] if available_params else 'temperature'
            
            return {
                "success": True,
                "chart_type": "time_series",
                "x_axis": "time",
                "y_axis": y_param,
                "title": f"{y_param.title()} Over Time",
                "explanation": f"Showing how {y_param} changes over time in your data"
            }
        
        # Handle scatter plots
        elif chart_type == "scatter":
            if len(parameters) < 2:
                # Default to temperature vs salinity if available
                if 'temperature' in available_params and 'salinity' in available_params:
                    return {
                        "success": True,
                        "chart_type": "scatter",
                        "x_axis": "salinity",
                        "y_axis": "temperature", 
                        "title": "Temperature vs Salinity (T-S Diagram)",
                        "explanation": "T-S diagrams are fundamental in oceanography for identifying water masses"
                    }
                elif len(available_params) >= 2:
                    return {
                        "success": True,
                        "chart_type": "scatter",
                        "x_axis": available_params[0],
                        "y_axis": available_params[1],
                        "title": f"{available_params[1].title()} vs {available_params[0].title()}",
                        "explanation": f"Comparing {available_params[1]} against {available_params[0]}"
                    }
                else:
                    return {
                        "success": False,
                        "reason": "Insufficient parameters for scatter plot",
                        "message": "I need at least two different parameters to create a scatter plot. Your data seems to have limited parameter variety."
                    }
            
            x_param = x_axis or parameters[0]
            y_param = y_axis or parameters[1]
            
            return {
                "success": True,
                "chart_type": "scatter",
                "x_axis": x_param,
                "y_axis": y_param,
                "title": f"{y_param.title()} vs {x_param.title()}",
                "explanation": f"Showing the relationship between {y_param} and {x_param}"
            }
        
        # Handle histograms
        elif chart_type == "histogram":
            param = parameters[0] if parameters else 'temperature'
            if param not in available_params:
                param = available_params[0] if available_params else 'temperature'
                
            return {
                "success": True,
                "chart_type": "histogram",
                "x_axis": param,
                "y_axis": "frequency",
                "title": f"Distribution of {param.title()}",
                "explanation": f"Showing the distribution of {param} values in your data"
            }
        
        # Default to line chart
        else:
            param = parameters[0] if parameters else 'temperature'
            if param not in available_params:
                param = available_params[0] if available_params else 'temperature'
                
            if 'depth' in available_params:
                return {
                    "success": True,
                    "chart_type": "line",
                    "x_axis": param,
                    "y_axis": "depth",
                    "title": f"{param.title()} Profile by Depth",
                    "explanation": f"Showing how {param} varies with depth"
                }
            else:
                return {
                    "success": True,
                    "chart_type": "line",
                    "x_axis": "measurement_index",
                    "y_axis": param,
                    "title": f"{param.title()} Values",
                    "explanation": f"Showing {param} values across measurements"
                }

    def _generate_chart_config(self, refined_request: Dict, db_results: List[Dict]) -> Dict:
        """Generate Plotly.js chart configuration"""
        
        chart_type = refined_request["chart_type"]
        x_axis = refined_request["x_axis"]
        y_axis = refined_request["y_axis"]
        title = refined_request["title"]
        
        # Prepare data for chart
        chart_data = self._prepare_chart_data(db_results, x_axis, y_axis, chart_type)
        
        # Get chart specifications
        spec = self.supported_chart_types.get(chart_type, self.supported_chart_types['line'])
        
        # Build Plotly configuration
        config = {
            "data": [{
                "x": chart_data["x"],
                "y": chart_data["y"],
                "type": spec["plotly_type"],
                "mode": spec["mode"],
                "name": f"{y_axis.title()} vs {x_axis.title()}",
                "marker": {
                    "size": 8 if spec["mode"] and "markers" in spec["mode"] else None,
                    "color": "#1f77b4",
                    "line": {"width": 1, "color": "#ffffff"} if spec["mode"] and "markers" in spec["mode"] else None
                },
                "line": {
                    "width": 2,
                    "color": "#1f77b4"
                } if spec["mode"] and "lines" in spec["mode"] else None
            }],
            "layout": {
                "title": {
                    "text": title,
                    "font": {"size": 16, "color": "#1f2937"}
                },
                "xaxis": {
                    "title": {"text": self._get_axis_label(x_axis), "font": {"size": 12}},
                    "showgrid": True,
                    "gridcolor": "#e5e7eb",
                    "color": "#374151"
                },
                "yaxis": {
                    "title": {"text": self._get_axis_label(y_axis), "font": {"size": 12}},
                    "showgrid": True,
                    "gridcolor": "#e5e7eb",
                    "color": "#374151",
                    "autorange": "reversed" if y_axis == "depth" else True  # Oceanographic convention for depth
                },
                "plot_bgcolor": "#f9fafb",
                "paper_bgcolor": "white",
                "hovermode": "closest",
                "showlegend": False,
                "margin": {"l": 60, "r": 40, "t": 60, "b": 60}
            },
            "config": {
                "responsive": True,
                "displayModeBar": True,
                "displaylogo": False,
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "custom_chart",
                    "height": 500,
                    "width": 800,
                    "scale": 1
                }
            }
        }
        
        return config

    def _prepare_chart_data(self, db_results: List[Dict], x_axis: str, y_axis: str, chart_type: str) -> Dict:
        """Extract and prepare data for charting"""
        
        x_data = []
        y_data = []
        
        if not db_results or not isinstance(db_results, list):
            return {"x": x_data, "y": y_data}
        
        for record in db_results:
            if not record or not isinstance(record, dict):
                continue
                
            try:
                x_val = None
                y_val = None
                
                # Handle x-axis data
                if x_axis == "time":
                    x_val = record.get("date")
                    if x_val:
                        # Better date handling
                        if isinstance(x_val, str) and len(x_val) >= 10:
                            x_data.append(x_val[:10])
                        else:
                            x_data.append(str(x_val)[:10])
                    else:
                        continue
                elif x_axis == "measurement_index":
                    x_val = len(x_data)  # Use index
                    x_data.append(x_val)
                else:
                    x_val = record.get(x_axis)
                    if x_val is not None:
                        # Better numeric validation
                        try:
                            x_numeric = float(x_val)
                            if not (math.isnan(x_numeric) or math.isinf(x_numeric)):
                                x_data.append(x_numeric)
                            else:
                                continue
                        except (ValueError, TypeError):
                            continue
                    else:
                        continue
                
                # Handle y-axis data
                if y_axis == "frequency":
                    continue  # Handle histogram separately
                else:
                    y_val = record.get(y_axis)
                    if y_val is not None:
                        try:
                            y_numeric = float(y_val)
                            if not (math.isnan(y_numeric) or math.isinf(y_numeric)):
                                y_data.append(y_numeric)
                            else:
                                x_data.pop() if x_data else None  # Remove corresponding x value
                                continue
                        except (ValueError, TypeError):
                            x_data.pop() if x_data else None  # Remove corresponding x value
                            continue
                    else:
                        x_data.pop() if x_data else None  # Remove corresponding x value
                        continue
                        
            except Exception as e:
                print(f"Error processing chart data point: {e}")
                # Skip invalid data points
                continue
        
        # Ensure equal length arrays
        min_length = min(len(x_data), len(y_data))
        return {"x": x_data[:min_length], "y": y_data[:min_length]}

    def _get_axis_label(self, axis: str) -> str:
        """Get formatted axis label"""
        labels = {
            "temperature": "Temperature (°C)",
            "salinity": "Salinity (PSU)",
            "pressure": "Pressure (dbar)",
            "depth": "Depth (m)",
            "time": "Date",
            "measurement_index": "Measurement #",
            "frequency": "Frequency"
        }
        return labels.get(axis, axis.title())

    def _prepare_data_summary(self, db_results: List[Dict]) -> str:
        """Prepare a summary of available data for AI context"""
        if not db_results:
            return "No data available"
        
        available_params = self._get_available_parameters(db_results)
        has_time = self._has_temporal_data(db_results)
        has_location = any(r.get('latitude') and r.get('longitude') for r in db_results)
        
        summary = [
            f"Total records: {len(db_results)}",
            f"Available parameters: {', '.join(available_params)}",
            f"Temporal data: {'Yes' if has_time else 'No'}",
            f"Location data: {'Yes' if has_location else 'No'}"
        ]
        
        # Add ranges for key parameters
        for param in ['temperature', 'salinity', 'depth']:
            values = [r.get(param) for r in db_results if r.get(param) is not None]
            if values:
                summary.append(f"{param.title()} range: {min(values):.2f} to {max(values):.2f}")
        
        return "\n".join(summary)

    def _format_chart_classification(self, classification: Dict) -> str:
        """Format chart classification for AI context"""
        return f"""
Detected chart type: {classification.get('chart_type', 'unknown')}
Parameters mentioned: {', '.join(classification.get('parameters', []))}
X-axis: {classification.get('x_axis', 'not specified')}
Y-axis: {classification.get('y_axis', 'not specified')}
Confidence: {classification.get('confidence', 0):.2f}
"""

    def _format_session_context(self, session_context: dict) -> str:
        """Format session context for AI"""
        if not session_context:
            return ""
        
        recent_queries = session_context.get('recent_exchanges', [])
        context_parts = ["Recent conversation context:"]
        
        for exchange in recent_queries[-2:]:  # Last 2 exchanges
            user_q = exchange.get('user_query', '')
            if user_q:
                context_parts.append(f"- User asked: {user_q}")
        
        return "\n".join(context_parts) if len(context_parts) > 1 else ""

    def _get_available_parameters(self, db_results: List[Dict]) -> List[str]:
        """Get list of available parameters in the data"""
        if not db_results:
            return []
        
        params = []
        sample_record = db_results[0]
        
        for param in ['temperature', 'salinity', 'pressure', 'depth']:
            if any(record.get(param) is not None for record in db_results):
                params.append(param)
        
        return params

    def _has_temporal_data(self, db_results: List[Dict]) -> bool:
        """Check if data has meaningful temporal information"""
        if not db_results:
            return False
        
        dates = [r.get('date') for r in db_results if r.get('date')]
        if len(dates) < 2:
            return False
        
        # Check if we have multiple different dates
        unique_dates = set(str(d)[:10] if isinstance(d, str) else str(d)[:10] for d in dates)
        return len(unique_dates) > 1