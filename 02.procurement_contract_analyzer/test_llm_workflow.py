#!/usr/bin/env python3
"""
Test script to verify the new LLM-based contract analysis workflow.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.adapters.llm_adapter import LLMAdapter
from app.analyzers.llm_risk_agent import LLMRiskAgent
from app.utils.io import read_text_any, markdown_to_text
from app.rag.chunker import split_into_clauses

async def test_llm_workflow():
    """Test the LLM-based workflow."""
    print("🧪 Testing LLM-based Contract Analysis Workflow")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        return False
    
    try:
        # Initialize LLM components
        print("🔧 Initializing LLM components...")
        llm_adapter = LLMAdapter()
        llm_risk_agent = LLMRiskAgent(llm_adapter)
        print("✅ LLM components initialized successfully")
        
        # Test embedding generation
        print("\n🔍 Testing embedding generation...")
        test_texts = [
            "Supplier shall provide services as described in the agreement.",
            "Vendor will deliver products according to specifications."
        ]
        embeddings = llm_adapter.get_embeddings(test_texts)
        print(f"✅ Generated embeddings with shape: {embeddings.shape}")
        
        # Test similarity search
        print("\n🔍 Testing similarity search...")
        query_embeddings = llm_adapter.get_embeddings(["service agreement"])
        top_idx, top_scores = llm_adapter.search_similar(query_embeddings, embeddings, topk=1)
        print(f"✅ Similarity search completed. Top match: {top_scores[0][0]:.3f}")
        
        # Test contract analysis with sample data
        print("\n📄 Testing contract analysis...")
        sample_contract = """
        # ACME Corp — Supplier Agreement
        
        ## Scope of Services
        Vendor will provide tooling support and optional advisory services.
        
        ## Payment
        Payment terms: net 45 days. Late fees may apply.
        
        ## Confidentiality
        Both parties will consider exchanged information confidential.
        
        ## Data Processing
        A Data Processing Addendum is not applicable.
        
        ## Liability
        Vendor's liability is unlimited for any losses.
        
        ## Termination
        Vendor may terminate for convenience with 10 days' notice.
        
        ## Legal
        Governing law: Delaware.
        """
        
        # Process contract
        contract_text = markdown_to_text(sample_contract)
        contract_clauses = split_into_clauses(contract_text)
        
        # Prepare template clauses (simplified)
        template_clauses = [
            {
                'title': 'Scope of Services',
                'body': 'Supplier shall provide the Services as described in the applicable Order Forms.'
            },
            {
                'title': 'Data Protection',
                'body': 'Supplier shall process Customer Personal Data solely on documented instructions and comply with the DPA.'
            }
        ]
        
        matched_clauses = [
            {
                'title': 'Scope of Services',
                'body': 'Vendor will provide tooling support and optional advisory services.',
                'similarity': 75.0
            }
        ]
        
        # Run LLM analysis
        print("🤖 Running LLM risk assessment...")
        result = llm_risk_agent.analyze_contract(
            contract_text, template_clauses, matched_clauses
        )
        
        print(f"✅ Analysis completed!")
        print(f"   Risk Score: {result.overall_risk}")
        print(f"   Risk Band: {result.risk_band}")
        print(f"   Missing Clauses: {len(result.missing_clauses)}")
        print(f"   Clause Results: {len(result.clause_results)}")
        print(f"   Global Flags: {len(result.global_flags)}")
        
        # Test recommendations
        recommendations = llm_risk_agent.generate_recommendations(result)
        print(f"   Recommendations: {len(recommendations)}")
        
        print("\n🎉 All tests passed! LLM workflow is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    print("Starting LLM workflow test...")
    success = asyncio.run(test_llm_workflow())
    
    if success:
        print("\n✅ LLM workflow test completed successfully!")
        print("\nTo use the new LLM features:")
        print("1. Set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the API: uvicorn app.main:app --reload --port 8000")
        print("4. Use the /analyze endpoint with use_llm=true (default)")
    else:
        print("\n❌ LLM workflow test failed!")
        print("Please check your OpenAI API key and dependencies.")

if __name__ == "__main__":
    main()
