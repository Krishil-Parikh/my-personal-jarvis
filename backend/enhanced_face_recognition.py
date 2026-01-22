"""
Enhanced Face Recognition System with Save/Authentication capabilities
Integrates with Voice Assistant for camera-based authentication
"""

import cv2
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import os
import time
from datetime import datetime

class EnhancedFaceRecognizer:
    def __init__(self, embeddings_dir="face_embeddings"):
        """Initialize face recognition with save/load capabilities"""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Create embeddings directory
        self.embeddings_dir = embeddings_dir
        os.makedirs(embeddings_dir, exist_ok=True)
        
        # Load models
        print("🔄 Loading face recognition models...")
        self.mtcnn = MTCNN(
            image_size=160, 
            margin=20, 
            min_face_size=40, 
            device=self.device,
            post_process=False
        )
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        print("✅ Face recognition models loaded")
        
        # Known faces database
        self.known_faces = {}  # {name: embedding}
        self.load_all_faces()
        
        # Thresholds
        self.similarity_threshold = 0.75  # Recognition threshold (strict)
        self.quality_threshold = 0.8  # Minimum face quality for saving
        
        # Status
        self.is_authenticated = False
        self.authenticated_user = None
        self.current_similarity = 0.0
    
    def load_all_faces(self):
        """Load all saved face embeddings"""
        if not os.path.exists(self.embeddings_dir):
            return
        
        for filename in os.listdir(self.embeddings_dir):
            if filename.endswith(".npy"):
                name = filename.replace("_embedding.npy", "")
                embedding_path = os.path.join(self.embeddings_dir, filename)
                try:
                    embedding = np.load(embedding_path)
                    self.known_faces[name] = embedding
                    print(f"📁 Loaded face: {name}")
                except Exception as e:
                    print(f"⚠️ Error loading {filename}: {e}")
        
        print(f"✅ Loaded {len(self.known_faces)} face(s)")
    
    def check_face_quality(self, frame):
        """
        Check if face in frame is good quality for saving
        Returns: (is_good, confidence, face_bbox, message)
        """
        try:
            # Convert to PIL
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Detect face with bounding box
            boxes, probs = self.mtcnn.detect(img)
            
            if boxes is None or len(boxes) == 0:
                return False, 0.0, None, "No face detected"
            
            if len(boxes) > 1:
                return False, 0.0, None, "Multiple faces detected - please ensure only one person"
            
            # Get face confidence and position
            box = boxes[0]
            confidence = probs[0]
            
            # Check confidence
            if confidence < 0.95:
                return False, confidence, box, f"Face confidence too low ({confidence:.2f})"
            
            # Check if face is centered and large enough
            frame_h, frame_w = frame.shape[:2]
            x1, y1, x2, y2 = box
            face_w = x2 - x1
            face_h = y2 - y1
            
            # Face should be at least 30% of frame width
            if face_w < frame_w * 0.3:
                return False, confidence, box, "Face too small - move closer"
            
            # Face should be reasonably centered
            face_center_x = (x1 + x2) / 2
            face_center_y = (y1 + y2) / 2
            
            if abs(face_center_x - frame_w/2) > frame_w * 0.3:
                return False, confidence, box, "Face not centered horizontally"
            
            if abs(face_center_y - frame_h/2) > frame_h * 0.3:
                return False, confidence, box, "Face not centered vertically"
            
            return True, confidence, box, "Perfect! Face is clear and centered"
            
        except Exception as e:
            return False, 0.0, None, f"Error: {str(e)}"
    
    def save_face(self, frame, name):
        """
        Save a face from the current frame
        Returns: (success, message, embedding_path)
        """
        try:
            # First check quality
            is_good, confidence, bbox, message = self.check_face_quality(frame)
            
            if not is_good:
                return False, message, None
            
            # Convert to PIL
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Get face tensor
            face = self.mtcnn(img)
            
            if face is None:
                return False, "Failed to extract face", None
            
            # Generate embedding
            with torch.no_grad():
                embedding = self.resnet(face.unsqueeze(0).to(self.device)).detach().cpu().numpy()[0]
            
            # Save embedding
            embedding_path = os.path.join(self.embeddings_dir, f"{name}_embedding.npy")
            np.save(embedding_path, embedding)
            
            # Save reference image
            img_path = os.path.join(self.embeddings_dir, f"{name}_photo.jpg")
            cv2.imwrite(img_path, frame)
            
            # Add to known faces
            self.known_faces[name] = embedding
            
            return True, f"Face saved successfully as '{name}'", embedding_path
            
        except Exception as e:
            return False, f"Error saving face: {str(e)}", None
    
    def recognize_face(self, frame):
        """
        Recognize face in frame
        Returns: (authenticated, user_name, similarity, annotated_frame, bbox)
        """
        if len(self.known_faces) == 0:
            cv2.putText(frame, "No faces registered", (30, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            return False, None, 0.0, frame, None
        
        try:
            # Convert to PIL
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Detect face with bbox
            boxes, probs = self.mtcnn.detect(img)
            
            if boxes is None or len(boxes) == 0:
                cv2.putText(frame, "No face detected", (30, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                self.is_authenticated = False
                self.authenticated_user = None
                return False, None, 0.0, frame, None
            
            # Get face embedding
            face = self.mtcnn(img)
            if face is None:
                return False, None, 0.0, frame, None
            
            with torch.no_grad():
                embedding = self.resnet(face.unsqueeze(0).to(self.device)).detach().cpu().numpy()[0]
            
            # Compare with all known faces
            best_match = None
            best_similarity = 0.0
            
            print(f"[Face Recognition] Comparing against {len(self.known_faces)} known face(s)...")
            for name, known_embedding in self.known_faces.items():
                similarity = np.dot(known_embedding, embedding) / (
                    np.linalg.norm(known_embedding) * np.linalg.norm(embedding)
                )
                print(f"[Face Recognition] {name}: similarity = {similarity:.3f} (threshold: {self.similarity_threshold})")
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = name
            
            # Draw bounding box
            bbox = boxes[0]
            x1, y1, x2, y2 = [int(coord) for coord in bbox]
            
            # Check if authenticated
            if best_similarity > self.similarity_threshold:
                # Authenticated
                color = (0, 255, 0)
                text = f"Welcome {best_match} ({best_similarity:.2f})"
                self.is_authenticated = True
                self.authenticated_user = best_match
                self.current_similarity = best_similarity
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, text, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                return True, best_match, best_similarity, frame, bbox
            else:
                # Not authenticated
                color = (0, 0, 255)
                text = f"Unknown ({best_similarity:.2f})"
                self.is_authenticated = False
                self.authenticated_user = None
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                cv2.putText(frame, text, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                return False, None, best_similarity, frame, bbox
                
        except Exception as e:
            print(f"Error in face recognition: {e}")
            cv2.putText(frame, "Recognition Error", (30, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            return False, None, 0.0, frame, None
    
    def delete_face(self, name):
        """Delete a saved face"""
        if name in self.known_faces:
            # Remove from memory
            del self.known_faces[name]
            
            # Delete files
            embedding_path = os.path.join(self.embeddings_dir, f"{name}_embedding.npy")
            photo_path = os.path.join(self.embeddings_dir, f"{name}_photo.jpg")
            
            if os.path.exists(embedding_path):
                os.remove(embedding_path)
            if os.path.exists(photo_path):
                os.remove(photo_path)
            
            return True, f"Deleted face: {name}"
        else:
            return False, f"Face not found: {name}"
    
    def list_faces(self):
        """List all registered faces"""
        return list(self.known_faces.keys())
    
    def get_status(self):
        """Get current authentication status"""
        return {
            'authenticated': self.is_authenticated,
            'user': self.authenticated_user,
            'similarity': self.current_similarity,
            'threshold': self.similarity_threshold,
            'registered_faces': len(self.known_faces)
        }
