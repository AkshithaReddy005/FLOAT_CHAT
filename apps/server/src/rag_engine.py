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
        self.gemini_model = "gemini-2.0-flash"
        
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
                               db_results: List[Dict], query_classification: Dict) -> str:
        """Generate comprehensive response using RAG approach"""
        
        if self.use_gemini:
            return await self._generate_with_rag(user_query, context_results, db_results, query_classification)
        else:
            return self._generate_rule_based_response(user_query, db_results, query_classification)
    
    async def _generate_with_rag(self, user_query: str, context_results: Dict,
                                db_results: List[Dict], query_classification: Dict) -> str:
        """Generate response using Retrieval-Augmented Generation with Gemini"""
        
        # Prepare context from ChromaDB
        context_docs = context_results.get('documents', [[]])[0][:5] if context_results.get('documents') else []
        context_text = self._format_context(context_docs)
        
        # Prepare data summary
        data_summary = self._prepare_data_summary(db_results)
        
        # Prepare query classification info
        classification_info = self._format_classification(query_classification)
        
        # Build RAG prompt
        prompt = self._build_rag_prompt(user_query, context_text, data_summary, classification_info)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=600
                )
            )
            return response.text
        except Exception as e:
            print(f"RAG Engine: Gemini API error: {e}")
            return self._generate_rule_based_response(user_query, db_results, query_classification)
    
    def _build_rag_prompt(self, user_query: str, context_text: str, 
                         data_summary: str, classification_info: str) -> str:
        """Build comprehensive RAG prompt"""
        
        return f"""You are FloatChat, a friendly and knowledgeable AI assistant for ARGO oceanographic data. You help users understand ocean measurements through natural conversation and clear explanations.

User Query: "{user_query}"

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
    
    def _generate_rule_based_response(self, user_query: str, db_results: List[Dict], 
                                    query_classification: Dict) -> str:
        """Generate response using rule-based approach when LLM is not available"""
        
        if not db_results:
            return ("I couldn't find any ARGO measurements that match your specific query. This might be because:\n\n"
                   "• The location you're interested in isn't covered by our ARGO float network yet\n"
                   "• The time period you mentioned doesn't have available data\n"
                   "• The specific combination of parameters you're looking for isn't in our database\n\n"
                   "Here are some things you could try:\n"
                   "• Broaden your search area or time range\n"
                   "• Check what data is available using the 'What data is available?' button\n"
                   "• Try asking about similar regions or related measurements\n\n"
                   "Feel free to ask me about what data we do have - I'm here to help you explore!")
        
        # Statistical summary
        count = len(db_results)
        unique_floats = len(set(r['float_id'] for r in db_results))
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        
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