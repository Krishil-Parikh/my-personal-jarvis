"""
Quick test to verify the integrated search system works
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from backend.ai_assistant import AIAssistant

async def test_search():
    print("Testing intelligent web search integration...\n")
    
    ai = AIAssistant()
    
    # Test query that should trigger web search
    query = "Tell me about the Venezuela situation"
    
    print(f"Query: {query}\n")
    print("Processing...\n")
    
    try:
        result = await ai.answer_with_intelligent_search(query, force_browser=False)
        
        print("=" * 70)
        print("ANSWER:")
        print("=" * 70)
        print(result['answer'])
        
        if result.get('sources'):
            print("\n" + "=" * 70)
            print("SOURCES:")
            print("=" * 70)
            for i, source in enumerate(result['sources'], 1):
                print(f"{i}. {source}")
        
        print("\n✅ Test successful!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())
