import requests
import json
import os
import asyncio
import base64
import cv2
import numpy as np

class AIAssistant:
    def __init__(self, api_key=None):
        """
        Initialize OpenRouter API client
        
        Args:
            api_key: OpenRouter API key (can also be set via OPENROUTER_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY','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')
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "mistralai/mistral-7b-instruct"
        self.vision_model = "qwen/qwen-2.5-vl-7b-instruct:free"  # Free vision model
        self.site_url = os.getenv('SITE_URL', 'http://localhost:5000')
        self.site_name = os.getenv('SITE_NAME', 'Personal-Jarvis')
        
        if not self.api_key:
            print("Warning: No OpenRouter API key provided. Set OPENROUTER_API_KEY environment variable.")
    
    def generate_response(self, query, context=None, conversation_history=None, temperature=0.7, max_tokens=500):
        """
        Generate AI response using Mistral model
        
        Args:
            query: User query
            context: Additional context (e.g., web search results)
            conversation_history: Previous conversation turns
            temperature: Sampling temperature for generation
            max_tokens: Maximum tokens to generate
        
        Returns:
            AI generated response
        """
        if not self.api_key:
            return "API key not configured. Please set OPENROUTER_API_KEY environment variable."
        
        try:
            # Build messages
            messages = []
            
            # System prompt
            system_prompt = (
                "You are Jarvis, a warm, friendly, and concise male-voiced assistant. "
                "Keep answers clear, accurate, and supportive; add brief helpful context when useful, "
                "but avoid long tangents.\n\n"
                "IMPORTANT: If you don't have reliable information about a topic, or if the query is asking about "
                "current events, recent news, real-time data, specific product details, or factual information "
                "you're uncertain about, respond with just: [NEEDS_WEB_SEARCH]\n\n"
                "Then the system will automatically search the web and provide you current information to answer properly. "
                "This ensures you give accurate, up-to-date responses instead of guessing or admitting ignorance."
            )
            
            if context:
                system_prompt += f"\n\nContext from web search:\n{context}"
            
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
            # Add conversation history if available
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 turns
                    messages.append(msg)
            
            # Add current query
            messages.append({
                "role": "user",
                "content": query
            })
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            print(f"Error generating AI response: {e}")
            return f"I encountered an error processing your request: {str(e)}"
    
    def summarize_web_results(self, query, web_results):
        """
        Summarize web search results
        
        Args:
            query: Original search query
            web_results: Dictionary of URL -> content
        
        Returns:
            Summarized response
        """
        # Combine all web content
        combined_context = ""
        for idx, (url, content) in enumerate(web_results.items(), 1):
            combined_context += f"\n\n[Source {idx}: {url}]\n{content[:1000]}"  # Limit each source
        
        # Truncate if too long
        if len(combined_context) > 8000:
            combined_context = combined_context[:8000] + "..."
        
        prompt = f"Based on the following web search results, answer this question: {query}\n\nProvide a clear, concise answer."
        
        return self.generate_response(prompt, context=combined_context)

    def summarize_multi_web_results(self, user_request, results_by_query):
        """
        Summarize web results collected from multiple rewritten queries.
        """
        combined_context = ""
        source_idx = 1
        for rewritten_query, url_map in results_by_query.items():
            if not url_map:
                continue
            combined_context += f"\n\n[Query Variant: {rewritten_query}]"
            for url, content in url_map.items():
                combined_context += f"\n[Source {source_idx}: {url}]\n{content[:1000]}"
                source_idx += 1

        if not combined_context:
            return "I could not gather enough information from the web to answer that."\
                " Please try rephrasing or narrowing the topic."

        # Cap context to avoid oversized requests
        if len(combined_context) > 8000:
            combined_context = combined_context[:8000] + "..."

        prompt = (
            "Use the gathered web results to answer the user's request. "
            "Prefer consensus across sources; be concise and practical. "
            "If unsure, say so briefly."
        )

        return self.generate_response(prompt, context=combined_context, temperature=0.3)

    def rewrite_query_for_search(self, user_utterance):
        """
        Use the LLM to produce a concise web-search-friendly query from a user utterance.
        """
        if not user_utterance:
            return ""
        prompt = (
            "You rewrite user requests into a short, clear web search query. "
            "Keep it concise (<=8 words), no quotes, no filler, no pronouns. "
            "Just return the query text.\n\n"
            f"User request: {user_utterance}"
        )
        try:
            return self.generate_response(prompt, temperature=0.2, max_tokens=32)
        except Exception:
            # If LLM fails, fall back to original
            return user_utterance

    def generate_research_questions(self, user_query, max_questions=4):
        """
        Generate multiple research angles/questions from user query.
        """
        if not user_query:
            return []
        
        prompt = (
            f"Generate {max_questions} diverse research angles to comprehensively understand: '{user_query}'\n\n"
            "Each angle should probe a different aspect (e.g., definition, current trends, key players, latest news, statistics).\n"
            "Return one angle per line — concise and search-friendly."
        )
        
        try:
            resp = self.generate_response(prompt, temperature=0.4, max_tokens=150)
            angles = [line.strip() for line in resp.splitlines() if line.strip() and len(line) > 8]
            return angles[:max_questions]
        except Exception as e:
            print(f"Error generating research questions: {e}")
            return [user_query]

    def extract_key_insights(self, query, web_results_by_query):
        """
        Extract key insights and facts from aggregated web results.
        """
        # Build context from all results
        context_parts = []
        for research_angle, url_contents in web_results_by_query.items():
            if url_contents:
                context_parts.append(f"\n[Research Angle: {research_angle}]")
                for url, content in list(url_contents.items())[:2]:  # Top 2 per angle
                    snippet = content[:1500] if content else ""
                    if snippet:
                        context_parts.append(f"Source: {url}\n{snippet}")
        
        context = "\n".join(context_parts)[:12000]
        
        if not context.strip():
            return "No relevant information found in search results."
        
        prompt = (
            f"Based on the web research below about '{query}', extract and summarize:\n"
            "- Key facts and statistics\n"
            "- Important trends or developments\n"
            "- Notable entities or people mentioned\n"
            "- Any recommendations or best practices\n\n"
            f"Context:\n{context}\n\n"
            "Provide a concise, well-organized summary (3-4 paragraphs)."
        )
        
        try:
            return self.generate_response(prompt, temperature=0.3, max_tokens=600)
        except Exception as e:
            print(f"Error extracting insights: {e}")
            return "Error processing search results."

    def needs_web_search(self, response: str) -> bool:
        """
        Check if the AI response indicates it needs web search.
        Returns True if response contains the web search signal.
        """
        return "[NEEDS_WEB_SEARCH]" in response

    def answer_with_web_context(self, query: str, web_results_by_query: dict) -> str:
        """
        Answer a query using web search results for context.
        """
        # Build context from all results
        context_parts = []
        for research_angle, url_contents in web_results_by_query.items():
            if url_contents:
                context_parts.append(f"\n[From research on: {research_angle}]")
                for url, content in list(url_contents.items())[:2]:
                    snippet = content[:1200] if content else ""
                    if snippet:
                        context_parts.append(f"Source: {url}\n{snippet}")
        
        context = "\n".join(context_parts)[:10000]
        
        if not context.strip():
            return "I searched but couldn't find enough information to answer that. Can you rephrase your question?"
        
        prompt = f"Using the web search results below, answer this question: {query}\n\nProvide a clear, helpful answer."
        
        try:
            return self.generate_response(prompt, context=context, temperature=0.4, max_tokens=500)
        except Exception as e:
            print(f"Error answering with web context: {e}")
            return "I encountered an error while processing the search results."
    async def answer_with_intelligent_search(self, query: str, force_browser=False):
        """
        Answer a query using the intelligent web search system.
        This method integrates with the new intelligent_web_search module.
        """
        try:
            # Import here to avoid circular dependency
            from .intelligent_web_search import IntelligentWebSearch
            
            # Initialize search system
            search_system = IntelligentWebSearch(show_browser=force_browser)
            
            # Perform intelligent search
            search_results = await search_system.search(query, force_browser=force_browser)
            
            # Generate answer using the search results
            answer = search_system.generate_answer(query, search_results)
            
            return {
                'answer': answer,
                'search_results': search_results,
                'sources': [r.get('url') for r in search_results.get('results', [])[:5]]
            }
            
        except Exception as e:
            print(f"Error in intelligent search: {e}")
            return {
                'answer': f"I encountered an error while searching: {str(e)}",
                'search_results': None,
                'sources': []
            }

    def analyze_image(self, image, query="What do you see in this image?", detail="high"):
        """
        Analyze an image using Vision Language Model
        
        Args:
            image: Either a file path (str), numpy array (cv2 frame), or PIL Image
            query: Question about the image
            detail: 'low' or 'high' - quality of image analysis
        
        Returns:
            str: AI's description/analysis of the image
        """
        if not self.api_key:
            return "API key not configured."
        
        try:
            # Convert image to base64
            if isinstance(image, str):
                # File path
                with open(image, "rb") as img_file:
                    image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            elif isinstance(image, np.ndarray):
                # OpenCV/numpy array (BGR format)
                # Encode as JPEG
                success, buffer = cv2.imencode('.jpg', image)
                if not success:
                    return "Failed to encode image"
                image_base64 = base64.b64encode(buffer).decode('utf-8')
            else:
                return "Unsupported image format"
            
            # Build message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": query
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": detail
                            }
                        }
                    ]
                }
            ]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.site_url,
                "X-Title": self.site_name
            }
            
            payload = {
                "model": self.vision_model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result['choices'][0]['message']['content']
        
        except Exception as e:
            print(f"Error in image analysis: {e}")
            return f"I encountered an error analyzing the image: {str(e)}"

    def analyze_camera_feed(self, frame, query="What do you see?"):
        """
        Analyze a camera frame with a specific query
        
        Args:
            frame: OpenCV frame (numpy array)
            query: User's question about what they're seeing
        
        Returns:
            str: AI's answer about the camera view
        """
        return self.analyze_image(frame, query, detail="high")

    def process_query(self, query: str, conversation_history=None):
        """
        Process a user query with automatic web search integration.
        
        This is the main entry point that:
        1. First tries to answer with existing knowledge
        2. If [NEEDS_WEB_SEARCH] is returned, performs intelligent web search
        3. Returns the final answer with sources
        """
        # First try without web search
        initial_response = self.generate_response(
            query,
            conversation_history=conversation_history,
            temperature=0.7,
            max_tokens=500
        )
        
        # Check if web search is needed
        if self.needs_web_search(initial_response):
            print("🔍 Web search triggered by AI")
            
            # Perform intelligent web search (synchronously)
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self.answer_with_intelligent_search(query)
            )
            
            return result
        
        # Return initial response if no web search needed
        return {
            'answer': initial_response,
            'search_results': None,
            'sources': []
        }