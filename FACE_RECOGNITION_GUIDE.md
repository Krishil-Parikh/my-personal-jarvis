# Face Recognition & Authentication System

## Overview

The integrated face recognition system allows Jarvis to:
- **Save faces** for identification
- **Authenticate users** via camera
- **Recognize registered users** automatically
- **Manage multiple user profiles**

## Voice Commands

### Camera Control

| Command | Action |
|---------|--------|
| "Look at camera" / "Open camera" | Opens camera feed |
| "Stop camera" / "Close camera" | Closes camera |

### Face Registration

| Command | Action |
|---------|--------|
| "Save this face" / "Register face" | Saves your face with a name |

**Example conversation:**
```
You: "Hey Jarvis, look at the camera"
Jarvis: "Okay, showing camera feed. Say 'save this face' to register, or 'stop camera' to close."

You: "Save this face"
Jarvis: "What name should I save this face under?"

You: "John"
Jarvis: "Saving face as John. Please position your face clearly in the center and stay still."
[3 second countdown]
Jarvis: "Face saved successfully! Welcome, John!"
```

### Authentication

| Command | Action |
|---------|--------|
| "Authenticate" / "Verify me" / "Login" | Authenticate using face |

### Face Management

| Command | Action |
|---------|--------|
| "List faces" / "Who do you know" | Lists all registered faces |

## Face Registration Requirements

For successful face registration, ensure:

✅ **Face Visibility**
- Face must be clearly visible
- No obstructions (sunglasses, masks, etc.)
- Good lighting conditions

✅ **Face Position**
- Face centered in frame
- Face takes up at least 30% of frame width
- Move closer if face is too small

✅ **Face Quality**
- Detection confidence > 95%
- Only one person in frame
- Face looking at camera

✅ **Environment**
- Good lighting (not too dark/bright)
- Stable position (don't move)
- Clear background

## Real-time Feedback

During registration, you'll see:

| Status | Color | Meaning |
|--------|-------|---------|
| "Perfect! Face is clear and centered" | 🟢 Green | Ready to save |
| "Face too small - move closer" | 🟠 Orange | Adjustment needed |
| "Face not centered" | 🟠 Orange | Reposition |
| "Multiple faces detected" | 🟠 Orange | Ensure only one person |
| "No face detected" | 🟡 Yellow | Position face in view |

## Authentication Process

1. Say: "Authenticate" or "Verify me"
2. Look at camera
3. System compares your face with registered faces
4. If match > 65% similarity → ✅ Authenticated
5. If match < 65% similarity → ❌ Not recognized

**Authenticated:**
```
🟢 Green box around face
"Welcome [Name] (0.85)"
```

**Not Recognized:**
```
🔴 Red box around face
"Unknown (0.42)"
```

## Technical Details

### Face Recognition Pipeline

1. **Face Detection** (MTCNN)
   - Detects faces in frame
   - Returns bounding box and confidence
   - Minimum confidence: 95%

2. **Face Alignment** (MTCNN)
   - Aligns face to standard pose
   - Extracts 160x160 face image

3. **Feature Extraction** (InceptionResnetV1)
   - Generates 512-dimensional embedding
   - Pre-trained on VGGFace2 dataset

4. **Face Matching** (Cosine Similarity)
   - Compares embeddings
   - Threshold: 0.65 (65%)
   - Returns best match if above threshold

### Storage

Faces are stored in `face_embeddings/` directory:

```
face_embeddings/
  ├── john_embedding.npy    # 512-dim embedding
  ├── john_photo.jpg        # Reference photo
  ├── alice_embedding.npy
  ├── alice_photo.jpg
  └── ...
```

### Security Considerations

⚠️ **Important:**
- Embeddings are stored locally (not encrypted)
- For production, add encryption
- Consider liveness detection for anti-spoofing
- Current system can be fooled by photos

### Performance

| Operation | Time |
|-----------|------|
| Face Detection | ~50ms |
| Feature Extraction | ~100ms |
| Face Matching | ~10ms |
| **Total Recognition** | **~160ms** |

**Frame Rate:** ~6 FPS (real-time capable)

### Hardware Requirements

**Minimum:**
- Webcam (720p recommended)
- CPU: Intel i5 or equivalent
- RAM: 4GB

**Recommended:**
- Webcam: 1080p
- GPU: NVIDIA (CUDA support)
- RAM: 8GB

**With GPU:**
- 10x faster processing
- Real-time at 30+ FPS

## Troubleshooting

### "No face detected"

**Solutions:**
- Improve lighting
- Move closer to camera
- Remove obstructions
- Clean camera lens
- Check camera is working

### "Face confidence too low"

**Solutions:**
- Better lighting
- Look directly at camera
- Remove partial obstructions
- Ensure face is clearly visible

### "Multiple faces detected"

**Solutions:**
- Ensure only one person in frame
- Move others out of view
- Use plain background

### "Face too small"

**Solutions:**
- Move closer to camera
- Use higher resolution camera
- Adjust camera angle

### "Authentication fails"

**Possible reasons:**
- Different lighting conditions
- Different angle/pose
- Facial changes (beard, glasses)
- Low quality camera

**Solutions:**
- Re-register under current conditions
- Register multiple poses
- Improve lighting
- Lower threshold (in code)

## Advanced Configuration

Edit `backend/enhanced_face_recognition.py`:

```python
class EnhancedFaceRecognizer:
    def __init__(self, embeddings_dir="face_embeddings"):
        # Recognition threshold (0.0 - 1.0)
        self.similarity_threshold = 0.65  # Lower = more lenient
        
        # Quality threshold for saving
        self.quality_threshold = 0.8
```

**Threshold Guidelines:**
- **0.50-0.60:** Very lenient (more false positives)
- **0.60-0.70:** Balanced (recommended)
- **0.70-0.80:** Strict (fewer false positives)
- **0.80+:** Very strict (may miss valid matches)

## Integration Example

```python
from backend.voice_assistant import LocalAssistant

assistant = LocalAssistant()

# Test face recognition
assistant.speak("Please authenticate")
success, user = assistant.authenticate_user()

if success:
    print(f"Welcome, {user}!")
    # Grant access to system
else:
    print("Access denied")
    # Deny access
```

## Future Enhancements

Planned features:
- [ ] Liveness detection (anti-spoofing)
- [ ] Multiple face poses per user
- [ ] Age/emotion recognition
- [ ] Encrypted embedding storage
- [ ] Cloud backup of faces
- [ ] Face recognition in photos
- [ ] Automatic login on recognition

## Privacy & Ethics

**Data Collection:**
- Faces stored locally only
- No cloud upload (by default)
- User must explicitly register

**User Rights:**
- Delete your face anytime
- Export your data
- Opt-out of recognition

**Best Practices:**
- Get consent before saving faces
- Inform users when camera is active
- Provide opt-out mechanisms
- Secure embedding storage
- Regular data audits

## Support

For issues:
1. Check camera is working: `python backend/camera.py`
2. Test face detection: Check learning/face-detection/
3. Verify models installed: facenet-pytorch, torch
4. Check logs for errors
5. Ensure good lighting conditions

## Credits

**Models:**
- MTCNN: Face detection
- InceptionResnetV1: Feature extraction
- VGGFace2: Pre-trained weights

**Libraries:**
- facenet-pytorch
- OpenCV
- PyTorch
