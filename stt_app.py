#!/usr/bin/env python3
"""
Fully Offline Speech-to-Text Application
Compatible with Windows and Raspberry Pi 5 (Linux)
Uses Vosk for local speech recognition with no internet dependencies
"""

import os
import sys
import time
import json
import argparse
import platform
import subprocess
import wave
from threading import Thread

# Determine the operating system
SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_LINUX = SYSTEM == "Linux"

# Required packages - only locally runnable ones
REQUIRED_PACKAGES = [
    "PyAudio",
    "numpy",
    "sounddevice",
    "vosk"
]

def check_dependencies():
    """Check and install required dependencies."""
    try:
        import pip
        for package in REQUIRED_PACKAGES:
            try:
                __import__(package.lower())
                print(f"✓ {package} is installed")
            except ImportError:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        
        # Install platform-specific dependencies
        if IS_LINUX:
            try:
                import RPi.GPIO
                print("✓ RPi.GPIO is installed")
            except ImportError:
                print("Installing RPi.GPIO...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "RPi.GPIO"])
        
        # Verify Vosk model
        import vosk
        model_path = "model"
        if not os.path.exists(model_path):
            print("Downloading Vosk model for offline recognition...")
            model_name = "vosk-model-small-en-us-0.15"
            model_url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
            
            # Create directory for model
            os.makedirs(model_path, exist_ok=True)
            
            # Download and extract model using Python libraries (no wget/curl dependency)
            import zipfile
            try:
                import urllib.request
                print(f"Downloading {model_name}...")
                zip_path = f"{model_name}.zip"
                urllib.request.urlretrieve(model_url, zip_path)
                
                print("Extracting model...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                
                # Move files to model directory
                import shutil
                for item in os.listdir(model_name):
                    shutil.move(os.path.join(model_name, item), os.path.join(model_path, item))
                
                # Clean up
                os.remove(zip_path)
                os.rmdir(model_name)
                print("Model setup complete")
            except Exception as e:
                print(f"Error downloading model: {e}")
                print("Please download the model manually from https://alphacephei.com/vosk/models")
                print("Download vosk-model-small-en-us-0.15, extract it, and rename it to 'model'")
                if not input("Continue without downloading model? (y/n): ").lower().startswith('y'):
                    sys.exit(1)
            
    except Exception as e:
        print(f"Error setting up dependencies: {e}")
        sys.exit(1)


class VoskSTT:
    """Offline Speech-to-Text using Vosk."""
    
    def __init__(self):
        from vosk import Model, KaldiRecognizer
        import pyaudio
        
        # Set up Vosk model
        model_path = "model"
        if not os.path.exists(model_path):
            model_path = "vosk-model-small-en-us-0.15"
            if not os.path.exists(model_path):
                print("ERROR: Model not found. Please run with --install first")
                sys.exit(1)
            
        self.model = Model(model_path)
        
        # Set up audio stream
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000
        )
        self.stream.start_stream()
        
        # Create recognizer
        self.rec = KaldiRecognizer(self.model, 16000)
    
    def listen(self, timeout=5):
        """Listen to microphone and convert speech to text using Vosk."""
        print("Listening...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            data = self.stream.read(4000, exception_on_overflow=False)
            if len(data) == 0:
                break
                
            if self.rec.AcceptWaveform(data):
                result = json.loads(self.rec.Result())
                if result.get("text", ""):
                    self.cleanup()
                    return result["text"]
        
        # Get final result
        result = json.loads(self.rec.FinalResult())
        text = result.get("text", "No speech detected")
        self.cleanup()
        return text
    
    def cleanup(self):
        """Clean up resources."""
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


class STTApplication:
    """Main application class."""
    
    def __init__(self):
        # Initialize STT engine
        self.engine = VoskSTT()
        
        # Set up LED and button for RPi (if on Linux)
        if IS_LINUX:
            self.setup_rpi_interface()
    
    def setup_rpi_interface(self):
        """Set up Raspberry Pi GPIO interface for button and LED."""
        try:
            import RPi.GPIO as GPIO
            
            # Set up GPIO pins
            self.LED_PIN = 17
            self.BUTTON_PIN = 27
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.LED_PIN, GPIO.OUT)
            GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Set up button callback
            GPIO.add_event_detect(
                self.BUTTON_PIN, 
                GPIO.FALLING, 
                callback=self.button_callback, 
                bouncetime=300
            )
            
            self.button_pressed = False
        except (ImportError, RuntimeError):
            print("GPIO setup failed. Running without hardware interface.")
    
    def button_callback(self, channel):
        """Handle button press event."""
        self.button_pressed = True
        
    def led_on(self):
        """Turn on the LED (for RPi)."""
        if IS_LINUX:
            try:
                import RPi.GPIO as GPIO
                GPIO.output(self.LED_PIN, GPIO.HIGH)
            except (ImportError, RuntimeError, AttributeError):
                pass
    
    def led_off(self):
        """Turn off the LED (for RPi)."""
        if IS_LINUX:
            try:
                import RPi.GPIO as GPIO
                GPIO.output(self.LED_PIN, GPIO.LOW)
            except (ImportError, RuntimeError, AttributeError):
                pass
    
    def run(self):
        """Run the STT application."""
        print("\nFully Offline Speech-to-Text Application")
        print(f"Platform: {SYSTEM}")
        print("Press Ctrl+C to exit\n")
        
        try:
            while True:
                # For RPi with button
                if IS_LINUX and hasattr(self, 'button_pressed'):
                    if self.button_pressed:
                        self.led_on()
                        text = self.engine.listen()
                        print(f"You said: {text}")
                        self.led_off()
                        self.button_pressed = False
                    time.sleep(0.1)
                # For Windows or keyboard input
                else:
                    input("Press Enter to start listening...")
                    self.led_on()
                    text = self.engine.listen()
                    print(f"You said: {text}")
                    self.led_off()
                    
                    # Save to file
                    with open("transcript.txt", "a", encoding="utf-8") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {text}\n")
                
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            # Clean up GPIO (for RPi)
            if IS_LINUX:
                try:
                    import RPi.GPIO as GPIO
                    GPIO.cleanup()
                except (ImportError, RuntimeError):
                    pass


def fetch_model_offline():
    """Provide instructions for offline model acquisition."""
    print("\nTo use this application fully offline, you need the Vosk speech model.")
    print("\nManual Download Instructions:")
    print("1. Visit https://alphacephei.com/vosk/models")
    print("2. Download 'vosk-model-small-en-us-0.15' (or newer equivalent)")
    print("3. Extract the ZIP file")
    print("4. Rename the extracted folder to 'model'")
    print("5. Place the 'model' folder in the same directory as this script\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fully Offline Speech-to-Text Application")
    parser.add_argument("--install", action="store_true", help="Install dependencies and exit")
    parser.add_argument("--model-info", action="store_true", help="Show model download instructions")
    args = parser.parse_args()
    
    if args.model_info:
        fetch_model_offline()
        return
        
    if args.install:
        check_dependencies()
        print("Dependencies installed successfully.")
        return
        
    # Check if model exists
    if not os.path.exists("model") and not os.path.exists("vosk-model-small-en-us-0.15"):
        print("Speech recognition model not found.")
        print("Run with --install to download, or --model-info for manual instructions.")
        return
        
    # Check dependencies before running
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package.lower())
        except ImportError:
            print(f"Required package {package} not found. Run with --install first.")
            return
    
    # Run the application
    app = STTApplication()
    app.run()


if __name__ == "__main__":
    main()