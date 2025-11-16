**Project**

- **Name**: Jarvis — local personal assistant / interaction hub.
- **Root script**: `main.py` — entrypoint that starts the assistant.

**What it contains**
- **Core modules**: `basic_interaction.py`, `macro_manager.py`.
- **Agents**: `agents/` (placeholder for agent implementations).
- **Learning assets**: `learning/` (face landmark detection example and captured frames).

**Quick Start**
- **Prerequisites**: Python 3.11, Windows. A virtual environment is strongly recommended.
- **Create & activate venv (PowerShell)**:

```
python -m venv venv
; .\venv\Scripts\Activate.ps1
```

- **Upgrade pip (optional but recommended)**:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip install --upgrade pip
```

- **Install runtime dependencies**: There's no single `requirements.txt` in the repo by default. Install the main dependencies used by the project (CPU wheels shown below). If you have CUDA, pick matching CUDA wheels from the PyTorch index instead.

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip install \
  --index-url https://download.pytorch.org/whl/cpu \
  torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 \
  facenet-pytorch mediapipe opencv-python pillow numpy
```

**Run Jarvis**
- From the project root, with the venv activated:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe main.py
```

**Files of interest**
- `main.py`: program entrypoint and orchestration.
- `basic_interaction.py`: LLM interaction, triple extraction helpers, and related logic.
- `macro_manager.py`: macro handling.
- `learning/face_landmark_detection.py`: example face-landmark/landmarker assets.

**Troubleshooting**
- RuntimeError: "operator torchvision::nms does not exist"
  - Cause: torch and torchvision binary mismatch (common after pip upgrades). torchvision expects operator implementations present in the installed `torch` binary.
  - Fix (CPU example):

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu \
  torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 -U
```

  - If you use CUDA, replace the `+cpu` wheels with the appropriate `+cuXXX` versions from https://download.pytorch.org/whl/ (match `torch` and `torchvision` exactly).

- f-string error with curly braces in `basic_interaction.py` when building prompts
  - Symptom: `ValueError: Invalid format specifier ... for object of type 'str'` when building a prompt containing JSON-like `{}`.
  - Fix: Escape literal braces in f-strings by doubling them (`{{` / `}}`) or use a regular string for the JSON example. This repo already uses the escaped form.

**Development notes**
- Use `venv` activation before running or installing packages to avoid system-wide change.
- If you add heavy ML models, prefer to pin versions in a `requirements.txt` or `pyproject.toml` for reproducible installs.

**Extending the project**
- Add a `requirements.txt` by running:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip freeze > requirements.txt
```

- Consider adding setup scripts or a `README-dev.md` with developer workflows, tests, and style guidelines.

**Contact / Authors**
- Project workspace: `c:\Users\krish\OneDrive\Desktop\JARVIS`

**License**
- None specified. Add a `LICENSE` file if you want to open-source or clarify usage.
