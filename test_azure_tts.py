# Test Azure TTS Directly
# Run this to diagnose speaking issues

import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

print("\n" + "="*70)
print("TESTING AZURE TEXT-TO-SPEECH")
print("="*70 + "\n")

# Load environment
load_dotenv()

speech_key = os.getenv("AZURE_SPEECH_KEY")
speech_region = os.getenv("AZURE_SPEECH_REGION")
voice_name = os.getenv("AZURE_SPEECH_VOICE", "en-US-GuyNeural")

print(f"1. Checking credentials...")
print(f"   API Key: {'✅ Set' if speech_key else '❌ Missing'}")
print(f"   Region: {speech_region if speech_region else '❌ Missing'}")
print(f"   Voice: {voice_name}")

if not speech_key or not speech_region:
    print("\n❌ ERROR: Azure credentials not configured!")
    print("   Please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env file\n")
    exit(1)

print("\n2. Testing speech synthesis...")

try:
    # Create config
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=speech_region
    )
    speech_config.speech_synthesis_voice_name = voice_name
    
    # Set output format
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    
    # Create synthesizer
    audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )
    
    # Test text
    test_text = "Hello! This is a test of the Azure Text to Speech system. Can you hear me?"
    
    print(f"   Speaking: '{test_text}'")
    print(f"   Please wait...\n")
    
    # Synthesize
    result = synthesizer.speak_text_async(test_text).get()
    
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("✅ SUCCESS! Speech synthesis working correctly!")
        print("   If you heard the audio, Azure TTS is configured properly.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = result.cancellation_details
        print(f"❌ FAILED! Speech synthesis was cancelled.")
        print(f"   Reason: {cancellation.reason}")
        print(f"   Error: {cancellation.error_details}")
        print(f"   Error code: {cancellation.error_code}")
        
        if "401" in str(cancellation.error_details):
            print("\n   💡 This looks like an authentication error.")
            print("      Please verify your AZURE_SPEECH_KEY is correct.")
        elif "region" in str(cancellation.error_details).lower():
            print("\n   💡 This looks like a region error.")
            print("      Please verify your AZURE_SPEECH_REGION is correct.")
    else:
        print(f"❌ Unexpected result: {result.reason}")

except Exception as e:
    print(f"❌ EXCEPTION: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70 + "\n")
