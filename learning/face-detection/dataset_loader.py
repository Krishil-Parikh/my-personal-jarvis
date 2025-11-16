# save as create_embedding.py

import torch
from facenet_pytorch import InceptionResnetV1, MTCNN
from PIL import Image
import numpy as np
import os

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load pretrained model
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=40, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

data_dir = r"captured_frames\1"
embeddings = []

for img_file in os.listdir(data_dir):
    if not img_file.endswith('.jpg'):
        continue
    img_path = os.path.join(data_dir, img_file)
    img = Image.open(img_path).convert('RGB')
    face = mtcnn(img)
    if face is not None:
        embedding = resnet(face.unsqueeze(0).to(device))
        embeddings.append(embedding.detach().cpu().numpy())

if embeddings:
    avg_embedding = np.mean(np.vstack(embeddings), axis=0)
    np.save("krishil_face_embedding.npy", avg_embedding)
    print("✅ Saved face embedding as krishil_face_embedding.npy")
else:
    print("⚠️ No faces detected!")
