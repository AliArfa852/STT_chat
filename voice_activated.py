#!/usr/bin/env python3
"""
Fully Offline Speech-to-Text Application with Keyword Activation
Compatible with Windows and Raspberry Pi 5 (Linux)
Designed to run continuously in the background
"""

import os
import sys
import time
import json
import queue
import argparse
import platform
import subprocess
import wave
import threading
import array
import logging
import signal
import atexit
from collections import deque
from datetime import datetime

# Determine the operating system
SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_LINUX = SYSTEM == "Linux"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stt_service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("STT-Service")

# Required packages - only locally runnable ones
REQUIRED_PACKAGES = [
    "PyAudio",
    "numpy",
    "sounddevice",
    "vosk",
    "webrtcvad"  # For voice activity detection
]

if IS_WINDOWS:
    # Windows service dependencies
    REQUIRED_PACKAGES.append("pywin32")
    REQUIRED_PACKAGES.append("pystray")
elif IS_LINUX:
    # Linux service dependencies
    REQUIRED_PACKAGES.append("python-daemon")

def check_dependencies():
    """Check and install required dependencies."""
    try:
        import pip
        for package in REQUIRED_PACKAGES:
            try:
                if package == 'python-daemon' and IS_LINUX:
                    module_name = 'daemon'
                else:
                    module_name = package.lower().replace('-', '_')
                
                __import__(module_name)
                logger.info(f"INSTALLED: {package}")
            except ImportError:
                logger.info(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        
        # Install platform-specific dependencies
        if IS_LINUX:
            try:
                import RPi.GPIO
                logger.info("INSTALLED: RPi.GPIO")
            except ImportError:
                logger.info("Installing RPi.GPIO...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "RPi.GPIO"])
        
        # Verify Vosk model
        model_path = "model"
        if not os.path.exists(model_path):
            logger.info("Downloading Vosk model for offline recognition...")
            model_name = "vosk-model-small-en-us-0.15"
            model_url = f"https://alphacephei.com/vosk/models/{model_name}.zip"
            
            # Create directory for model
            os.makedirs(model_path, exist_ok=True)
            
            # Download and extract model using Python libraries (no wget/curl dependency)
            import zipfile
            try:
                import urllib.request
                logger.info(f"Downloading {model_name}...")
                zip_path = f"{model_name}.zip"
                urllib.request.urlretrieve(model_url, zip_path)
                
                logger.info("Extracting model...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(".")
                
                # Move files to model directory
                import shutil
                for item in os.listdir(model_name):
                    shutil.move(os.path.join(model_name, item), os.path.join(model_path, item))
                
                # Clean up
                os.remove(zip_path)
                os.rmdir(model_name)
                logger.info("Model setup complete")
            except Exception as e:
                logger.error(f"Error downloading model: {e}")
                logger.info("Please download the model manually from https://alphacephei.com/vosk/models")
                logger.info("Download vosk-model-small-en-us-0.15, extract it, and rename it to 'model'")
                if not input("Continue without downloading model? (y/n): ").lower().startswith('y'):
                    sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error setting up dependencies: {e}")
        sys.exit(1)


class SimpleKeywordDetector:
    """
    Simplified keyword detection class that uses the same approach as the working test script.
    Eliminates the use of VAD for more reliable detection.
    """
    
    def __init__(self, keywords=None, sensitivity=0.5):
        from vosk import Model, KaldiRecognizer
        import pyaudio
        
        # Set default keywords if none provided
        self.keywords = keywords or ["hey computer", "wake up", "listen", "start"]
        self.sensitivity = sensitivity
        
        # Set up Vosk model
        model_path = "model"
        if not os.path.exists(model_path):
            model_path = "vosk-model-small-en-us-0.15"
            if not os.path.exists(model_path):
                logger.error("ERROR: Model not found. Please run with --install first")
                sys.exit(1)
            
        self.model = Model(model_path)
        
        # Set up audio - using the same configuration as the working test
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000  # Same as working test
        )
        
        # Create recognizer - no grammar restrictions
        self.recognizer = KaldiRecognizer(self.model, 16000)
        
        # Running status
        self.running = False
        self.detected_callback = None
        self.thread = None
    
    def listen_for_keyword(self, callback=None):
        """Start listening for keywords in the background."""
        self.detected_callback = callback
        self.running = True
        
        # Start listening thread
        self.thread = threading.Thread(target=self._listen_worker, daemon=True)
        self.thread.start()
        
        logger.info(f"Listening for keywords: {', '.join(self.keywords)}")
    
    def _listen_worker(self):
        """Background worker thread for keyword detection"""
        last_detection_time = 0
        cooldown_period = 3  # seconds between detections
        
        self.stream.start_stream()
        
        while self.running:
            try:
                # Read audio (same approach as the working test)
                data = self.stream.read(4000, exception_on_overflow=False)
                
                if len(data) == 0:
                    continue
                
                # Process audio with recognizer
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower()
                    
                    # If there's recognized text, log it
                    if text:
                        logger.info(f"Heard: '{text}'")
                        
                        # Check if any keyword was detected
                        current_time = time.time()
                        if current_time - last_detection_time > cooldown_period:
                            for keyword in self.keywords:
                                if keyword in text:
                                    logger.info(f"Keyword detected: '{keyword}' in '{text}'")
                                    last_detection_time = current_time
                                    
                                    if self.detected_callback:
                                        self.detected_callback()
                                    break
            
            except Exception as e:
                logger.error(f"Error in keyword detection: {e}")
                time.sleep(0.5)  # Prevent tight loop on error
    
    def stop(self):
        """Stop keyword detection"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=1)
            
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
        except Exception as e:
            logger.error(f"Error stopping keyword detector: {e}")


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
                logger.error("ERROR: Model not found. Please run with --install first")
                sys.exit(1)
            
        self.model = Model(model_path)
        
        # Set up audio stream - using the same configuration as the working test
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
        logger.info("Listening...")
        
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
        try:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
        except Exception as e:
            logger.error(f"Error cleaning up STT resources: {e}")


class STTService:
    """Main service class that runs in background."""
    
    def __init__(self, keywords=None, output_dir=None):
        # Set output directory
        self.output_dir = output_dir or os.path.expanduser("~/stt_transcripts")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize keyword detector - using the new SimpleKeywordDetector
        self.keyword_detector = SimpleKeywordDetector(keywords=keywords)
        
        # Set up LED for RPi (if on Linux)
        if IS_LINUX:
            self.setup_rpi_interface()
            
        # Variables for service state
        self.running = False
        self.paused = False
        
        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def setup_rpi_interface(self):
        """Set up Raspberry Pi GPIO interface for LED."""
        try:
            import RPi.GPIO as GPIO
            
            # Set up GPIO pins
            self.LED_PIN = 17
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.LED_PIN, GPIO.OUT)
            
            # Initial state
            GPIO.output(self.LED_PIN, GPIO.LOW)
            
        except (ImportError, RuntimeError):
            logger.warning("GPIO setup failed. Running without hardware interface.")
    
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
    
    def led_blink(self, times=2, interval=0.1):
        """Blink the LED (for RPi)."""
        if IS_LINUX:
            try:
                import RPi.GPIO as GPIO
                for _ in range(times):
                    GPIO.output(self.LED_PIN, GPIO.HIGH)
                    time.sleep(interval)
                    GPIO.output(self.LED_PIN, GPIO.LOW)
                    time.sleep(interval)
            except (ImportError, RuntimeError, AttributeError):
                pass
                
    def keyword_detected(self):
        """Called when keyword is detected."""
        if self.paused:
            return
            
        try:
            # Visual feedback
            self.led_blink(times=2, interval=0.1)
            self.led_on()
            
            # Initialize STT engine (each time to ensure fresh resources)
            engine = VoskSTT()
            
            # Start full STT recognition
            text = engine.listen(timeout=5)
            logger.info(f"Transcribed: {text}")
            self.led_off()
            
            # Save to daily transcript file
            if text and text != "No speech detected":
                self._save_transcript(text)
                
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            self.led_off()
            
    def _save_transcript(self, text):
        """Save transcript to daily file."""
        try:
            # Create filename based on date
            today = datetime.now().strftime("%Y-%m-%d")
            filename = os.path.join(self.output_dir, f"transcript_{today}.txt")
            
            # Append to file
            with open(filename, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] {text}\n")
                
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")
    
    def start(self):
        """Start the service."""
        self.running = True
        self.paused = False
        
        logger.info("Starting STT background service")
        logger.info(f"Transcripts will be saved to: {self.output_dir}")
        
        # Start keyword detection
        self.keyword_detector.listen_for_keyword(callback=self.keyword_detected)
        
        # Indication that service has started
        self.led_blink(times=3, interval=0.2)
        
        # If on Windows, create system tray icon
        if IS_WINDOWS:
            self._setup_windows_tray()
    
    def _setup_windows_tray(self):
        """Set up Windows system tray icon."""
        try:
            import pystray
            from PIL import Image, ImageDraw
            
            # Create a simple icon with more visible colors
            icon_size = 64
            icon_image = Image.new('RGB', (icon_size, icon_size), color=(240, 240, 240))
            dc = ImageDraw.Draw(icon_image)
            
            # Draw a microphone icon (simplified)
            center_x, center_y = icon_size // 2, icon_size // 2
            mic_width, mic_height = 30, 40
            
            # Draw mic body
            dc.rectangle(
                [(center_x - mic_width//2, center_y - mic_height//2), 
                 (center_x + mic_width//2, center_y + mic_height//2)],
                fill=(30, 144, 255),  # Dodger blue
                outline=(0, 0, 0),
                width=2
            )
            
            # Draw mic top curve
            dc.ellipse(
                [(center_x - mic_width//2, center_y - mic_height//2 - 5),
                 (center_x + mic_width//2, center_y - mic_height//2 + 10)],
                fill=(30, 144, 255),
                outline=(0, 0, 0),
                width=2
            )
            
            # Define menu items
            def toggle_pause():
                self.paused = not self.paused
                logger.info(f"Service {'paused' if self.paused else 'resumed'}")
                
                # Update icon tooltip to show status
                icon.title = f"STT Service ({'Paused' if self.paused else 'Running'})"
            
            def exit_app():
                logger.info("Exiting from system tray")
                self.stop()
                icon.stop()
            
            # Create the icon with tooltip
            icon = pystray.Icon(
                "stt_service",
                icon=icon_image,
                title="STT Service (Running)",  # Tooltip text
                menu=pystray.Menu(
                    pystray.MenuItem("Pause/Resume", toggle_pause),
                    pystray.MenuItem("Exit", exit_app)
                )
            )
            
            # Make sure the icon is visible immediately
            logger.info("Starting system tray icon...")
            
            # Run the icon in its own thread - this is crucial for it to show
            tray_thread = threading.Thread(target=icon.run, daemon=True)
            tray_thread.start()
            
            # Store reference to prevent garbage collection
            self.tray_icon = icon
            self.tray_thread = tray_thread
            
            logger.info("System tray icon should now be visible")
            
        except ImportError:
            logger.warning("pystray not available, running without system tray icon")
        except Exception as e:
            logger.error(f"Error setting up system tray: {e}")
    
    def run_daemon(self):
        """Run as a daemon on Linux."""
        if not IS_LINUX:
            logger.error("Daemon mode is only supported on Linux")
            return
            
        try:
            import daemon
            
            # Set up daemon context
            context = daemon.DaemonContext(
                working_directory=os.getcwd(),
                umask=0o002,
                pidfile=None,  # No PID file by default
                detach_process=True,
                signal_map={
                    signal.SIGTERM: self._handle_signal,
                    signal.SIGINT: self._handle_signal
                }
            )
            
            # Open daemon context and start service
            with context:
                self.start()
                
                # Keep main thread alive
                while self.running:
                    time.sleep(1)
                    
        except ImportError:
            logger.error("python-daemon package is required for daemon mode")
        except Exception as e:
            logger.error(f"Error running as daemon: {e}")
    
    def _handle_signal(self, signum, frame):
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, shutting down")
        self.stop()
    
    def stop(self):
        """Stop the service."""
        logger.info("Stopping STT background service")
        self.running = False
        
        # Clean up resources
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'keyword_detector'):
            try:
                self.keyword_detector.stop()
            except Exception as e:
                logger.error(f"Error stopping keyword detector: {e}")
        
        # Clean up GPIO (for RPi)
        if IS_LINUX:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except (ImportError, RuntimeError):
                pass
        
        logger.info("STT service stopped")


def create_windows_service():
    """Create Windows service."""
    if not IS_WINDOWS:
        print("Windows service creation is only supported on Windows")
        return
        
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager
        import socket
        
        class AppServerSvc(win32serviceutil.ServiceFramework):
            _svc_name_ = "STTService"
            _svc_display_name_ = "Speech-to-Text Background Service"
            _svc_description_ = "Continuously listens for speech commands in the background"
            
            def __init__(self, args):
                win32serviceutil.ServiceFramework.__init__(self, args)
                self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
                socket.setdefaulttimeout(60)
                self.service = None
                
            def SvcStop(self):
                self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                win32event.SetEvent(self.hWaitStop)
                if self.service:
                    self.service.stop()
                    
            def SvcDoRun(self):
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                    servicemanager.PYS_SERVICE_STARTED,
                    (self._svc_name_, '')
                )
                
                # Create and start STT service
                self.service = STTService()
                self.service.start()
                
                # Wait for stop signal
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AppServerSvc)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(AppServerSvc)
            
    except ImportError:
        print("pywin32 is required for Windows service functionality")
    except Exception as e:
        print(f"Error setting up Windows service: {e}")


def select_audio_device():
    """Interactive device selection for STT application"""
    import pyaudio
    
    print("\nAudio Device Setup")
    print("=================")
    
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("\nAvailable audio input devices:")
    input_devices = []
    
    for i in range(0, numdevices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        if device_info.get('maxInputChannels') > 0:
            input_devices.append((i, device_info.get('name')))
            print(f"  - Device {i}: {device_info.get('name')}")
    
    if not input_devices:
        print("No input devices found!")
        p.terminate()
        return None
    
    # Ask user to select a device
    selected_device = None
    while selected_device is None:
        try:
            device_input = input("\nEnter the device number to use (or 'q' to quit): ")
            if device_input.lower() == 'q':
                p.terminate()
                return None
                
            device_num = int(device_input)
            if any(id == device_num for id, _ in input_devices):
                selected_device = device_num
                device_name = next(name for id, name in input_devices if id == device_num)
                print(f"\nSelected device {selected_device}: {device_name}")
            else:
                print("Invalid device number, try again.")
        except ValueError:
            print("Please enter a valid number.")
    
    # Verify device works
    try:
        test_stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            input_device_index=selected_device,
            frames_per_buffer=1024
        )
        test_stream.close()
        print("Device tested successfully.")
    except Exception as e:
        print(f"Error opening device: {e}")
        print("Please try a different device.")
        p.terminate()
        return None
    
    p.terminate()
    
    # Save device settings to file
    settings = {
        "input_device": selected_device,
        "device_name": device_name
    }
    
    with open("audio_settings.json", "w") as f:
        json.dump(settings, f)
    
    print(f"Audio settings saved to audio_settings.json")
    return selected_device


def load_audio_settings():
    """Load saved audio device settings"""
    if os.path.exists("audio_settings.json"):
        try:
            with open("audio_settings.json", "r") as f:
                settings = json.load(f)
            return settings.get("input_device")
        except Exception:
            return None
    return None


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
    parser = argparse.ArgumentParser(description="Fully Offline Speech-to-Text Background Service")
    parser.add_argument("--install", action="store_true", help="Install dependencies and exit")
    parser.add_argument("--model-info", action="store_true", help="Show model download instructions")
    parser.add_argument("--keywords", type=str, help="Comma-separated list of custom keywords")
    parser.add_argument("--output-dir", type=str, help="Directory to store transcripts")
    
    # Service-specific options
    parser.add_argument("--service", action="store_true", help="Run as a background service")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground (default)")
    parser.add_argument("--install-service", action="store_true", help="Install as system service (Windows/Linux)")
    
    # Audio device selection
    parser.add_argument("--setup-audio", action="store_true", help="Interactive setup for audio device")
    
    args = parser.parse_args()
    
    if args.setup_audio:
        select_audio_device()
        return
    
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
    
    # Windows service installation
    if args.install_service and IS_WINDOWS:
        create_windows_service()
        return
    
    # Parse custom keywords if provided
    keywords = None
    if args.keywords:
        keywords = [k.strip().lower() for k in args.keywords.split(",")]
    
    # Create service instance
    service = STTService(keywords=keywords, output_dir=args.output_dir)
    
    # Run in specified mode
    if args.service and IS_LINUX:
        service.run_daemon()
    else:
        # Run in foreground
        service.start()
        
        try:
            # Keep main thread alive
            while service.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
            service.stop()


if __name__ == "__main__":
    main()