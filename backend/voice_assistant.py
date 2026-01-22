import os
import time
import threading
import re
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from .app_launcher import open_application, extract_app_name
from .web_search import WebSearcher
from .memory import ConversationMemory
from .ai_assistant import AIAssistant

class LocalAssistant:
    """Voice assistant backed by Azure Speech for STT/TTS."""

    def __init__(self):
        # Load environment (.env)
        load_dotenv()

        # Load Azure keys from environment
        self.speech_key = os.getenv("AZURE_SPEECH_KEY")
        self.speech_region = os.getenv("AZURE_SPEECH_REGION")
        if not self.speech_key or not self.speech_region:
            raise RuntimeError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set in environment/.env")

        # Optional voice selection
        # Default to a male voice; override via AZURE_SPEECH_VOICE in .env
        self.voice_name = os.getenv("AZURE_SPEECH_VOICE", "en-US-GuyNeural")

        # Azure speech config
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
        self.speech_config.speech_recognition_language = "en-US"
        self.speech_config.speech_synthesis_voice_name = self.voice_name

        # Components
        self.web_searcher = WebSearcher()
        self.memory = ConversationMemory()
        self.ai = AIAssistant()
        
        # Interruption support
        self.is_speaking = False
        self.stop_speaking = False
        self.speaking_lock = threading.Lock()
        self._synth = None

    def speak(self, text, emotion: str = "neutral"):
        """Text to speech via Azure with interruption support (chunked)."""
        print(f"Assistant: {text}")
        with self.speaking_lock:
            self.is_speaking = True
            self.stop_speaking = False
        
        try:
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            # Keep reference to current synthesizer for stopping
            self._synth = synthesizer

            # Split text into sentences to allow quicker interruption
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s]
            for segment in sentences:
                # Check for stop request before each segment
                with self.speaking_lock:
                    if self.stop_speaking:
                        # Try to stop speaking immediately
                        try:
                            if hasattr(self._synth, 'stop_speaking_async'):
                                self._synth.stop_speaking_async()
                        except Exception:
                            pass
                        break

                # Speak this segment
                try:
                    result_future = synthesizer.speak_text_async(segment)
                    result = result_future.get()
                    if result.reason == speechsdk.ResultReason.Canceled:
                        details = result.cancellation_details
                        print(f"[TTS Error] {details.reason}: {details.error_details}")
                except Exception as e:
                    print(f"[TTS Error] {e}")
                    break
        finally:
            with self.speaking_lock:
                self.is_speaking = False
                self.stop_speaking = False
            self._synth = None

    def interrupt_speaking(self):
        """Signal to stop speaking immediately."""
        with self.speaking_lock:
            self.stop_speaking = True
        # Attempt to stop current synthesis if available
        try:
            if self._synth and hasattr(self._synth, 'stop_speaking_async'):
                self._synth.stop_speaking_async()
        except Exception:
            pass

    def takeCommand(self, interrupt_mode=False):
        """
        Speech to text via Azure.
        
        Args:
            interrupt_mode: If True, only listen for wake word to interrupt speaking.
                           If False, listen for normal commands.
        """
        if interrupt_mode:
            print("\nListening for wake word to interrupt...")
        else:
            print("\nListening for command...")
        
        audio = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio
        )
        
        # For interrupt mode, use async with shorter timeout by getting future and waiting
        if interrupt_mode:
            try:
                result_future = recognizer.recognize_once_async()
                # Wait max 2 seconds for interrupt
                result = result_future.get()
            except Exception as e:
                print(f"Interrupt listen timeout/error: {e}")
                return ""
        else:
            result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            command = result.text.strip().lower()
            
            if interrupt_mode:
                    # In interrupt mode, check for wake word (must be substantial)
                    if len(command) >= 3 and any(phrase in command for phrase in ['hey jarvis', 'jarvis', 'interrupt']):
                        print("[WAKE WORD DETECTED - INTERRUPTING NOW!]")
                        self.interrupt_speaking()  # Stop speaking immediately
                        return "INTERRUPTED"
                    else:
                        # Not a wake word, ignore silently in interrupt mode
                        return ""
            else:
                    # Normal mode - only return if command is substantial (min 3 chars, not just noise)
                    if len(command) >= 3 and not command.isdigit():
                        print(f"User: {command}")
                        return command
                    else:
                        # Ignore very short or noise-only input
                        return ""
                
        elif result.reason == speechsdk.ResultReason.NoMatch:
            if interrupt_mode:
                return ""  # No match in interrupt mode
            pass  # Silently continue
        elif result.reason == speechsdk.ResultReason.Canceled:
            if interrupt_mode:
                return ""  # Timeout or error in interrupt mode
            details = result.cancellation_details
            if "TooManyRequests" not in details.reason:
                pass  # Silently ignore transient errors
        
        return ""
    
    def process_command(self, command):
        """
        Process and execute user command
        
        Args:
            command: User voice command
        
        Returns:
            tuple: (response_text, command_type)
        """
        command_lower = command.lower()
        
        # Check for system sleep
        if any(word in command_lower for word in ['sleep', 'go to sleep']):
            response = "Putting system to sleep"
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            self.memory.add_conversation(command, response, {"type": "sleep"})
            return response, "sleep"

        # Check for shutdown
        if any(phrase in command_lower for phrase in ['good bye jarvis', 'goodbye jarvis', 'shutdown system', 'turn off']):
            response = "Shutting down. Goodbye!"
            self.memory.add_conversation(command, response, {"type": "shutdown"})
            os.system("shutdown /s /t 0")
            return response, "shutdown"

        # Check for app launching
        if any(word in command_lower for word in ['open', 'launch', 'start', 'run']):
            app_name = extract_app_name(command)
            if app_name:
                response = f"Opening {app_name}"
                success = open_application(app_name)
                if not success:
                    response = f"Failed to open {app_name}"
                
                # Store in memory
                self.memory.add_conversation(command, response, {"type": "app_launch"})
                return response, "app_launch"
        
        # Check for web search
        if any(word in command_lower for word in ['search', 'look up', 'find', 'google', 'what is', 'who is', 'tell me about']):
            # Extract the core query
            core_query = self.web_searcher.extract_search_query(command)
            
            if not core_query:
                return "Could not extract search query from your request.", "web_search_failed"
            
            # Generate multiple research angles for comprehensive coverage
            research_questions = self.ai.generate_research_questions(core_query, max_questions=4)
            
            if not research_questions:
                research_questions = [core_query]
            
            print(f"[Web Search] Core query: {core_query}")
            print(f"[Web Search] Research angles: {research_questions}")
            
            response = f"Researching {core_query}. This may take a moment..."

            # Search using multiple angles in parallel
            results_by_query = self.web_searcher.search_and_crawl_multi(
                research_questions,
                num_results=5,
                max_workers=4
            )

            any_results = any(results_by_query.values()) if results_by_query else False
            print(f"[Web Search] Got results: {any_results}, angles: {len(research_questions)}")

            if any_results:
                # Store in memory
                for q, url_map in results_by_query.items():
                    for url, content in url_map.items():
                        self.memory.add_web_context(q, url, content)

                # Extract key insights from all sources
                print("[Web Search] Extracting insights...")
                ai_response = self.ai.extract_key_insights(core_query, results_by_query)

                # Store conversation
                self.memory.add_conversation(command, ai_response, {"type": "web_search"})

                return ai_response, "web_search"
            else:
                # Fallback: try a simple LLM response without web context
                print("[Web Search] No results found. Using LLM for answer...")
                try:
                    ai_response = self.ai.generate_response(
                        f"Answer this question based on your knowledge: {command}",
                        temperature=0.5
                    )
                    self.memory.add_conversation(command, ai_response, {"type": "web_search_failed"})
                    return ai_response, "web_search"
                except Exception as e:
                    print(f"[Error] LLM fallback failed: {e}")
                    response = f"I couldn't find detailed information about {core_query}. Please try a more specific search."
                    self.memory.add_conversation(command, response, {"type": "web_search_failed"})
                    return response, "web_search_failed"
        
        # General conversation - use AI
        # Get relevant context from memory
        context = self.memory.get_relevant_context(command, n_results=3)
        
        # First, get AI response
        ai_response = self.ai.generate_response(command)
        
        # Check if the AI indicated it needs web search
        if self.ai.needs_web_search(ai_response):
            print("[General Query] AI signaled need for web search. Searching now...")
            
            # Generate research questions for comprehensive coverage
            research_questions = self.ai.generate_research_questions(command, max_questions=3)
            if not research_questions:
                research_questions = [command]
            
            print(f"[Research] Angles: {research_questions}")
            
            # Perform web search
            results_by_query = self.web_searcher.search_and_crawl_multi(
                research_questions,
                num_results=4,
                max_workers=4
            )
            
            any_results = any(results_by_query.values()) if results_by_query else False
            
            if any_results:
                # Store web context in memory
                for q, url_map in results_by_query.items():
                    for url, content in url_map.items():
                        self.memory.add_web_context(q, url, content)
                
                # Generate answer using web context
                ai_response = self.ai.answer_with_web_context(command, results_by_query)
            else:
                ai_response = "I searched for that information, but couldn't find enough results. Can you be more specific?"
        
        # Store conversation
        self.memory.add_conversation(command, ai_response, {"type": "general"})
        
        return ai_response, "general"

# --- Main Execution ---
if __name__ == "__main__":
    assistant = LocalAssistant()
    assistant.speak("System online. How can I help you?")

    try:
        while True:
            query = assistant.takeCommand()

            if "stop" in query or "exit" in query:
                assistant.speak("Shutting down. Goodbye!")
                break
            
            if query:
                # Placeholder for logic
                assistant.speak(f"You said {query}. I'm processing that.")

    except KeyboardInterrupt:
        print("\nStopped by user.")
