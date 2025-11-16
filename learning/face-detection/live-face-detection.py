# save as recognize_face.py

import cv2
import torch
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load models
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=40, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Load your saved embedding
known_embedding = np.load("krishil_face_embedding.npy")

# Threshold for similarity (tune between 0.6–0.8)
SIMILARITY_THRESHOLD = 0.75

cap = cv2.VideoCapture(0)
while True:
    ret, frame = cap.read()
    if not ret:
        break

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    face = mtcnn(img)

    if face is not None:
        embedding = resnet(face.unsqueeze(0).to(device)).detach().cpu().numpy()[0]
        sim = np.dot(known_embedding, embedding) / (
            np.linalg.norm(known_embedding) * np.linalg.norm(embedding)
        )

        if sim > SIMILARITY_THRESHOLD:
            text = f"Access Granted ({sim:.2f})"
            color = (0, 255, 0)
        else:
            text = f"Unknown ({sim:.2f})"
            color = (0, 0, 255)

        cv2.putText(frame, text, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.imshow("Face Recognition", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
