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
        
        return f"""You are FloatChat, an expert AI assistant specializing in ARGO oceanographic data analysis. You help researchers understand ocean data through clear explanations and insights.

User Query: "{user_query}"

Query Analysis:
{classification_info}

Relevant Context from Knowledge Base:
{context_text}

Current Query Results:
{data_summary}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. KNOWLEDGE BOUNDARY AWARENESS: If the context from the knowledge base is limited or says "No relevant context found" or "No specific context found", and the user asks about specific oceanographic phenomena, concepts, or locations that are NOT covered in the available context, you MUST clearly state that you don't have sufficient information in the knowledge base to provide a comprehensive answer about that specific topic.

2. HONESTY ABOUT DATA LIMITATIONS: If no data is found matching the query criteria, clearly state this and explain possible reasons (location not covered, time period not available, etc.). Do not speculate about data that doesn't exist.

3. STRUCTURED RESPONSE FORMAT:
   - Start with a clear, direct answer to the question
   - Use bullet points or numbered lists for key findings
   - Separate data insights from general context
   - End with actionable suggestions or next steps

4. RESPONSE STRUCTURE:
   • **Direct Answer**: [Clear response to the user's question]
   • **Key Findings from Data**: [Bullet points of main insights from actual results]
   • **Context**: [Only include relevant background if available in knowledge base]
   • **Interpretation**: [What the findings suggest about ocean conditions]

5. Be conversational but scientifically accurate
6. Keep responses concise and well-structured for better readability
7. If you're unsure about any aspect due to limited context, explicitly state this limitation

Remember: It's better to admit knowledge limitations than to provide potentially incorrect information."""
    
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
            return ("**Direct Answer**: No ARGO measurements were found matching your specific query criteria.\n\n"
                   "**Possible Reasons**:\n"
                   "• The requested location may not be covered by our ARGO float network\n"
                   "• The time period specified might not have available data\n"
                   "• The parameter combination requested may not exist in our database\n\n"
                   "**Suggestions**:\n"
                   "• Try broadening your search criteria (wider date range or geographic area)\n"
                   "• Check if similar regions have available data\n"
                   "• Use our data visualization tools to explore what's available")
        
        # Statistical summary
        count = len(db_results)
        unique_floats = len(set(r['float_id'] for r in db_results))
        temps = [r['temperature'] for r in db_results if r['temperature'] is not None]
        salinities = [r['salinity'] for r in db_results if r['salinity'] is not None]
        depths = [r['depth'] for r in db_results if r['depth'] is not None]
        
        # Build structured response
        response_parts = []
        
        # Direct answer
        response_parts.append(f"**Direct Answer**: Found {count} ARGO measurements from {unique_floats} different floats matching your query.")
        
        # Key findings
        findings = []
        if temps:
            avg_temp = sum(temps) / len(temps)
            min_temp, max_temp = min(temps), max(temps)
            findings.append(f"Temperature: {min_temp:.1f}°C to {max_temp:.1f}°C (avg: {avg_temp:.1f}°C)")
        
        if salinities:
            avg_sal = sum(salinities) / len(salinities)
            min_sal, max_sal = min(salinities), max(salinities)
            findings.append(f"Salinity: {min_sal:.2f} to {max_sal:.2f} (avg: {avg_sal:.2f})")
        
        if depths:
            min_depth, max_depth = min(depths), max(depths)
            findings.append(f"Depth range: {min_depth:.0f}m to {max_depth:.0f}m")
        
        if findings:
            response_parts.append("**Key Findings from Data**:\n• " + "\n• ".join(findings))
        
        # Interpretation
        interpretation = []
        if depths:
            if max_depth > 1000:
                interpretation.append("Data includes deep ocean measurements, providing insights into deep water properties")
            elif max_depth > 200:
                interpretation.append("Data covers surface and mid-depth waters, showing vertical ocean structure")
            else:
                interpretation.append("Data focuses on surface and near-surface waters")
        
        if interpretation:
            response_parts.append("**Interpretation**: " + ". ".join(interpretation) + ".")
        
        # Visualization note
        response_parts.append("**Visualizations**: Interactive charts below show spatial distribution, depth profiles, and temporal patterns.")
        
        return "\n\n".join(response_parts)