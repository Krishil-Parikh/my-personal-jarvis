import cv2
import threading
import time
from collections import deque
import numpy as np


class CameraCapture:
    def __init__(self, camera_id=0, width=640, height=480, backend=cv2.CAP_DSHOW):
        """
        backend options (Windows):
        - cv2.CAP_DSHOW     → usually fixes black screen
        - cv2.CAP_MSMF      → Microsoft Media Foundation (good alternative)
        - cv2.CAP_ANY       → let OpenCV choose (often fails)
        """
        print(f"[Camera] Trying to open camera {camera_id} with backend {backend}")
        self.cap = cv2.VideoCapture(camera_id, backend)
        
        if not self.cap.isOpened():
            print(f"[Camera] ERROR: Failed to open camera {camera_id}")
            self.cap = None
            self.is_running = False
            return

        # Try to set resolution (some cameras ignore it)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Camera] Opened {self.width}x{self.height}")

        self.current_frame = None
        self.lock = threading.Lock()           # ← critical for thread safety
        self.is_running = False
        self.thread = None

        # Small queue to avoid using very stale frames
        self.frame_queue = deque(maxlen=2)

    def start(self):
        """Start capture thread if not already running"""
        if self.cap is None:
            print("[Camera] Cannot start - capture not opened")
            return

        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._capture_frames, daemon=True)
            self.thread.start()
            print("[Camera] Capture thread started")
            time.sleep(0.5)  # give thread time to grab first frame

    def stop(self):
        """Stop capture and clean up"""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        print("[Camera] Camera stopped & released")

    def _capture_frames(self):
        """Background capture loop"""
        while self.is_running:
            if self.cap is None:
                break

            ret, frame = self.cap.read()
            if ret:
                # Optional: resize if camera didn't honor set()
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = cv2.resize(frame, (self.width, self.height))

                with self.lock:
                    self.current_frame = frame.copy()   # copy to avoid race issues
                    self.frame_queue.append(frame.copy())

            else:
                print("[Camera] WARNING: cap.read() failed")
                time.sleep(0.1)  # avoid CPU spin

            time.sleep(0.033)  # ~30 fps cap

    def get_frame(self):
        """Get latest BGR frame (thread-safe)"""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def get_frame_rgb(self):
        """Get latest RGB frame or None"""
        frame = self.get_frame()
        if frame is not None:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()