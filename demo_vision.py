"""
Demo: Vision Language Model (VLM) Camera Analysis

This demonstrates how Jarvis can analyze what's on the camera
and answer questions about it using GPT-4 Vision.
"""

import sys
import os
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ai_assistant import AIAssistant
from backend.camera import CameraCapture
import time

def demo_camera_analysis():
    """Demo VLM analysis of camera feed"""
    
    print("\n" + "="*70)
    print("VISION LANGUAGE MODEL - CAMERA ANALYSIS DEMO")
    print("="*70)
    
    # Initialize components
    print("\n🔄 Initializing camera...")
    camera = CameraCapture(camera_id=0)
    camera.start()
    time.sleep(1)
    
    print("🔄 Initializing AI assistant with vision...")
    ai = AIAssistant()
    
    print("\n✅ Ready!")
    print("\nInstructions:")
    print("1. Position something in front of the camera")
    print("2. Press SPACE to capture and analyze")
    print("3. Type your question (or press Enter for default)")
    print("4. Press ESC to exit\n")
    
    cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
            
            # Show live feed
            display_frame = frame.copy()
            cv2.putText(display_frame, "Press SPACE to analyze, ESC to exit", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow("Camera", display_frame)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == 27:  # ESC
                print("\n👋 Exiting...")
                break
            
            elif key == 32:  # SPACE
                print("\n" + "="*70)
                print("📸 CAPTURING IMAGE")
                print("="*70)
                
                # Capture frame
                captured_frame = camera.get_frame()
                
                # Save for reference
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshots/demo_capture_{timestamp}.jpg"
                os.makedirs("screenshots", exist_ok=True)
                cv2.imwrite(screenshot_path, captured_frame)
                print(f"✅ Saved: {screenshot_path}")
                
                # Get user's question
                print("\n💬 What would you like to know about this image?")
                print("   (Press Enter for: 'What do you see in this image?')")
                user_query = input("   Your question: ").strip()
                
                if not user_query:
                    user_query = "What do you see in this image? Describe it in detail."
                
                print(f"\n🤔 Analyzing: '{user_query}'")
                print("⏳ Please wait...")
                
                # Analyze with VLM
                analysis = ai.analyze_camera_feed(captured_frame, user_query)
                
                print("\n" + "="*70)
                print("🤖 JARVIS ANALYSIS:")
                print("="*70)
                print(analysis)
                print("="*70)
                
                print("\n✅ Analysis complete!")
                print("   Position something else and press SPACE again,")
                print("   or press ESC to exit.\n")
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    
    finally:
        cv2.destroyAllWindows()
        camera.stop()
        print("\n✅ Camera stopped")

def demo_image_analysis():
    """Demo VLM analysis of static images"""
    
    print("\n" + "="*70)
    print("VISION LANGUAGE MODEL - IMAGE ANALYSIS DEMO")
    print("="*70)
    
    ai = AIAssistant()
    
    # Test with a sample image (if available)
    test_images = [
        "screenshots/",
        "images/",
        "face_embeddings/"
    ]
    
    print("\n📁 Looking for images to analyze...")
    
    found_images = []
    for directory in test_images:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    found_images.append(os.path.join(directory, file))
    
    if not found_images:
        print("❌ No images found. Please run camera demo first.")
        return
    
    print(f"✅ Found {len(found_images)} image(s)")
    
    for i, image_path in enumerate(found_images[:3], 1):  # Limit to 3
        print(f"\n{'='*70}")
        print(f"IMAGE {i}: {image_path}")
        print('='*70)
        
        # Analyze
        print("🤔 Analyzing...")
        analysis = ai.analyze_image(image_path, "Describe this image in detail.")
        
        print("\n🤖 Analysis:")
        print(analysis)
        print('='*70)
        
        if i < len(found_images[:3]):
            input("\nPress Enter to analyze next image...")

def main():
    """Main demo selector"""
    
    print("\n" + "#"*70)
    print("# VISION LANGUAGE MODEL (VLM) - DEMO")
    print("#"*70)
    
    print("\nSelect demo:")
    print("1. Camera Analysis (Live)")
    print("2. Image Analysis (Static files)")
    print("3. Exit")
    
    try:
        choice = input("\nYour choice (1-3): ").strip()
        
        if choice == "1":
            demo_camera_analysis()
        elif choice == "2":
            demo_image_analysis()
        elif choice == "3":
            print("Goodbye!")
        else:
            print("Invalid choice")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
