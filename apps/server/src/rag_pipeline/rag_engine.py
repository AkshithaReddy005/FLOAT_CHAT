"""
RAG Engine Module
Orchestrates the RAG (Retrieval-Augmented Generation) workflow using Gemini API.
"""

import os
from typing import Dict, List
from dotenv import load_dotenv

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

load_dotenv()


class RAGEngine:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv("GEMINI_RAG_MODEL", "gemini-2.0-flash")
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel(self.gemini_model)
                self.use_gemini = True
                print(f"RAG Engine: Gemini enabled with model {self.gemini_model}")
            except Exception as e:
                print(f"RAG Engine: Failed to initialize Gemini: {e}")
                self.use_gemini = False
        else:
            self.use_gemini = False
            print("RAG Engine: Using rule-based responses only")
    
    async def generate_response(self, user_query: str, context_results: Dict, 
                               db_results: List[Dict], query_classification: Dict, session_context: dict = None, is_chart_request: bool = False) -> str:
        """Generate comprehensive response using RAG approach with session context"""
        
        # Handle chart requests specially
        if is_chart_request:
            return self._generate_chart_request_response(user_query, db_results, query_classification)
        
        if self.use_gemini:
            try:
                return await self._generate_with_rag(user_query, context_results, db_results, query_classification, session_context)
            except Exception as e:
                print(f"RAG Engine: Gemini failed: {e}, falling back to rule-based")
                return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
        else:
            return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
    
    async def _generate_with_rag(self, user_query: str, context_results: Dict,
                                db_results: List[Dict], query_classification: Dict, session_context: dict = None) -> str:
        """Generate response using Retrieval-Augmented Generation with Gemini"""
        
        # Prepare context from ChromaDB with increased context for better analysis
        context_docs = context_results.get('documents', [[]])[0][:8] if context_results.get('documents') else []
        context_text = self._format_context(context_docs)
        
        # Prepare data summary
        data_summary = self._prepare_data_summary(db_results)
        
        # Prepare query classification info
        classification_info = self._format_classification(query_classification)
        
        # Prepare session context summary
        session_summary = self._format_session_context(session_context)
        
        # Build RAG prompt
        prompt = self._build_rag_prompt(user_query, context_text, data_summary, classification_info, session_summary)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1200  # Increased for more comprehensive responses
                )
            )
            
            # Enhanced response validation and safety handling
            if response:
                # Check if response was blocked or filtered
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        if finish_reason == 2:  # SAFETY
                            print("RAG Engine: Response blocked by safety filters, using fallback")
                            return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
                        elif finish_reason == 3:  # RECITATION  
                            print("RAG Engine: Response blocked by recitation filters, using fallback")
                            return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
                        elif finish_reason == 4:  # OTHER
                            print("RAG Engine: Response blocked for other reasons, using fallback")
                            return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
                
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
                    print(f"RAG Engine: Error extracting text from response: {text_extract_error}")
                
                # Validate extracted text
                if response_text and len(response_text.strip()) > 10:
                    return response_text.strip()
                else:
                    print("RAG Engine: Gemini returned empty or very short response, using fallback")
                    return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
            else:
                print("RAG Engine: No response from Gemini, using fallback")
                return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
                
        except Exception as e:
            print(f"RAG Engine: Gemini API error: {e}")
            return self._generate_rule_based_response(user_query, db_results, query_classification, session_context)
    
    def _build_rag_prompt(self, user_query: str, context_text: str, 
                         data_summary: str, classification_info: str, session_summary: str = "") -> str:
        """Build comprehensive RAG prompt"""
        
        session_section = f"""
Previous Conversation Context:
{session_summary}
""" if session_summary else ""
        
        return f"""You are FloatChat, a friendly and knowledgeable AI assistant for ARGO oceanographic data. You help users understand ocean measurements through natural conversation and clear explanations.

User Query: "{user_query}"
{session_section}
Available Data Context:
{context_text}

Query Results:
{data_summary}

RESPONSE GUIDELINES:
🌊 **Be Conversational**: Respond naturally, like talking to a colleague. Use "I found..." or "Based on the data..." instead of formal structures.

🔍 **Balance Helpfulness with Honesty**: 
- If you have good data, share insights enthusiastically
- If data is limited, explain what you can see and suggest alternatives
- For simple questions, provide simple answers
- For complex requests, dive deeper into analysis

💬 **Flexible Communication**:
- Match the user's tone (casual questions → casual answers, technical requests → detailed analysis)  
- Don't force structured formats unless the query is complex
- Use bullet points only when listing multiple items makes sense
- Feel free to ask follow-up questions to help better

📊 **Data Transparency**:
- When you have relevant data, share it with confidence
- When data is sparse, explain what's available and suggest related queries
- If no data matches, suggest similar or nearby measurements

🤝 **Be Helpful**:
- Offer practical suggestions and next steps
- Share interesting patterns you notice
- Connect findings to broader oceanographic context when relevant
- Don't be overly cautious - users want insights, not disclaimers

Remember: You're here to help users explore ocean data. Be informative, friendly, and genuinely useful. If a question is simple, keep your answer simple. If it's complex, provide the depth they're looking for."""
    
    def _format_context(self, context_docs: List[str]) -> str:
        """Format context documents for the prompt"""
        if not context_docs:
            return "No specific context found in knowledge base."
        
        # Clean and format context
        formatted_context = []
        for i, doc in enumerate(context_docs[:3], 1):  # Limit to top 3 most relevant
            # Clean the document text
            cleaned_doc = doc.strip()
            if cleaned_doc and len(cleaned_doc) > 20:  # Only include substantial content
                formatted_context.append(f"{i}. {cleaned_doc}")
        
        if not formatted_context:
            return "No relevant context found in knowledge base."
        elif len(formatted_context) == 1 and len(formatted_context[0]) < 100:
            return f"Limited context available: {formatted_context[0]}"
        else:
            return "\n".join(formatted_context)
    
    def _prepare_data_summary(self, db_results: List[Dict]) -> str:
        """Prepare a comprehensive summary of the data results"""
        if not db_results:
            return "No data found matching the query criteria."
        
        summary_parts = [f"Found {len(db_results)} measurements"]
        
        # Temperature analysis
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        if temps:
            avg_temp = sum(temps) / len(temps)
            min_temp, max_temp = min(temps), max(temps)
            summary_parts.append(
                f"Temperature range: {min_temp:.2f}°C to {max_temp:.2f}°C (average: {avg_temp:.2f}°C)"
            )
        
        # Salinity analysis
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        if salinities:
            avg_sal = sum(salinities) / len(salinities)
            min_sal, max_sal = min(salinities), max(salinities)
            summary_parts.append(
                f"Salinity range: {min_sal:.2f} to {max_sal:.2f} (average: {avg_sal:.2f})"
            )
        
        # Depth analysis
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        if depths:
            min_depth, max_depth = min(depths), max(depths)
            summary_parts.append(f"Depth range: {min_depth:.1f}m to {max_depth:.1f}m")
        
        # Float information
        unique_floats = len(set(r['float_id'] for r in db_results))
        summary_parts.append(f"Data from {unique_floats} different ARGO floats")
        
        # Temporal information
        dates = [r['date'] for r in db_results if r['date']]
        if dates:
            date_strs = [str(d)[:10] for d in dates]
            unique_dates = len(set(date_strs))
            summary_parts.append(f"Spanning {unique_dates} different dates")
        
        return ". ".join(summary_parts) + "."
    
    def _format_classification(self, query_classification: Dict) -> str:
        """Format query classification information"""
        classification_parts = []
        
        if query_classification.get("needs_data"):
            classification_parts.append("Data query detected")
        
        if query_classification.get("is_analytical"):
            classification_parts.append("Analytical query requiring statistical analysis")
        
        if query_classification.get("has_temporal"):
            classification_parts.append("Temporal analysis requested")
        
        if query_classification.get("has_spatial"):
            classification_parts.append("Spatial/geographic analysis requested")
        
        complexity = query_classification.get("complexity_level", "simple")
        classification_parts.append(f"Query complexity: {complexity}")
        
        return ". ".join(classification_parts) + "." if classification_parts else "General query."
    
    def _format_session_context(self, session_context: dict = None) -> str:
        """Format session context for the prompt with enhanced intelligence"""
        if not session_context:
            return ""
        
        context_parts = []
        
        # Add conversation summary with focus on continuity
        if session_context.get('conversation_summary'):
            context_parts.append(f"Conversation Flow: {session_context['conversation_summary']}")
        
        # Add intelligent recent exchanges analysis
        recent_exchanges = session_context.get('recent_exchanges', [])
        if recent_exchanges:
            context_parts.append("Recent Context:")
            
            # Analyze patterns in recent exchanges
            topics_discussed = set()
            depth_queries = []
            location_focus = []
            
            for exchange in recent_exchanges[-3:]:  # Last 3 exchanges
                user_q = exchange.get('user_query', '').lower()
                ai_summary = exchange.get('ai_response_summary', '')
                
                # Extract topics
                if 'temperature' in user_q:
                    topics_discussed.add('temperature analysis')
                if 'salinity' in user_q:
                    topics_discussed.add('salinity analysis')
                if 'depth' in user_q or 'deep' in user_q:
                    topics_discussed.add('depth analysis')
                
                # Extract depth patterns
                import re
                depth_matches = re.findall(r'(?:below|above|at)\s*(\d+)\s*m', user_q)
                if depth_matches:
                    depth_queries.extend([f"{match}m depth" for match in depth_matches])
                
                # Extract location continuity
                if any(loc in user_q for loc in ['mumbai', 'arabian', 'indian']):
                    location_focus.append('regional analysis')
            
            # Add contextual summary
            if topics_discussed:
                context_parts.append(f"  Focus areas: {', '.join(topics_discussed)}")
            if depth_queries:
                context_parts.append(f"  Depth interests: {', '.join(depth_queries[-2:])}")
            if location_focus:
                context_parts.append(f"  Geographic continuity: studying regional patterns")
        
        # Add enhanced key context with analytical insights
        key_context = session_context.get('key_context', {})
        if key_context:
            analytical_context = []
            
            # Location continuity analysis
            locations = key_context.get('locations', [])
            if locations:
                unique_regions = set()
                for loc in locations[-5:]:  # Recent locations
                    loc_lower = loc.lower()
                    if 'mumbai' in loc_lower or 'arabian' in loc_lower:
                        unique_regions.add('Arabian Sea region')
                    elif 'indian' in loc_lower:
                        unique_regions.add('Indian Ocean')
                    elif 'bay' in loc_lower:
                        unique_regions.add('Bay of Bengal')
                
                if unique_regions:
                    analytical_context.append(f"Regional focus: {', '.join(unique_regions)}")
                else:
                    analytical_context.append(f"Geographic context: {', '.join(locations[-2:])}")
            
            # Data type patterns
            data_types = key_context.get('data_types', [])
            if data_types:
                # Categorize data types
                measurement_types = []
                depth_references = []
                
                for dt in data_types[-5:]:
                    if dt.lower() in ['temperature', 'salinity', 'pressure']:
                        measurement_types.append(dt.lower())
                    elif 'm' in dt and any(word in dt for word in ['below', 'above', 'at']):
                        depth_references.append(dt)
                
                if measurement_types:
                    analytical_context.append(f"Parameters of interest: {', '.join(set(measurement_types))}")
                if depth_references:
                    analytical_context.append(f"Depth context: {', '.join(depth_references[-2:])}")
            
            # Recent focus with continuity hints
            recent_focus = key_context.get('recent_focus', [])
            if recent_focus:
                # Look for continuation patterns
                last_query = recent_focus[-1].lower() if recent_focus else ""
                if any(word in last_query for word in ['below', 'above', 'deeper', 'shallower', 'there', 'same']):
                    analytical_context.append("Query pattern: Building on previous depth/location context")
                elif len(recent_focus) > 1:
                    analytical_context.append(f"Exploration pattern: Progressive analysis in {len(recent_focus)} queries")
            
            if analytical_context:
                context_parts.append("Analytical Context: " + " • ".join(analytical_context))
        
        # Add query continuity hints
        continuity_hints = self._extract_continuity_hints(session_context)
        if continuity_hints:
            context_parts.append(f"Continuity Hints: {continuity_hints}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _extract_continuity_hints(self, session_context: dict) -> str:
        """Extract hints about query continuity and context dependencies"""
        hints = []
        
        # Check for recent location establishment
        key_context = session_context.get('key_context', {})
        locations = key_context.get('locations', [])
        data_types = key_context.get('data_types', [])
        recent_focus = key_context.get('recent_focus', [])
        
        # Location continuity
        if locations:
            last_location = locations[-1].lower()
            if 'mumbai' in last_location or 'arabian' in last_location:
                hints.append("Arabian Sea region established as focus area")
            elif 'indian' in last_location:
                hints.append("Indian Ocean context established")
        
        # Parameter continuity
        if data_types:
            recent_params = [dt for dt in data_types[-3:] if dt.lower() in ['temperature', 'salinity', 'pressure', 'depth']]
            if len(set(recent_params)) > 1:
                hints.append("Multi-parameter analysis in progress")
            elif recent_params:
                hints.append(f"{recent_params[-1]} analysis established")
        
        # Depth progression patterns
        if recent_focus:
            last_query = recent_focus[-1].lower()
            if 'below' in last_query or 'deeper' in last_query:
                hints.append("Depth progression: exploring deeper waters")
            elif 'above' in last_query or 'surface' in last_query:
                hints.append("Depth progression: focusing on surface waters")
        
        return " • ".join(hints) if hints else ""
    
    def _generate_rule_based_response(self, user_query: str, db_results: List[Dict], 
                                    query_classification: Dict, session_context: dict = None) -> str:
        """Generate response using rule-based approach when LLM is not available"""
        
        # Handle the case with no data
        if not db_results:
            return self._generate_no_data_response(user_query)
        
        # Handle case with data
        try:
            # Statistical summary
            count = len(db_results)
            unique_floats = len(set(r.get('float_id', 'unknown') for r in db_results))
            temps = [r['temperature'] for r in db_results if r.get('temperature') is not None]
            salinities = [r['salinity'] for r in db_results if r.get('salinity') is not None]
            depths = [r['depth'] for r in db_results if r.get('depth') is not None]
            
            # Build conversational response
            response_parts = []
            
            # Friendly opening
            response_parts.append(f"Great! I found {count} ARGO measurements from {unique_floats} different floats that match what you're looking for.")
            
            # Key findings in natural language
            findings = []
            if temps:
                avg_temp = sum(temps) / len(temps)
                min_temp, max_temp = min(temps), max(temps)
                findings.append(f"Temperature ranges from {min_temp:.1f}°C to {max_temp:.1f}°C (average: {avg_temp:.1f}°C)")
            
            if salinities:
                avg_sal = sum(salinities) / len(salinities)
                min_sal, max_sal = min(salinities), max(salinities)
                findings.append(f"Salinity values span {min_sal:.2f} to {max_sal:.2f} (average: {avg_sal:.2f})")
            
            if depths:
                min_depth, max_depth = min(depths), max(depths)
                findings.append(f"Measurements taken from {min_depth:.0f}m to {max_depth:.0f}m depth")
            
            if findings:
                response_parts.append("Here's what I found:\n\n" + "\n".join([f"• {finding}" for finding in findings]))
            
            # Add some insight
            insights = []
            if depths:
                if max_depth > 1000:
                    insights.append("The data includes deep ocean measurements, which is great for understanding deep water properties and ocean circulation patterns.")
                elif max_depth > 200:
                    insights.append("This covers both surface and mid-depth waters, giving you a nice view of the vertical ocean structure.")
                else:
                    insights.append("The measurements focus on surface and near-surface waters, perfect for studying upper ocean conditions.")
            
            if insights:
                response_parts.append("\n" + insights[0])
            
            # Encourage exploration
            response_parts.append("\nYou can explore the data further using the interactive maps and depth profiles below. Feel free to ask me more specific questions about what you see!")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            print(f"Error in rule-based response generation: {e}")
            # Emergency fallback
            return self._generate_emergency_fallback_response(user_query, db_results)

    def _generate_no_data_response(self, user_query: str) -> str:
        """Generate a helpful response when no data is found"""
        
        return (
            f"I understand you're asking about '{user_query}'. While I couldn't find specific ARGO measurements "
            f"that exactly match your query, this doesn't mean the data doesn't exist! Here are some possibilities:\n\n"
            f"• **Geographic Coverage**: The location you're interested in might not be covered by our current ARGO float network\n"
            f"• **Time Period**: The specific dates you mentioned might not have available data yet\n"
            f"• **Parameter Combination**: The exact combination of measurements you're looking for might require a different search approach\n\n"
            f"**Here's what you can try:**\n"
            f"• Broaden your search area or time range\n"
            f"• Ask about nearby regions or similar ocean areas\n"
            f"• Check what data is available using questions like 'What recent data do you have?'\n"
            f"• Try asking about related measurements or parameters\n\n"
            f"Our ARGO database contains temperature, salinity, pressure, and depth measurements from oceanographic floats "
            f"across various ocean regions. I'm here to help you explore what's available - just ask me about what "
            f"data we have or try a slightly different question!"
        )

    def _generate_emergency_fallback_response(self, user_query: str, db_results: List[Dict]) -> str:
        """Emergency fallback when even rule-based response fails"""
        
        count = len(db_results) if db_results else 0
        
        if count > 0:
            return (
                f"I found {count} ARGO measurements related to your query '{user_query}'. "
                f"While I'm experiencing some technical difficulties with detailed analysis, "
                f"you can explore this oceanographic data using the interactive visualizations below. "
                f"The data includes temperature, salinity, depth, and pressure measurements from ARGO floats. "
                f"Try asking more specific questions about what you see in the visualizations!"
            )
        else:
            return (
                f"I understand you're asking about '{user_query}'. While I'm having some technical difficulties "
                f"with data analysis, our system contains ARGO oceanographic measurements including temperature, "
                f"salinity, depth, and pressure data from various ocean regions. Please try asking about specific "
                f"locations, recent measurements, or available data. I'll do my best to help you explore the data!"
            )
    
    def generate_response_summary(self, response_text: str, db_results: List[Dict], query_classification: Dict) -> str:
        """Generate a concise summary of the AI response for session context"""
        
        # Extract key information from the response and data
        summary_parts = []
        
        # Basic data info
        if db_results:
            count = len(db_results)
            summary_parts.append(f"Found {count} measurements")
            
            # Get unique data types
            data_types = []
            if any(r.get('temperature') is not None for r in db_results):
                data_types.append("temperature")
            if any(r.get('salinity') is not None for r in db_results):
                data_types.append("salinity")
            if any(r.get('depth') is not None for r in db_results):
                data_types.append("depth")
            
            if data_types:
                summary_parts.append(f"with {', '.join(data_types)} data")
        else:
            summary_parts.append("No specific data found")
        
        # Look for key topics in response
        response_lower = response_text.lower()
        
        # Geographic mentions
        if any(word in response_lower for word in ['arabian sea', 'mumbai', 'indian ocean', 'bay of bengal']):
            if 'arabian sea' in response_lower:
                summary_parts.append("from Arabian Sea")
            elif 'mumbai' in response_lower:
                summary_parts.append("near Mumbai")
            elif 'indian ocean' in response_lower:
                summary_parts.append("from Indian Ocean")
            elif 'bay of bengal' in response_lower:
                summary_parts.append("from Bay of Bengal")
        
        # Analysis type
        if query_classification.get('is_analytical'):
            summary_parts.append("with statistical analysis")
        elif query_classification.get('has_temporal'):
            summary_parts.append("with temporal analysis")
        elif query_classification.get('has_spatial'):
            summary_parts.append("with spatial analysis")
        
        # Combine and clean up
        summary = "; ".join(summary_parts)
        return summary[:100] + "..." if len(summary) > 100 else summary
    
    def _generate_chart_request_response(self, user_query: str, db_results: List[Dict], query_classification: Dict) -> str:
        """Generate a specialized response for chart requests"""
        
        if not db_results:
            return (
                "I'd love to create a chart for you, but I don't have any data matching your request. "
                "Try asking me to find some oceanographic data first, then I can generate the visualization you want."
            )
        
        # Get data summary for context
        count = len(db_results)
        available_params = []
        if any(r.get('temperature') is not None for r in db_results):
            available_params.append('temperature')
        if any(r.get('salinity') is not None for r in db_results):
            available_params.append('salinity')
        if any(r.get('depth') is not None for r in db_results):
            available_params.append('depth')
        if any(r.get('pressure') is not None for r in db_results):
            available_params.append('pressure')
        
        # Check if we have temporal data
        dates = [r.get('date') for r in db_results if r.get('date')]
        has_temporal_data = len(set(str(d)[:10] for d in dates)) > 1 if dates else False
        
        # Generate contextual chart response
        query_lower = user_query.lower()
        
        # Identify what kind of chart was requested
        if 'temperature' in query_lower and 'depth' in query_lower:
            chart_description = "temperature vs. depth profile"
        elif 'temperature' in query_lower and 'salinity' in query_lower:
            chart_description = "temperature-salinity (T-S) diagram"
        elif 'time' in query_lower or 'temporal' in query_lower:
            chart_description = "time series chart"
        elif 'scatter' in query_lower:
            chart_description = "scatter plot"
        elif 'histogram' in query_lower or 'distribution' in query_lower:
            chart_description = "distribution histogram"
        else:
            chart_description = "visualization"
        
        # Build response
        response_parts = []
        
        # Acknowledge the request
        response_parts.append(f"Perfect! I can create a {chart_description} for you using the oceanographic data I found.")
        
        # Describe the data
        if count > 0:
            response_parts.append(f"I have {count} data points with {', '.join(available_params)} measurements.")
            
            # Add temporal info if relevant
            if has_temporal_data:
                unique_dates = len(set(str(d)[:10] for d in dates))
                response_parts.append(f"The data spans {unique_dates} different dates, which will work great for time-based analysis.")
            
            # Add depth range if relevant
            if 'depth' in available_params:
                depths = [r['depth'] for r in db_results if r.get('depth') is not None]
                if depths:
                    depth_range = f"{min(depths):.0f}m to {max(depths):.0f}m"
                    response_parts.append(f"Depth coverage includes {depth_range}, giving us a good vertical profile.")
        
        # Explain what the chart will show
        if 'temperature' in query_lower and 'depth' in query_lower:
            response_parts.append("The temperature profile will show how water temperature changes with depth - you should see the thermocline where temperature drops rapidly.")
        elif 'temperature' in query_lower and 'salinity' in query_lower:
            response_parts.append("The T-S diagram will help identify different water masses and their characteristics - each water mass has a unique temperature-salinity signature.")
        elif has_temporal_data and ('time' in query_lower or 'temporal' in query_lower):
            response_parts.append("The time series will reveal temporal patterns and trends in the ocean measurements.")
        else:
            response_parts.append("The chart will help visualize relationships and patterns in the oceanographic data.")
        
        # Encourage interaction
        response_parts.append("The interactive chart below will let you explore the data in detail. You can hover over points for specific values and zoom into areas of interest!")
        
        return " ".join(response_parts)