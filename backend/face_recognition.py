import cv2
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import os

class FaceRecognizer:
    def __init__(self, embedding_path="learning/face-detection/krishil_face_embedding.npy"):
        """Initialize face recognition with saved embedding"""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load models
        print("Loading face recognition models...")
        self.mtcnn = MTCNN(image_size=160, margin=0, min_face_size=40, device=self.device)
        self.resnet = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        
        # Load known embedding
        self.embedding_path = embedding_path
        if os.path.exists(embedding_path):
            self.known_embedding = np.load(embedding_path)
            print(f"Loaded embedding from {embedding_path}")
        else:
            self.known_embedding = None
            print(f"Warning: Embedding file not found at {embedding_path}")
        
        # Threshold for similarity (tune between 0.6–0.8)
        self.similarity_threshold = 0.75
        
        self.is_authenticated = False
        self.current_similarity = 0.0
    
    def recognize_face(self, frame):
        """
        Process a frame and return recognition result
        
        Returns:
            tuple: (authenticated, similarity, annotated_frame)
        """
        if self.known_embedding is None:
            # No embedding loaded, just return the frame
            cv2.putText(frame, "No embedding loaded", (30, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return False, 0.0, frame
        
        try:
            # Convert to PIL Image
            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Detect face
            face = self.mtcnn(img)
            
            if face is not None:
                # Get embedding
                embedding = self.resnet(face.unsqueeze(0).to(self.device)).detach().cpu().numpy()[0]
                
                # Calculate similarity (cosine similarity)
                similarity = np.dot(self.known_embedding, embedding) / (
                    np.linalg.norm(self.known_embedding) * np.linalg.norm(embedding)
                )
                
                self.current_similarity = similarity
                
                if similarity > self.similarity_threshold:
                    text = f"Access Granted ({similarity:.2f})"
                    color = (0, 255, 0)
                    self.is_authenticated = True
                else:
                    text = f"Unknown ({similarity:.2f})"
                    color = (0, 0, 255)
                    self.is_authenticated = False
                
                cv2.putText(frame, text, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                return self.is_authenticated, similarity, frame
            else:
                # No face detected
                cv2.putText(frame, "No face detected", (30, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                self.is_authenticated = False
                return False, 0.0, frame
                
        except Exception as e:
            print(f"Error in face recognition: {e}")
            cv2.putText(frame, "Recognition Error", (30, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            return False, 0.0, frame
    
    def set_threshold(self, threshold):
        """Update similarity threshold"""
        self.similarity_threshold = threshold
    
    def get_status(self):
        """Get current authentication status"""
        return {
            'authenticated': self.is_authenticated,
            'similarity': self.current_similarity,
            'threshold': self.similarity_threshold
        }
