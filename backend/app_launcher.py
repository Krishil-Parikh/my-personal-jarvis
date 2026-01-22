import pyautogui
import time
import re

def open_application(app_name):
    """
    Opens an application using Windows search
    
    Args:
        app_name: Name of the application to open
    """
    try:
        print(f"Opening application: {app_name}")
        
        # Press Windows key
        pyautogui.press('win')
        time.sleep(0.5)
        
        # Type the application name
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.5)
        
        # Press Enter
        pyautogui.press('enter')
        
        return True
    except Exception as e:
        print(f"Error opening application: {e}")
        return False

def extract_app_name(command):
    """
    Extract application name from voice command
    Removes words like 'jarvis', 'open', 'launch', 'start', etc.
    
    Args:
        command: Voice command string
    
    Returns:
        Cleaned application name
    """
    # Words to remove
    remove_words = [
        'jarvis', 'hey jarvis', 'ok jarvis',
        'open', 'launch', 'start', 'run',
        'please', 'can you', 'could you',
        'the', 'app', 'application', 'program'
    ]
    
    # Convert to lowercase
    command = command.lower().strip()
    
    # Remove punctuation at the end
    command = command.rstrip('.,!?')
    
    # Remove specified words
    for word in remove_words:
        command = re.sub(r'\b' + re.escape(word) + r'\b', '', command, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    app_name = ' '.join(command.split()).strip()
    
    return app_name
