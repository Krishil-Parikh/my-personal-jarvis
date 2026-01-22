import os
import time
import threading
import re
import asyncio
import cv2
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from .app_launcher import open_application, extract_app_name
from .memory import ConversationMemory
from .ai_assistant import AIAssistant
from .camera import CameraCapture
from .enhanced_face_recognition import EnhancedFaceRecognizer

class LocalAssistant:
    """Voice assistant backed by Azure Speech for STT/TTS."""

    def __init__(self, signals=None):
        # Load environment (.env)
        load_dotenv()
        
        # UI signals for frontend logging
        self.signals = signals

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
        self.memory = ConversationMemory()
        self.ai = AIAssistant()
        
        # Face recognition (lazy loaded)
        self.face_recognizer = None
        self.camera = None
        self.camera_active = False
        self.face_save_mode = False
        self.face_save_name = None
        
        # Interruption support
        self.is_speaking = False
        self.stop_speaking = False
        self.speaking_lock = threading.Lock()
        self._synth = None

    def speak(self, text, emotion: str = "neutral"):
        """Text to speech via Azure with interruption support (chunked)."""
        # Emit to frontend FIRST (simple format)
        if self.signals:
            self.signals.log_message.emit(text, "jarvis")
        
        # Print to console (formatted)
        max_width = 100
        lines = text.split('\n')
        
        print("\n" + "=" * max_width)
        for line in lines:
            if len(line) > max_width:
                # Word wrap long lines
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_width:
                        current_line += word + " "
                    else:
                        if current_line:
                            print(f"🤖 {current_line.strip():<{max_width-2}}")
                        current_line = word + " "
                if current_line:
                    print(f"🤖 {current_line.strip():<{max_width-2}}")
            else:
                print(f"🤖 {line:<{max_width-2}}")
        print("=" * max_width + "\n", flush=True)
        
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
                        print("\n⚠️ [INTERRUPTED] Speech stopped by user!\n")
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
                        print("\n🛑 [WAKE WORD DETECTED - INTERRUPTING NOW!]\n")
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
    
    # ============================================================
    # CAMERA & FACE RECOGNITION METHODS
    # ============================================================
    
    def init_camera(self):
        """Initialize camera if not already active"""
        # Stop existing camera if any
        if self.camera is not None and not self.camera.is_opened():
            try:
                self.camera.stop()
                self.camera = None
            except:
                self.camera = None
        
        # Create new camera
        if self.camera is None:
            print("📷 Initializing camera...")
            self.camera = CameraCapture(camera_id=0)
            self.camera.start()
            time.sleep(1)  # Give camera time to warm up
            
        if self.face_recognizer is None:
            print("🤖 Initializing face recognition...")
            self.face_recognizer = EnhancedFaceRecognizer()
        
        self.camera_active = True
        opened = self.camera.is_opened()
        if opened:
            print("📷 Camera ready")
        else:
            print("❌ Camera failed to open")
        return opened
    
    def stop_camera(self):
        """Stop camera"""
        if self.camera:
            self.camera.stop()
            self.camera_active = False
            print("📷 Camera stopped")
    
    def look_at_camera(self):
        """Open camera and show live feed in frontend"""
        if not self.init_camera():
            return "Sorry, I couldn't access the camera."
        
        # Camera feed will show in frontend automatically via camera_active flag
        return "Camera feed active. Say 'stop camera' to close."
    
    def save_face(self, name=None):
        """Save current face from camera"""
        if not self.camera_active or self.camera is None:
            if not self.init_camera():
                return "Sorry, I couldn't access the camera."
        
        # Ask for name if not provided
        if name is None:
            self.speak("What name should I save this face under?")
            name_command = self.takeCommand()
            if not name_command:
                return "I didn't catch the name. Please try again."
            
            # Extract name from command
            name = name_command.replace("save as", "").replace("name is", "").strip()
            
            if not name or len(name) < 2:
                return "Invalid name. Please try again."
        
        self.speak(f"Saving face as {name}. Please position your face clearly in the center and stay still.")
        
        # Show live feed with quality check
        cv2.namedWindow("Face Registration", cv2.WINDOW_NORMAL)
        
        countdown = 3
        saved = False
        message = ""
        
        try:
            while countdown > 0:
                frame = self.camera.get_frame()
                if frame is None:
                    continue
                
                # Check face quality
                is_good, confidence, bbox, quality_msg = self.face_recognizer.check_face_quality(frame)
                
                # Draw bbox if available
                if bbox is not None:
                    x1, y1, x2, y2 = [int(c) for c in bbox]
                    color = (0, 255, 0) if is_good else (0, 165, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                
                # Show status
                status_color = (0, 255, 0) if is_good else (0, 165, 255)
                cv2.putText(frame, quality_msg, (30, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
                
                if is_good:
                    cv2.putText(frame, f"Capturing in {countdown}...", (30, 80), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                cv2.imshow("Face Registration", frame)
                cv2.waitKey(1)
                
                if is_good:
                    time.sleep(1)
                    countdown -= 1
                    
                    if countdown == 0:
                        # Save the face
                        success, msg, path = self.face_recognizer.save_face(frame, name)
                        saved = success
                        message = msg
                        
                        if success:
                            self.speak(f"Face saved successfully! Welcome, {name}!")
                        else:
                            self.speak(f"Failed to save face. {msg}")
                        
                        break
        
        finally:
            cv2.destroyAllWindows()
        
        return message
    
    def authenticate_user(self):
        """Authenticate user using face recognition"""
        if not self.init_camera():
            return False, "Camera not available"
        
        self.speak("Please look at the camera for authentication.")
        
        cv2.namedWindow("Authentication", cv2.WINDOW_NORMAL)
        
        max_attempts = 30  # 3 seconds at 10 fps
        attempts = 0
        authenticated = False
        user_name = None
        
        try:
            while attempts < max_attempts:
                frame = self.camera.get_frame()
                if frame is None:
                    attempts += 1
                    continue
                
                auth, user, similarity, annotated_frame, bbox = self.face_recognizer.recognize_face(frame)
                
                cv2.imshow("Authentication", annotated_frame)
                cv2.waitKey(100)  # 10 fps
                
                if auth:
                    authenticated = True
                    user_name = user
                    break
                
                attempts += 1
        
        finally:
            cv2.destroyAllWindows()
            self.stop_camera()
        
        if authenticated:
            self.speak(f"Authentication successful. Welcome back, {user_name}!")
            return True, user_name
        else:
            self.speak("Authentication failed. Face not recognized.")
            return False, None
    
    def authenticate_on_startup(self):
        """Authenticate user on system startup - allows secondary users to log in"""
        if not self.init_camera():
            print("[SYSTEM] Camera not available for authentication")
            return False, "Primary User"
        
        print("[SYSTEM] Waiting for face authentication...")
        
        cv2.namedWindow("System Authentication", cv2.WINDOW_NORMAL)
        
        max_attempts = 50  # 5 seconds at 10 fps
        attempts = 0
        authenticated = False
        user_name = None
        
        try:
            while attempts < max_attempts:
                frame = self.camera.get_frame()
                if frame is None:
                    attempts += 1
                    continue
                
                auth, user, similarity, annotated_frame, bbox = self.face_recognizer.recognize_face(frame)
                
                # Show authentication status
                if auth:
                    status_text = f"Welcome {user}! (Similarity: {similarity:.2f})"
                    color = (0, 255, 0)
                else:
                    status_text = f"Looking for known face... {attempts}/{max_attempts}"
                    color = (0, 165, 255)
                
                cv2.putText(annotated_frame, status_text, (30, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                cv2.imshow("System Authentication", annotated_frame)
                cv2.waitKey(100)  # 10 fps
                
                if auth:
                    authenticated = True
                    user_name = user
                    break
                
                attempts += 1
        
        finally:
            cv2.destroyAllWindows()
            self.stop_camera()
        
        if authenticated:
            print(f"[SYSTEM] Access Granted! User: {user_name}, Similarity: {similarity:.2f}")
        else:
            print(f"[SYSTEM] Authentication timeout. Using default access.")
            user_name = "Primary User"
        
        return authenticated, user_name
    
    def analyze_camera_view(self, query="What do you see in this image?"):
        """
        Analyze what's currently visible in the camera using VLM
        
        Args:
            query: User's question about what they're seeing
        
        Returns:
            str: AI's analysis of the camera view
        """
        if not self.camera_active or self.camera is None:
            if not self.init_camera():
                return "Sorry, I couldn't access the camera."
        
        # Get current frame
        frame = self.camera.get_frame()
        if frame is None:
            return "Sorry, I couldn't capture an image from the camera."
        
        # Save frame for reference (optional)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join("screenshots", f"camera_analysis_{timestamp}.jpg")
        os.makedirs("screenshots", exist_ok=True)
        cv2.imwrite(screenshot_path, frame)
        print(f"📸 Saved camera frame: {screenshot_path}")
        
        # Show analyzing message
        self.speak("Let me analyze what I'm seeing...")
        
        # Analyze with VLM
        analysis = self.ai.analyze_camera_feed(frame, query)
        
        return analysis
    
    # ============================================================
    # COMMAND PROCESSING
    # ============================================================
    
    def process_command(self, command):
        """
        Process and execute user command
        
        Args:
            command: User voice command
        
        Returns:
            tuple: (response_text, command_type)
        """
        command_lower = command.lower()
        
        print(f"[DEBUG] Processing command: '{command_lower}'")
        
        # ===== CAMERA MODE FILTER =====
        # When camera is active, ONLY accept camera-related commands
        if self.camera_active:
            # Allow only: VLM queries, save face, stop camera
            camera_commands = [
                'tell me about this', 'tell me something about this', 'what do you see', 
                'describe this', 'analyze this', 'what is this', 'what am i looking at',
                'what am i holding', 'what is in my hand', 'identify this',
                'save this face', 'save face', 'register face', 'save my face', 'add this face',
                'stop camera', 'close camera', 'exit camera', 'turn off camera'
            ]
            
            is_camera_command = any(phrase in command_lower for phrase in camera_commands)
            
            if not is_camera_command:
                response = "Camera is active. I can only process camera commands like 'tell me about this', 'save this face', or 'stop camera'."
                self.memory.add_conversation(command, response, {"type": "camera_mode_restriction"})
                return response, "camera_mode_restriction"
        
        # ===== CAMERA COMMANDS (HIGHEST PRIORITY) =====
        # Check for camera analysis (VLM) FIRST - before web search
        if any(phrase in command_lower for phrase in ['tell me about this', 'tell me something about this', 'what do you see', 'describe this', 'analyze this', 'what is this', 'what am i looking at']):
            if not self.camera_active:
                response = "The camera is not active. Say 'look at camera' first."
                self.memory.add_conversation(command, response, {"type": "camera_error"})
                return response, "camera_error"
            
            # Extract the user's specific question if present
            user_query = command
            
            # Analyze the camera view
            response = self.analyze_camera_view(user_query)
            self.memory.add_conversation(command, response, {"type": "camera_analysis"})
            return response, "camera_analysis"
        
        # Check for face saving
        if any(phrase in command_lower for phrase in ['save this face', 'save face', 'register face', 'save my face']):
            if not self.camera_active:
                response = "The camera is not active. Say 'look at camera' first."
                self.memory.add_conversation(command, response, {"type": "camera_error"})
                return response, "camera_error"
            
            response = self.save_face()
            self.memory.add_conversation(command, response, {"type": "face_save"})
            return response, "face_save"
        
        # Check for camera commands
        if any(phrase in command_lower for phrase in ['look at camera', 'look at the camera', 'open camera', 'show camera', 'camera']):
            response = self.look_at_camera()  # Blocking call - pauses listening while camera active
            self.memory.add_conversation(command, response, {"type": "camera"})
            return response, "camera"
        
        if any(phrase in command_lower for phrase in ['stop camera', 'close camera']):
            self.camera_active = False
            self.stop_camera()
            response = "Camera stopped"
            self.memory.add_conversation(command, response, {"type": "camera"})
            return response, "camera"
        
        if any(phrase in command_lower for phrase in ['exit camera', 'turn off camera']):
            self.camera_active = False
            self.stop_camera()
            response = "Camera stopped"
            self.memory.add_conversation(command, response, {"type": "camera"})
            return response, "camera"
        
        # ===== AUTHENTICATION COMMANDS =====
        if any(phrase in command_lower for phrase in ['authenticate', 'verify me', 'check my face', 'login']):
            success, user = self.authenticate_user()
            response = f"Authenticated as {user}" if success else "Authentication failed"
            self.memory.add_conversation(command, response, {"type": "authentication"})
            return response, "authentication"
        
        # ===== AUTHENTICATION COMMANDS =====
        if any(phrase in command_lower for phrase in ['authenticate', 'verify me', 'check my face', 'login']):
            success, user = self.authenticate_user()
            response = f"Authenticated as {user}" if success else "Authentication failed"
            self.memory.add_conversation(command, response, {"type": "authentication"})
            return response, "authentication"
        
        if any(phrase in command_lower for phrase in ['list faces', 'who do you know', 'registered faces']):
            faces = self.face_recognizer.list_faces() if self.face_recognizer else []
            if faces:
                response = f"I have {len(faces)} registered face(s): {', '.join(faces)}"
            else:
                response = "No faces registered yet"
            self.memory.add_conversation(command, response, {"type": "face_list"})
            return response, "face_list"
        
        # ===== SYSTEM COMMANDS =====
        if any(word in command_lower for word in ['sleep', 'go to sleep']):
            response = "Putting system to sleep"
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            self.memory.add_conversation(command, response, {"type": "sleep"})
            return response, "sleep"

        # Check for shutdown - but NOT 'stop camera'
        shutdown_phrases = ['good bye jarvis', 'goodbye jarvis', 'shutdown system', 'turn off system', 'shutdown']
        if any(phrase in command_lower for phrase in shutdown_phrases) and 'camera' not in command_lower:
            response = "Shutting down. Goodbye!"
            self.memory.add_conversation(command, response, {"type": "shutdown"})
            os.system("shutdown /s /t 0")
            return response, "shutdown"
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
            response = f"Searching for information. This may take a moment..."
            
            # Use the intelligent web search system
            try:
                # Run async search in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                search_result = loop.run_until_complete(
                    self.ai.answer_with_intelligent_search(command, force_browser=False)
                )
                
                loop.close()
                
                ai_response = search_result.get('answer', 'I could not find information on that.')
                
                # Store conversation with sources (convert list to string for ChromaDB)
                sources = search_result.get('sources', [])
                metadata = {
                    "type": "web_search",
                    "sources": ", ".join(sources) if sources else "none"
                }
                self.memory.add_conversation(command, ai_response, metadata)
                
                return ai_response, "web_search"
                
            except Exception as e:
                print(f"[Error] Web search failed: {e}")
                response = "I encountered an error while searching. Please try again."
                self.memory.add_conversation(command, response, {"type": "web_search_failed"})
                return response, "web_search_failed"
        
        # General conversation - use AI
        # Get relevant context from memory
        context = self.memory.get_relevant_context(command, n_results=3)
        
        # Use the integrated process_query which handles web search automatically
        try:
            # Check if we need async (for potential web search)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # First try with AI to see if web search is needed
            ai_response = self.ai.generate_response(command)
            
            # Check if the AI indicated it needs web search
            if self.ai.needs_web_search(ai_response):
                print("[General Query] AI signaled need for web search. Searching now...")
                
                search_result = loop.run_until_complete(
                    self.ai.answer_with_intelligent_search(command, force_browser=False)
                )
                
                ai_response = search_result.get('answer', ai_response)
                
                # Store with sources (convert list to string for ChromaDB)
                sources = search_result.get('sources', [])
                metadata = {
                    "type": "general_with_search",
                    "sources": ", ".join(sources) if sources else "none"
                }
                self.memory.add_conversation(command, ai_response, metadata)
            else:
                # Store regular conversation
                self.memory.add_conversation(command, ai_response, {"type": "general"})
            
            loop.close()
            
        except Exception as e:
            print(f"[Error] General query processing failed: {e}")
            ai_response = "I'm having trouble processing that. Could you rephrase?"
            self.memory.add_conversation(command, ai_response, {"type": "error"})
        
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
