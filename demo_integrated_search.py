"""
Demo script showing the integrated intelligent web search system

This demonstrates:
1. Multi-query generation from user input
2. ChromaDB caching
3. Intelligent browser automation decisions
4. AI-powered answer generation
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ai_assistant import AIAssistant
from intelligent_web_search import IntelligentWebSearch

async def demo_intelligent_search():
    """Demonstrate the intelligent search system"""
    
    print("=" * 70)
    print("INTELLIGENT WEB SEARCH DEMO")
    print("=" * 70)
    
    # Initialize AI assistant
    ai = AIAssistant()
    
    # Test scenarios
    scenarios = [
        {
            "query": "What is the transformer attention mechanism in AI?",
            "description": "Informational query - Should NOT trigger browser automation",
            "force_browser": False
        },
        {
            "query": "Show me the GitHub Actions interface and how to use it",
            "description": "Visual/interactive query - SHOULD trigger browser automation",
            "force_browser": False
        },
        {
            "query": "Latest developments in quantum computing 2026",
            "description": "Current events query - May or may not trigger browser",
            "force_browser": False
        }
    ]
    
    for idx, scenario in enumerate(scenarios, 1):
        print(f"\n{'=' * 70}")
        print(f"SCENARIO {idx}: {scenario['description']}")
        print(f"Query: {scenario['query']}")
        print(f"{'=' * 70}\n")
        
        # Process query with integrated system
        result = await ai.answer_with_intelligent_search(
            scenario['query'],
            force_browser=scenario['force_browser']
        )
        
        # Display results
        print("\n" + "=" * 70)
        print("ANSWER:")
        print("=" * 70)
        print(result['answer'])
        
        if result.get('sources'):
            print("\n" + "=" * 70)
            print("SOURCES:")
            print("=" * 70)
            for i, source in enumerate(result['sources'], 1):
                print(f"{i}. {source}")
        
        search_results = result.get('search_results', {})
        if search_results:
            print("\n" + "=" * 70)
            print("SEARCH STATISTICS:")
            print("=" * 70)
            print(f"Query variants: {len(search_results.get('query_variants', []))}")
            print(f"Total results: {search_results.get('total_results', 0)}")
            print(f"Browser automation: {'YES' if search_results.get('browser_automation_used') else 'NO'}")
        
        print("\n" + "=" * 70)
        print(f"SCENARIO {idx} COMPLETE")
        print("=" * 70)
        
        # Wait before next scenario
        if idx < len(scenarios):
            print("\nWaiting 5 seconds before next scenario...\n")
            await asyncio.sleep(5)

async def demo_process_query():
    """Demonstrate the automatic web search integration"""
    
    print("\n\n" + "=" * 70)
    print("AUTO WEB SEARCH INTEGRATION DEMO")
    print("=" * 70)
    
    ai = AIAssistant()
    
    # Queries that will trigger automatic web search
    queries = [
        "Who won the Nobel Prize in Physics in 2025?",  # Should trigger web search
        "What is 2 + 2?",  # Should NOT trigger web search
        "Latest news about SpaceX Starship launches",  # Should trigger web search
    ]
    
    for query in queries:
        print(f"\n{'=' * 70}")
        print(f"QUERY: {query}")
        print(f"{'=' * 70}\n")
        
        result = ai.process_query(query)
        
        print("ANSWER:")
        print(result['answer'])
        
        if result.get('sources'):
            print("\nSOURCES:")
            for i, source in enumerate(result['sources'], 1):
                print(f"{i}. {source}")
        
        print(f"\n{'=' * 70}\n")
        await asyncio.sleep(2)

async def demo_cache_efficiency():
    """Demonstrate caching efficiency"""
    
    print("\n\n" + "=" * 70)
    print("CACHE EFFICIENCY DEMO")
    print("=" * 70)
    
    search_system = IntelligentWebSearch(show_browser=False)
    
    query = "What is machine learning?"
    
    print(f"\nQuery: {query}")
    print("\nFIRST SEARCH (will fetch from web):")
    print("-" * 70)
    
    import time
    start = time.time()
    result1 = await search_system.search(query)
    time1 = time.time() - start
    
    print(f"Time taken: {time1:.2f} seconds")
    print(f"Results found: {result1['total_results']}")
    
    print("\n\nSECOND SEARCH (should use cache):")
    print("-" * 70)
    
    start = time.time()
    result2 = await search_system.search(query)
    time2 = time.time() - start
    
    print(f"Time taken: {time2:.2f} seconds")
    print(f"Results found: {result2['total_results']}")
    
    print(f"\n{'=' * 70}")
    print(f"Speed improvement: {(time1 / time2):.2f}x faster!")
    print(f"{'=' * 70}")

async def main():
    """Run all demos"""
    
    print("\n")
    print("#" * 70)
    print("# INTELLIGENT WEB SEARCH SYSTEM - COMPLETE DEMO")
    print("#" * 70)
    
    demos = [
        ("Intelligent Search", demo_intelligent_search),
        ("Auto Web Search Integration", demo_process_query),
        ("Cache Efficiency", demo_cache_efficiency)
    ]
    
    print("\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"{i}. {name}")
    print(f"{len(demos) + 1}. Run all demos")
    
    try:
        choice = input("\nSelect demo (1-{}): ".format(len(demos) + 1))
        choice = int(choice)
        
        if 1 <= choice <= len(demos):
            await demos[choice - 1][1]()
        elif choice == len(demos) + 1:
            for name, demo_func in demos:
                print(f"\n\n{'#' * 70}")
                print(f"# Starting: {name}")
                print(f"{'#' * 70}\n")
                await demo_func()
                print("\n" + "=" * 70)
                print("Demo complete. Press Enter to continue...")
                input()
        else:
            print("Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
