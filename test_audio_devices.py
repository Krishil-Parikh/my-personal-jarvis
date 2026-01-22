# Audio Device Diagnostic Test
# This will help identify why Azure TTS synthesis succeeds but no audio plays

import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

print("\n" + "="*70)
print("AUDIO DEVICE DIAGNOSTICS")
print("="*70 + "\n")

# Load environment
load_dotenv()

speech_key = os.getenv("AZURE_SPEECH_KEY")
speech_region = os.getenv("AZURE_SPEECH_REGION")
voice_name = os.getenv("AZURE_SPEECH_VOICE", "en-US-GuyNeural")

print("TEST 1: Save audio to file (bypass audio device)")
print("-" * 70)

try:
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=speech_region
    )
    speech_config.speech_synthesis_voice_name = voice_name
    
    # Save to WAV file instead of speakers
    audio_filename = "test_output.wav"
    audio_config = speechsdk.audio.AudioOutputConfig(filename=audio_filename)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    test_text = "This audio is being saved to a WAV file."
    print(f"   Synthesizing: '{test_text}'")
    result = synthesizer.speak_text_async(test_text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print(f"   ✅ Audio saved to: {audio_filename}")
        print(f"   Please play this file manually to verify synthesis works!\n")
        
        # Check file size
        if os.path.exists(audio_filename):
            size = os.path.getsize(audio_filename)
            print(f"   File size: {size:,} bytes")
            if size > 1000:
                print("   ✅ File contains audio data\n")
            else:
                print("   ❌ File is too small - may be empty\n")
    else:
        print(f"   ❌ Failed: {result.reason}\n")

except Exception as e:
    print(f"   ❌ Exception: {e}\n")


print("\nTEST 2: Check Windows audio devices")
print("-" * 70)

try:
    import sounddevice as sd
    
    devices = sd.query_devices()
    default_output = sd.default.device[1]
    
    print(f"   Default output device: #{default_output}\n")
    print("   Available output devices:\n")
    
    for i, device in enumerate(devices):
        if device['max_output_channels'] > 0:  # Output device
            is_default = " [DEFAULT]" if i == default_output else ""
            print(f"   [{i}] {device['name']}{is_default}")
            print(f"       Channels: {device['max_output_channels']}")
            print(f"       Sample rate: {device['default_samplerate']} Hz\n")
    
except ImportError:
    print("   ⚠️  sounddevice not installed")
    print("   Run: pip install sounddevice\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")


print("\nTEST 3: Play a simple beep (test audio output)")
print("-" * 70)

try:
    import winsound
    print("   Playing system beep...")
    winsound.Beep(1000, 500)  # 1000 Hz for 500ms
    print("   ✅ Did you hear a beep?\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")


print("\nTEST 4: Try Azure TTS with NULL audio device (test SDK only)")
print("-" * 70)

try:
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=speech_region
    )
    speech_config.speech_synthesis_voice_name = voice_name
    
    # No audio output
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    result = synthesizer.speak_text_async("Testing without audio output").get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("   ✅ Azure SDK synthesis works (without audio output)\n")
    else:
        print(f"   ❌ Failed: {result.reason}\n")

except Exception as e:
    print(f"   ❌ Exception: {e}\n")


print("="*70)
print("DIAGNOSTIC SUMMARY")
print("="*70)
print("""
If TEST 1 created a WAV file that plays correctly:
  ➡️  Synthesis works, but audio routing is broken

If you heard the beep in TEST 3:
  ➡️  Your speakers work, but Azure SDK can't reach them

SOLUTIONS TO TRY:
1. Check Windows Sound Settings:
   - Right-click speaker icon in taskbar
   - Click 'Open Sound settings'
   - Verify correct output device is selected
   - Check volume levels (both system and app-specific)

2. Restart Windows Audio Service:
   - Open Services (Win + R, type 'services.msc')
   - Find 'Windows Audio'
   - Right-click → Restart

3. Use file output instead:
   - Modify voice_assistant.py to save audio files
   - Play files with pygame or playsound library

4. Try different audio device:
   - Install sounddevice: pip install sounddevice
   - Run this test again to see available devices
""")
print("="*70 + "\n")
