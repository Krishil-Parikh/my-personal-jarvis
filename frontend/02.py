import sys
import cv2
import os
import numpy as np
import threading
import time
import psutil
from collections import deque
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QFrame, QSizePolicy, QSpacerItem, QTextEdit, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPixmap, QColor, QPalette, QFont, QPainter
try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
    pg.setConfigOption('background', '#0a0a0a')
    pg.setConfigOption('foreground', '#00ff88')
except ImportError:
    HAS_PYQTGRAPH = False

# Adjust import path according to your folder structure
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.camera import CameraCapture
from backend.face_recognition import FaceRecognizer
from backend.voice_assistant import LocalAssistant
import pyttsx3


class SystemMonitor:
    """Monitor system metrics (CPU, memory, disk usage)."""
    
    def __init__(self, max_history=60):
        self.max_history = max_history
        self.cpu_history = deque(maxlen=max_history)
        self.memory_history = deque(maxlen=max_history)
        self.disk_history = deque(maxlen=max_history)
        self.last_net_io = None
    
    def get_cpu_usage(self):
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.05)
    
    def get_memory_usage(self):
        """Get current memory usage percentage."""
        return psutil.virtual_memory().percent
    
    def get_disk_usage(self):
        """Get disk usage percentage."""
        try:
            return psutil.disk_usage('/').percent
        except Exception:
            try:
                return psutil.disk_usage('C:\\').percent
            except Exception:
                return 0
    
    def get_network_info(self):
        """Get network I/O stats."""
        try:
            net_io = psutil.net_io_counters()
            if self.last_net_io:
                time_delta = 1
                bytes_in = (net_io.bytes_recv - self.last_net_io.bytes_recv) / time_delta / 1024 / 1024  # MB/s
                bytes_out = (net_io.bytes_sent - self.last_net_io.bytes_sent) / time_delta / 1024 / 1024
                self.last_net_io = net_io
                return bytes_in, bytes_out
            else:
                self.last_net_io = net_io
                return 0, 0
        except Exception:
            return 0, 0
    
    def get_cpu_temp(self):
        """Get CPU temperature if available."""
        try:
            temps = psutil.sensors_temperatures()
            if temps and 'coretemp' in temps:
                return temps['coretemp'][0].current
            elif temps:
                first_key = list(temps.keys())[0]
                return temps[first_key][0].current
        except Exception:
            pass
        return 0
    
    def update_metrics(self):
        """Collect and store current metrics."""
        self.cpu_history.append(self.get_cpu_usage())
        self.memory_history.append(self.get_memory_usage())
        self.disk_history.append(self.get_disk_usage())
    
    def get_current_metrics(self):
        """Get current metric values."""
        cpu = psutil.cpu_percent(interval=0.05)
        memory = psutil.virtual_memory().percent
        disk = self.get_disk_usage()
        net_in, net_out = self.get_network_info()
        temp = self.get_cpu_temp()
        return {
            'cpu': cpu,
            'memory': memory,
            'disk': disk,
            'net_in': net_in,
            'net_out': net_out,
            'temp': temp
        }


class VoiceAssistantSignals(QObject):
    """Signals for thread-safe UI updates"""
    log_message = pyqtSignal(str, str)  # (message, type)
    task_update = pyqtSignal(str, str)  # (state, text)


