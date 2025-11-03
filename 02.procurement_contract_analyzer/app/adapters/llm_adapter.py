import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

class LLMAdapter:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize LLM adapter with OpenAI client."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or add it to .env file.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
        self.chat_model = os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini')
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a list of texts."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings)
        except Exception as e:
            raise Exception(f"Failed to get embeddings: {str(e)}")
    
    def search_similar(self, query_embeddings: np.ndarray, 
                      document_embeddings: np.ndarray, 
                      topk: int = 1) -> tuple:
        """Find most similar documents using cosine similarity."""
        similarities = cosine_similarity(query_embeddings, document_embeddings)
        top_indices = np.argsort(-similarities, axis=1)[:, :topk]
        top_scores = np.take_along_axis(similarities, top_indices, axis=1)
        return top_indices, top_scores
    
    def assess_contract_risk(self, contract_text: str, template_clauses: List[Dict], 
                           matched_clauses: List[Dict]) -> Dict[str, Any]:
        """Use LLM agent to assess contract risk comprehensively."""
        
        # Prepare context for the LLM agent
        template_context = "\n\n".join([
            f"Template Clause {i+1}: {clause['title']}\n{clause['body']}" 
            for i, clause in enumerate(template_clauses)
        ])
        
        matched_context = "\n\n".join([
            f"Matched Clause {i+1}: {clause['title']}\n{clause['body']}\nSimilarity: {clause['similarity']:.1f}%" 
            for i, clause in enumerate(matched_clauses)
        ])
        
        prompt = f"""
You are an expert procurement contract analyst. Analyze the following contract against the standard template and provide a comprehensive risk assessment.

CONTRACT TO ANALYZE:
{contract_text}

STANDARD TEMPLATE CLAUSES:
{template_context}

MATCHED CLAUSES ANALYSIS:
{matched_context}

Please provide a detailed risk assessment in the following JSON format:
{{
    "overall_risk_score": <0-100>,
    "risk_band": "<LOW/MEDIUM/HIGH>",
    "missing_clauses": ["list of missing template clauses"],
    "high_risk_clauses": [
        {{
            "clause_title": "title",
            "risk_level": "<LOW/MEDIUM/HIGH>",
            "risk_factors": ["factor1", "factor2"],
            "recommendations": ["recommendation1", "recommendation2"]
        }}
    ],
    "deviations": [
        {{
            "clause_title": "title",
            "deviation_type": "type",
            "severity": "<LOW/MEDIUM/HIGH>",
            "description": "description"
        }}
    ],
    "global_risks": ["risk1", "risk2"],
    "summary": "Overall assessment summary"
}}

Focus on:
1. Missing critical clauses
2. Significant deviations from template
3. Unfavorable terms for the customer
4. Legal and compliance risks
5. Financial and operational risks
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "You are an expert procurement contract analyst with deep knowledge of legal risks, compliance requirements, and best practices in contract negotiation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=2000
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            try:
                # Extract JSON from response (in case there's extra text)
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "overall_risk_score": 50,
                    "risk_band": "MEDIUM",
                    "missing_clauses": [],
                    "high_risk_clauses": [],
                    "deviations": [],
                    "global_risks": ["Failed to parse LLM response"],
                    "summary": content
                }
                
        except Exception as e:
            return {
                "overall_risk_score": 75,
                "risk_band": "HIGH",
                "missing_clauses": [],
                "high_risk_clauses": [],
                "deviations": [],
                "global_risks": [f"LLM analysis failed: {str(e)}"],
                "summary": f"Error in risk assessment: {str(e)}"
            }
    
    def analyze_clause_similarity(self, template_clause: str, contract_clause: str) -> Dict[str, Any]:
        """Use LLM to analyze clause similarity and deviations."""
        
        prompt = f"""
Compare these two contract clauses and analyze their similarity and any deviations:

TEMPLATE CLAUSE:
{template_clause}

CONTRACT CLAUSE:
{contract_clause}

Provide analysis in JSON format:
{{
    "similarity_score": <0-100>,
    "similarity_level": "<VERY_HIGH/HIGH/MEDIUM/LOW/VERY_LOW>",
    "key_differences": ["difference1", "difference2"],
    "risk_indicators": ["indicator1", "indicator2"],
    "recommendations": ["recommendation1", "recommendation2"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "You are a legal contract analyst specializing in clause comparison and risk assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            except json.JSONDecodeError:
                return {
                    "similarity_score": 50,
                    "similarity_level": "MEDIUM",
                    "key_differences": ["Failed to parse LLM response"],
                    "risk_indicators": [],
                    "recommendations": []
                }
                
        except Exception as e:
            return {
                "similarity_score": 0,
                "similarity_level": "VERY_LOW",
                "key_differences": [f"Analysis failed: {str(e)}"],
                "risk_indicators": [],
                "recommendations": []
            }
