"""
Simple example showing how to use the integrated intelligent web search
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from ai_assistant import AIAssistant

def example_1_basic_query():
    """Example 1: Basic query that doesn't need web search"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Query (No Web Search Needed)")
    print("="*70)
    
    ai = AIAssistant()
    query = "What is 2 + 2?"
    
    print(f"\nQuery: {query}")
    result = ai.process_query(query)
    
    print(f"\nAnswer: {result['answer']}")
    print(f"Web search used: {'Yes' if result['sources'] else 'No'}")

async def example_2_web_search_needed():
    """Example 2: Query that triggers automatic web search"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Query Needing Web Search")
    print("="*70)
    
    ai = AIAssistant()
    query = "What are the latest developments in quantum computing?"
    
    print(f"\nQuery: {query}")
    print("\nProcessing... (this may take a few seconds)")
    
    result = await ai.answer_with_intelligent_search(query)
    
    print(f"\nAnswer: {result['answer']}")
    
    if result['sources']:
        print(f"\nSources ({len(result['sources'])}):")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source}")

async def example_3_browser_automation():
    """Example 3: Query that may trigger browser automation"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Query Possibly Needing Browser Automation")
    print("="*70)
    
    ai = AIAssistant()
    query = "Show me how to create a GitHub repository"
    
    print(f"\nQuery: {query}")
    print("\nProcessing... (may open browser)")
    
    result = await ai.answer_with_intelligent_search(query, force_browser=False)
    
    print(f"\nAnswer: {result['answer'][:500]}...")  # First 500 chars
    
    search_info = result.get('search_results', {})
    if search_info:
        print(f"\nSearch Statistics:")
        print(f"  Query variants: {len(search_info.get('query_variants', []))}")
        print(f"  Total results: {search_info.get('total_results', 0)}")
        print(f"  Browser automation: {search_info.get('browser_automation_used', False)}")

async def example_4_direct_search():
    """Example 4: Direct use of IntelligentWebSearch"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Direct Web Search Usage")
    print("="*70)
    
    from intelligent_web_search import IntelligentWebSearch
    
    search = IntelligentWebSearch(show_browser=False)
    query = "machine learning basics"
    
    print(f"\nQuery: {query}")
    print("\nSearching...")
    
    results = await search.search(query)
    
    print(f"\n📊 Search Results:")
    print(f"  Original query: {results['query']}")
    print(f"  Query variants: {len(results['query_variants'])}")
    for i, variant in enumerate(results['query_variants'], 1):
        print(f"    {i}. {variant}")
    
    print(f"\n  Total results found: {results['total_results']}")
    print(f"  Browser automation: {results['browser_automation_used']}")
    
    print(f"\n📝 Generating answer...")
    answer = search.generate_answer(query, results)
    print(f"\nAnswer:\n{answer}")

async def example_5_conversation():
    """Example 5: Multi-turn conversation with memory"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Conversation with Memory")
    print("="*70)
    
    ai = AIAssistant()
    conversation_history = []
    
    queries = [
        "What is Python?",
        "What are its main features?",
        "How does it compare to JavaScript?"
    ]
    
    for query in queries:
        print(f"\n👤 User: {query}")
        
        result = ai.process_query(query, conversation_history)
        
        print(f"🤖 Jarvis: {result['answer'][:300]}...")
        
        # Update conversation history
        conversation_history.append({
            "role": "user",
            "content": query
        })
        conversation_history.append({
            "role": "assistant",
            "content": result['answer']
        })
        
        await asyncio.sleep(1)

async def main():
    """Run all examples"""
    
    print("\n" + "#"*70)
    print("# INTELLIGENT WEB SEARCH - USAGE EXAMPLES")
    print("#"*70)
    
    examples = [
        ("Basic Query (No Web Search)", example_1_basic_query),
        ("Automatic Web Search", example_2_web_search_needed),
        ("Browser Automation Decision", example_3_browser_automation),
        ("Direct Search API", example_4_direct_search),
        ("Conversation with Memory", example_5_conversation)
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print(f"  {len(examples) + 1}. Run all examples")
    print(f"  0. Exit")
    
    try:
        choice = input("\nSelect example (0-{}): ".format(len(examples) + 1))
        choice = int(choice)
        
        if choice == 0:
            print("Goodbye!")
            return
        elif 1 <= choice <= len(examples):
            name, func = examples[choice - 1]
            print(f"\nRunning: {name}\n")
            
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
                
            print("\n✅ Example complete!")
            
        elif choice == len(examples) + 1:
            for name, func in examples:
                print(f"\n{'#'*70}")
                print(f"# Running: {name}")
                print(f"{'#'*70}")
                
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
                
                print("\n✅ Example complete!")
                print("\nPress Enter to continue...")
                input()
        else:
            print("Invalid choice")
            
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    except ValueError:
        print("\n❌ Please enter a valid number")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
