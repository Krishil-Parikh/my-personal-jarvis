import os
import cv2
import numpy as np
import pandas as pd
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ---------------------- FUNCTIONS ----------------------

def draw_landmarks_on_image(rgb_image, detection_result):
    annotated_image = np.copy(rgb_image)
    for face_landmarks in detection_result.face_landmarks:
        face_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
        face_landmarks_proto.landmark.extend([
            landmark_pb2.NormalizedLandmark(x=lm.x, y=lm.y, z=lm.z)
            for lm in face_landmarks
        ])
        mp.solutions.drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=face_landmarks_proto,
            connections=mp.solutions.face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp.solutions.drawing_styles
            .get_default_face_mesh_tesselation_style()
        )
    return annotated_image

def landmarks_to_flat_list(landmarks):
    """Flatten landmarks to x1,y1,z1,... for however many landmarks exist"""
    flat_list = []
    for lm in landmarks:
        flat_list.extend([lm.x, lm.y, lm.z])
    return flat_list

def crop_face_from_landmarks(frame, landmarks, padding=10):
    h, w, _ = frame.shape
    xs = [int(lm.x * w) for lm in landmarks]
    ys = [int(lm.y * h) for lm in landmarks]
    x_min, x_max = max(min(xs)-padding, 0), min(max(xs)+padding, w)
    y_min, y_max = max(min(ys)-padding, 0), min(max(ys)+padding, h)
    return frame[y_min:y_max, x_min:x_max]

# ---------------------- SETUP ----------------------

cap = cv2.VideoCapture(0)
name = input("Enter the ID of the person: ")
os.makedirs(f"captured_frames/{name}", exist_ok=True)

# CSV setup: create empty DataFrame (columns added dynamically)
csv_file = f"captured_frames/{name}/landmarks.csv"
df = pd.DataFrame()

# MediaPipe FaceLandmarker setup
base_options = python.BaseOptions(
    model_asset_path='face_landmarker_v2_with_blendshapes.task'
)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True,
    num_faces=1
)
detector = vision.FaceLandmarker.create_from_options(options)

frame_count = 0

# ---------------------- MAIN LOOP ----------------------

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    detection_result = detector.detect(image)

    if detection_result.face_landmarks:
        landmarks = detection_result.face_landmarks[0]
        flat_landmarks = landmarks_to_flat_list(landmarks)

        # Create column names dynamically if first frame
        if df.empty:
            num_landmarks = len(landmarks)
            columns = [f"{axis}{i}" for i in range(num_landmarks) for axis in "xyz"]
            df = pd.DataFrame(columns=columns)

        # Save row
        df.loc[frame_count] = flat_landmarks

        # Crop face and save image
        cropped_face = crop_face_from_landmarks(frame, landmarks)
        filename = f"captured_frames/{name}/frame_{frame_count:05d}.jpg"
        cv2.imwrite(filename, cropped_face)

        # Optional: draw landmarks
        annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)
        cv2.imshow("Face Capture", cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

        print(f"Saved frame {frame_count} with {len(landmarks)} landmarks")

    frame_count += 1
    if frame_count == 1000 or cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ---------------------- CLEANUP ----------------------

df.to_csv(csv_file, index=False)
print(f"All landmarks saved to {csv_file}")

cap.release()
cv2.destroyAllWindows()
