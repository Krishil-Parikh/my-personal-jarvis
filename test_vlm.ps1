# Quick Test - VLM Camera Analysis
# Run this after: .venv\Scripts\activate

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "   TESTING VLM CAMERA ANALYSIS (Qwen 2.5 VL)" -ForegroundColor Cyan
Write-Host "================================================`n" -ForegroundColor Cyan

Write-Host "1️⃣  Testing AI Assistant with Vision..." -ForegroundColor Yellow
python -c "from backend.ai_assistant import AIAssistant; ai = AIAssistant(); print('✅ Vision Model:', ai.vision_model, '(FREE)')"

Write-Host "`n2️⃣  Testing Voice Assistant VLM Integration..." -ForegroundColor Yellow
python -c "from backend.voice_assistant import LocalAssistant; print('✅ Voice Assistant with VLM ready!')"

Write-Host "`n3️⃣  Testing Camera..." -ForegroundColor Yellow
python -c "from backend.camera import CameraCapture; cam = CameraCapture(); cam.start(); import time; time.sleep(1); print('✅ Camera OK') if cam.is_opened() else print('❌ Camera FAIL'); cam.stop()"

Write-Host "`n================================================" -ForegroundColor Green
Write-Host "   ALL TESTS COMPLETE!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green

Write-Host "`n📋 NEW VOICE COMMANDS:" -ForegroundColor Cyan
Write-Host "   • 'Look at camera'        → Opens camera" -ForegroundColor White
Write-Host "   • 'Tell me about this'    → Analyzes camera view with VLM" -ForegroundColor White
Write-Host "   • 'What do you see?'      → Describes what's on camera" -ForegroundColor White
Write-Host "   • 'Describe this'         → Analyzes current view" -ForegroundColor White
Write-Host "   • 'Stop camera'           → Closes camera`n" -ForegroundColor White

Write-Host "🎮 RUN DEMOS:" -ForegroundColor Cyan
Write-Host "   python demo_vision.py     → VLM camera demo" -ForegroundColor White
Write-Host "   python frontend\02.py     → Full Jarvis system`n" -ForegroundColor White