class VoiceAssistantThread(threading.Thread):
    """Run voice assistant in background thread with parallel STT/TTS"""
    def __init__(self, signals):
        super().__init__(daemon=True)
        self.signals = signals
        self.running = True
        self.assistant = None
    
    def get_task_type_title(self, command_type):
        """Get a short title for the task type"""
        titles = {
            "app_launch": "Opening App",
            "web_search": "Web Search",
            "web_search_failed": "Search Failed",
            "sleep": "System Sleep",
            "shutdown": "Shutting Down",
            "general": "Processing"
        }
        return titles.get(command_type, command_type)
    
    def run(self):
        try:
            self.signals.log_message.emit("Initializing voice system...", "system")
            self.assistant = LocalAssistant(signals=self.signals)  # Pass signals to assistant
            
            # Authenticate user on startup - allows secondary users to log in
            authenticated, user_name = self.assistant.authenticate_on_startup()
            
            if authenticated:
                self.signals.log_message.emit(f"Access Granted! User: {user_name}", "system")
            else:
                self.signals.log_message.emit("Authentication timeout. Using default access.", "system")
            self.assistant_ref = self.assistant  # Store reference for interruption
            self.signals.log_message.emit("System online. Ready for commands.", "system")
            
            # Speak startup in a non-blocking thread
            speak_thread = threading.Thread(
                target=self.assistant.speak,
                args=("System online. Ready for commands.",),
                daemon=True
            )
            speak_thread.start()
            speak_thread.join(timeout=3)  # Wait for startup speech to finish
            # Ensure TTS fully stops before first listen to avoid self-hearing
            while self.assistant.is_speaking:
                time.sleep(0.2)
            time.sleep(0.6)
            
            while self.running:
                # Check if currently speaking and show appropriate listening message
                if self.assistant.is_speaking:
                    self.signals.log_message.emit("Listening for wake word to interrupt...", "status")
                else:
                    self.signals.log_message.emit("Listening...", "status")
                    
                # If somehow still speaking, wait a bit before listening
                while self.assistant.is_speaking and self.running:
                    time.sleep(0.2)
                # Short settle delay to reduce residual echo from speakers
                time.sleep(0.4)
                # Listen for command normally (no wake word needed)
                query = self.assistant.takeCommand(interrupt_mode=False)
                
                if not self.running:
                    break
                
                if query:
                    self.signals.log_message.emit(query, "user")
                    
                    if "stop" in query or "exit" in query or "shutdown" in query:
                        self.signals.log_message.emit("Shutting down voice system.", "jarvis")
                        self.assistant.speak("Shutting down. Goodbye!")
                        break
                    
                    try:
                        # Extract command type first
                        response, command_type = self.assistant.process_command(query)
                        print(f"\n[DEBUG] Response: {response}")
                        print(f"[DEBUG] Command type: {command_type}")
                        
                        task_title = self.get_task_type_title(command_type)
                        
                        # Emit task update with short title
                        self.signals.task_update.emit("active", task_title)
                        self.signals.log_message.emit("Processing...", "status")
                        
                        # Speak response (assistant.speak() already emits to frontend)
                        completed = self._speak_with_interruption(response)
                        
                        # Only mark done if speech completed (not interrupted)
                        if completed:
                            self.signals.task_update.emit("done", task_title)
                        # Don't emit again - speak() already did it
                    except Exception as cmd_error:
                        error_msg = f"Command error: {str(cmd_error)}"
                        print(f"[ERROR] {error_msg}")
                        self.signals.log_message.emit(error_msg, "error")
        
        except Exception as e:
            self.signals.log_message.emit(f"Error: {str(e)}", "error")
    
    def _speak_with_interruption(self, text):
        """Speak while listening for interruption (wake word 'Hey Jarvis').
        Returns True if speech completed, False if interrupted.
        """
        # Start speaking in background thread
        speak_thread = threading.Thread(
            target=self.assistant.speak,
            args=(text,),
            daemon=True
        )
        speak_thread.start()
        
        # Wait initial 1.5 seconds before listening for interruption
        # This avoids the system picking up its own speech
        time.sleep(1.5)
        
        # Keep listening for interruption while speaking
        max_wait = 0
        interrupted = False
        while self.assistant.is_speaking and self.running and max_wait < 30:
            try:
                # Listen for interrupt with 2 second recognition window
                interrupt_cmd = self.assistant.takeCommand(interrupt_mode=True)
                if interrupt_cmd == "INTERRUPTED":
                    self.signals.log_message.emit("🛑 Speech interrupted by user!", "status")
                    interrupted = True
                    break
            except Exception as e:
                print(f"Interrupt listen error: {e}")
            
            # Small sleep to prevent busy-waiting
            time.sleep(0.1)
            max_wait += 0.1
        
        # Wait for speech to finish (with timeout)
        speak_thread.join(timeout=2)
        return not interrupted
    
    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Glassmorphic Camera App – PyQt6")
        self.resize(1280, 720)

        self.setStyleSheet("background-color: #000000;")

        # ── Central widget + main horizontal layout ──────────────────
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Left column (now mostly empty + camera in top-right) ─────
        left_panel = self._create_glass_panel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # Small camera preview container
        camera_container = QWidget()
        camera_container.setFixedSize(360, 280)           # ← adjust size here
        camera_container.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
                border: 2px solid #00b3ff;
                border-radius: 12px;
            }
        """)

        camera_inner_layout = QVBoxLayout(camera_container)
        camera_inner_layout.setContentsMargins(4, 4, 4, 4)
        camera_inner_layout.setSpacing(4)

        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setStyleSheet("background-color: black; border-radius: 8px;")
        self.camera_label.setText("Camera starting...")

        self.status_label = QLabel("Camera OFF")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #ff4d4d; font-size: 13px; font-weight: bold;")

        camera_inner_layout.addWidget(self.camera_label)
        camera_inner_layout.addWidget(self.status_label)

        # Add camera to top-right of left column
        left_layout.addWidget(camera_container)
        left_layout.addStretch(1)   # push everything else down / leave space

        # ── Middle panel (Terminal) ───────────────────────────────────
        middle_panel = self._create_glass_panel()
        middle_layout = QVBoxLayout(middle_panel)
        middle_layout.setContentsMargins(15, 15, 15, 15)
        middle_layout.setSpacing(10)
        
        # Terminal header
        terminal_header = QLabel("JARVIS Terminal")
        terminal_header.setStyleSheet("""
            color: #00ff88;
            font-size: 24px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            padding: 5px;
        """)
        terminal_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        middle_layout.addWidget(terminal_header)
        
        # Terminal output (text display)
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a0a;
                color: #00ff88;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                border: 2px solid #00ff88;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        self.terminal_output.setFont(QFont("Consolas", 14))
        middle_layout.addWidget(self.terminal_output)
        
        # Welcome message
        self.append_terminal("=== JARVIS PERSONAL ASSISTANT ===", "system")
        self.append_terminal("System initializing...", "system")

        # ── Right panel (Tasks) ───────────────────────────────────────
        right_panel = self._create_glass_panel()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        tasks_label = QLabel("Task History")
        tasks_label.setStyleSheet("color: #4fcbf5; font-size: 18px; font-weight: bold;")
        right_layout.addWidget(tasks_label)

        # Unified task list (completed + active)
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                background-color: #0a0a0a;
                color: #00d9ff;
                border: 1px solid #00b3ff;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
        """)
        self.task_list.setMinimumHeight(240)
        right_layout.addWidget(self.task_list, stretch=1)

        # ── System Monitor Section ──────────────────────────────────
        sys_monitor_label = QLabel("System Monitor")
        sys_monitor_label.setStyleSheet("color: #4fcbf5; font-size: 14px; font-weight: bold;")
        right_layout.addWidget(sys_monitor_label)

        # Metrics display (text-based for quick reference)
        self.metrics_label = QLabel()
        self.metrics_label.setStyleSheet("""
            color: #00ff88;
            font-size: 11px;
            font-family: 'Consolas', monospace;
            background-color: #0a0a0a;
            border: 1px solid #00b3ff;
            border-radius: 4px;
            padding: 5px;
        """)
        self.metrics_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.metrics_label.setMaximumHeight(60)
        right_layout.addWidget(self.metrics_label)

        # Create graphs if pyqtgraph is available
        self.graphs_container = None
        if HAS_PYQTGRAPH:
            self.graphs_container = QWidget()
            graphs_layout = QVBoxLayout(self.graphs_container)
            graphs_layout.setContentsMargins(0, 5, 0, 0)
            graphs_layout.setSpacing(4)
            
            # CPU Graph
            self.cpu_graph = pg.PlotWidget(title="CPU Usage")
            self.cpu_graph.setStyleSheet("border: 1px solid #00b3ff; border-radius: 4px;")
            self.cpu_graph.setLabel('left', 'Usage %')
            self.cpu_graph.setLabel('bottom', 'Time (HH:MM:SS)')
            self.cpu_graph.setYRange(0, 100)
            self.cpu_graph.showGrid(x=True, y=True, alpha=0.2)
            self.cpu_line = self.cpu_graph.plot(pen=pg.mkPen('#00ff88', width=2), symbol='o', symbolSize=4)
            self.cpu_graph.setMaximumHeight(80)
            graphs_layout.addWidget(self.cpu_graph)
            
            # Memory Graph
            self.mem_graph = pg.PlotWidget(title="Memory Usage")
            self.mem_graph.setStyleSheet("border: 1px solid #00b3ff; border-radius: 4px;")
            self.mem_graph.setLabel('left', 'Usage %')
            self.mem_graph.setLabel('bottom', 'Time (HH:MM:SS)')
            self.mem_graph.setYRange(0, 100)
            self.mem_graph.showGrid(x=True, y=True, alpha=0.2)
            self.mem_line = self.mem_graph.plot(pen=pg.mkPen('#ff6b6b', width=2), symbol='o', symbolSize=4)
            self.mem_graph.setMaximumHeight(80)
            graphs_layout.addWidget(self.mem_graph)
            
            # Disk Graph
            self.disk_graph = pg.PlotWidget(title="Disk Usage")
            self.disk_graph.setStyleSheet("border: 1px solid #00b3ff; border-radius: 4px;")
            self.disk_graph.setLabel('left', 'Usage %')
            self.disk_graph.setLabel('bottom', 'Time (HH:MM:SS)')
            self.disk_graph.setYRange(0, 100)
            self.disk_graph.showGrid(x=True, y=True, alpha=0.2)
            self.disk_line = self.disk_graph.plot(pen=pg.mkPen('#4fcbf5', width=2), symbol='o', symbolSize=4)
            self.disk_graph.setMaximumHeight(80)
            graphs_layout.addWidget(self.disk_graph)
            
            right_layout.addWidget(self.graphs_container, stretch=1)

        # System monitor for tracking
        self.system_monitor = SystemMonitor(max_history=60)
        self.system_monitor_data = {
            'cpu': deque(maxlen=60),
            'memory': deque(maxlen=60),
            'disk': deque(maxlen=60),
            'timestamps': deque(maxlen=60)  # Track actual timestamps
        }

        # ── Assemble main layout ──────────────────────────────────────
        main_layout.addWidget(left_panel, stretch=25)
        main_layout.addWidget(self._create_vertical_separator())
        main_layout.addWidget(middle_panel, stretch=50)
        main_layout.addWidget(self._create_vertical_separator())
        main_layout.addWidget(right_panel, stretch=25)

        # ── Camera logic ──────────────────────────────────────────────
        self.camera = CameraCapture(camera_id=0, width=640, height=480)
        # If needed: self.camera = CameraCapture(camera_id=1, width=640, height=480)

        self.camera.start()
        
        # Initialize face recognition
        embedding_path = os.path.join(os.path.dirname(__file__), '..', 'learning', 'face-detection', 'krishil_face_embedding.npy')
        self.face_recognizer = FaceRecognizer(embedding_path=embedding_path)
        
        # Authentication state
        self.is_authenticated = False
        self.face_recognition_active = True

        # Update timer ~30 fps
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)

        # System monitor timer (every 1 second)
        self.sys_monitor_timer = QTimer(self)
        self.sys_monitor_timer.timeout.connect(self.update_system_metrics)
        self.sys_monitor_timer.start(1000)

        # Initial status
        self.status_label.setText("Camera initializing...")
        self.status_label.setStyleSheet("color: #ffcc00; font-size: 13px; font-weight: bold;")
        
        # Voice assistant (will be started after authentication)
        self.voice_signals = VoiceAssistantSignals()
        self.voice_signals.log_message.connect(self.handle_voice_message)
        self.voice_signals.task_update.connect(self.handle_task_update)
        self.voice_thread = None
        self.voice_assistant = None  # Will store reference to assistant
        
        # Terminal message
        self.append_terminal("Waiting for face authentication...", "system")

    def _create_glass_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: rgba(26, 35, 50, 170);
                border: 1px solid rgba(0, 179, 255, 70);
                border-radius: 16px;
                margin: 6px;
            }
        """)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return panel

    def _create_vertical_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setStyleSheet("color: #00d9ff; width: 2px;")
        sep.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        return sep

    def update_frame(self):
        # Check if voice assistant camera is active
        if self.voice_assistant and hasattr(self.voice_assistant, 'camera_active') and self.voice_assistant.camera_active:
            # Show voice assistant camera feed
            if self.voice_assistant.camera and self.voice_assistant.camera.is_opened():
                frame = self.voice_assistant.camera.get_frame()
                if frame is not None:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Display frame
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

                    pixmap = QPixmap.fromImage(image)
                    scaled = pixmap.scaled(
                        self.camera_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )

                    self.camera_label.setPixmap(scaled)
                    self.camera_label.setText("")
                    self.status_label.setText("Camera Active")
                    self.status_label.setStyleSheet("color: #00ff88; font-size: 13px; font-weight: bold;")
                    return
        
        # Only update if face recognition is active (before authentication)
        if not self.face_recognition_active or self.is_authenticated:
            # Camera off - show gray screen
            if not hasattr(self, '_camera_off_pixmap'):
                pixmap = QPixmap(self.camera_label.size())
                pixmap.fill(QColor("#1a1a1a"))  # Dark gray background
                painter = QPainter(pixmap)
                painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                painter.setPen(QColor("#666666"))  # Gray text
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "📷 Camera OFF")
                painter.end()
                self._camera_off_pixmap = pixmap
            
            self.camera_label.setPixmap(self._camera_off_pixmap)
            self.status_label.setText("Camera OFF")
            self.status_label.setStyleSheet("color: #ff4d4d; font-size: 13px; font-weight: bold;")
            return
        
        # Get frame from camera
        frame_rgb = self.camera.get_frame_rgb()

        if frame_rgb is not None:
            # Convert RGB to BGR for face recognition (OpenCV uses BGR)
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            
            # Run face recognition
            authenticated, similarity, annotated_frame = self.face_recognizer.recognize_face(frame_bgr)
            
            # Convert back to RGB for display
            frame_display = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            
            # Update status based on authentication
            if authenticated:
                status_text = f"Access Granted ({similarity:.2f})"
                status_color = "#51cf66"
                
                # First time authentication
                if not self.is_authenticated:
                    self.is_authenticated = True
                    self.face_recognition_active = False
                    
                    # Update terminal
                    self.append_terminal(f"Access Granted! Similarity: {similarity:.2f}", "system")
                    self.append_terminal("Starting voice assistant...", "system")
                    
                    # Start voice assistant
                    self.start_voice_assistant()
            else:
                if similarity > 0:
                    status_text = f"Unknown ({similarity:.2f})"
                    status_color = "#ff6b6b"
                else:
                    status_text = "Scanning..."
                    status_color = "#ffcc00"
            
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(f"color: {status_color}; font-size: 13px; font-weight: bold;")
            
            # Display frame
            h, w, ch = frame_display.shape
            bytes_per_line = ch * w
            image = QImage(frame_display.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

            # Scale to fit the small preview label
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(
                self.camera_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.camera_label.setPixmap(scaled)
            self.camera_label.setText("")  # remove placeholder
        else:
            # No frame available - show gray screen
            if not hasattr(self, '_camera_off_pixmap'):
                pixmap = QPixmap(self.camera_label.size())
                pixmap.fill(QColor("#1a1a1a"))  # Dark gray background
                painter = QPainter(pixmap)
                painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                painter.setPen(QColor("#666666"))  # Gray text
                painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "📷 Camera OFF")
                painter.end()
                self._camera_off_pixmap = pixmap
            
            self.camera_label.setPixmap(self._camera_off_pixmap)
    
    def start_voice_assistant(self):
        """Start the voice assistant after authentication"""
        if self.voice_thread is None:
            # Speak "Access Granted"
            try:
                tts_engine = pyttsx3.init()
                tts_engine.setProperty('rate', 175)
                tts_engine.say("Access Granted. Voice assistant activated.")
                tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")
            
            # Start voice thread
            self.voice_thread = VoiceAssistantThread(self.voice_signals)
            self.voice_thread.start()
            
            # Wait briefly for assistant to initialize, then store reference
            import time
            time.sleep(0.5)
            if self.voice_thread and hasattr(self.voice_thread, 'assistant'):
                self.voice_assistant = self.voice_thread.assistant
            
            # Update status
            self.status_label.setText("Voice Assistant Active")
            self.status_label.setStyleSheet("color: #00ff88; font-size: 13px; font-weight: bold;")
    
    def append_terminal(self, message, msg_type="system"):
        """Append message to terminal with appropriate styling"""
        color_map = {
            "system": "#00ff88",    # Green
            "status": "#ffcc00",    # Yellow
            "user": "#00d9ff",      # Cyan
            "jarvis": "#ff6b6b",    # Red/Pink
            "error": "#ff4d4d"      # Bright red
        }
        
        prefix_map = {
            "system": "[SYSTEM]",
            "status": "[STATUS]",
            "user": "USER >>",
            "jarvis": "JARVIS >>",
            "error": "[ERROR]"
        }
        
        color = color_map.get(msg_type, "#00ff88")
        prefix = prefix_map.get(msg_type, "")
        
        # Format message
        formatted = f'<span style="color: {color};">{prefix} {message}</span>'
        
        # Append to terminal
        self.terminal_output.append(formatted)
        
        # Auto-scroll to bottom
        scrollbar = self.terminal_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def handle_voice_message(self, message, msg_type):
        """Handle messages from voice assistant thread"""
        self.append_terminal(message, msg_type)

    def handle_task_update(self, status: str, description: str):
        """
        Handle task updates with unified list.
        status: 'active' or 'done'
        description: short task title (e.g., "Web Search", "Opening App")
        """
        if status == "active":
            # Add as active task at the top with green LED indicator
            item = QListWidgetItem(f"● {description}")
            item.setData(Qt.ItemDataRole.UserRole, "active")
            item.setForeground(QColor("#00ff88"))  # Green for active
            item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            self.task_list.insertItem(0, item)
            
        elif status == "done":
            # Move the active task to completed (less opaque)
            found = False
            for i in range(self.task_list.count()):
                item = self.task_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == "active":
                    # Change to completed style (less opaque)
                    item.setText(f"✓ {description}")
                    item.setData(Qt.ItemDataRole.UserRole, "done")
                    item.setForeground(QColor("#7a8a96"))  # Faded gray for completed
                    item.setFont(QFont("Arial", 10))
                    found = True
                    break
            
            # Keep list to reasonable length
            if self.task_list.count() > 30:
                self.task_list.takeItem(self.task_list.count() - 1)

    def update_system_metrics(self):
        """Update system metrics display and graphs"""
        try:
            metrics = self.system_monitor.get_current_metrics()
            
            # Format metrics text
            metrics_text = (
                f"CPU:     {metrics['cpu']:.1f}%  |  "
                f"Memory:  {metrics['memory']:.1f}%  |  "
                f"Disk:    {metrics['disk']:.1f}%"
            )
            
            if metrics['temp'] > 0:
                metrics_text += f"  |  Temp: {metrics['temp']:.1f}°C"
            
            self.metrics_label.setText(metrics_text)
            
            # Update histories with timestamps
            from datetime import datetime
            current_time = datetime.now()
            time_str = current_time.strftime('%H:%M:%S')
            
            self.system_monitor_data['cpu'].append(metrics['cpu'])
            self.system_monitor_data['memory'].append(metrics['memory'])
            self.system_monitor_data['disk'].append(metrics['disk'])
            self.system_monitor_data['timestamps'].append(time_str)
            
            # Update graphs if available
            if HAS_PYQTGRAPH and self.graphs_container:
                x_data = list(range(len(self.system_monitor_data['cpu'])))
                time_labels = list(self.system_monitor_data['timestamps'])
                
                # Create x-axis ticks with time labels (every 5th or last point)
                num_points = len(time_labels)
                tick_interval = max(1, num_points // 5)
                x_ticks = [(i, time_labels[i] if i % tick_interval == 0 or i == num_points - 1 else '') 
                           for i in range(num_points)]
                
                # CPU graph
                self.cpu_graph.getAxis('bottom').setTicks([x_ticks])
                self.cpu_line.setData(x_data, list(self.system_monitor_data['cpu']))
                
                # Memory graph
                self.mem_graph.getAxis('bottom').setTicks([x_ticks])
                self.mem_line.setData(x_data, list(self.system_monitor_data['memory']))
                
                # Disk graph
                self.disk_graph.getAxis('bottom').setTicks([x_ticks])
                self.disk_line.setData(x_data, list(self.system_monitor_data['disk']))
        
        except Exception as e:
            print(f"Error updating system metrics: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'voice_thread'):
            self.voice_thread.stop()
            self.voice_thread.join(timeout=2)
        if hasattr(self, 'camera'):
            self.camera.stop()
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'sys_monitor_timer'):
            self.sys_monitor_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Dark theme
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#121212"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())