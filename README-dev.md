**Developer README**

This document covers developer-focused workflows for the Jarvis project.

**Environment setup (Windows, PowerShell)**
- Create and activate a virtual environment:

```
python -m venv venv
; .\venv\Scripts\Activate.ps1
```

- Install pinned dependencies from `requirements.txt` (created from the active venv in this repo):

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip install -r requirements.txt
```

**Run the application**
- Start Jarvis from the project root with the venv active:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe main.py
```

**Common developer tasks**
- Create `requirements.txt` from current environment:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip freeze > requirements.txt
```

- Run quick Python checks:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -c "import torch, torchvision; print(torch.__version__, torchvision.__version__)"
```

**Debugging tips**
- If you encounter `operator torchvision::nms does not exist`, your `torch`/`torchvision` binaries are mismatched. Use matching wheels from PyTorch's index (see `README.md` for example CPU wheels).
- For f-string issues when building prompts with literal JSON-like braces, escape braces with `{{` and `}}` in f-strings.

**Adding tests**
- There are no unit tests in this repo currently. To add tests:
  - Add a `tests/` folder and write tests using `pytest`.
  - Add `pytest` to `requirements-dev.txt` or `requirements.txt`.
  - Run tests with:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pytest -q
```

**Local development workflow suggestion**
- Use a branch for features and open a PR for merging.
- Keep `requirements.txt` updated when adding/removing packages:

```
C:/Users/krish/OneDrive/Desktop/JARVIS/venv/Scripts/python.exe -m pip freeze > requirements.txt
```

**Notes**
- Project root: `c:\Users\krish\OneDrive\Desktop\JARVIS`
- If you want GPU/CUDA support, install matching `torch`/`torchvision` wheels for your CUDA version.