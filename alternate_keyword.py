#!/usr/bin/env python3
"""
Enhanced Speech-to-Text with Alternative Keyword Detection
This uses a different approach for more reliable keyword detection
"""

import os
import time
import json
import pyaudio
from vosk import Model, KaldiRecognizer
import threading
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("stt_improved.log"), logging.StreamHandler()]
)
logger = logging.getLogger("STT-Improved")

class ImprovedKeywordDetection:
    """
    Alternative implementation of keyword detection
    Uses continuous recognition instead of VAD for more reliable results
    """
    
    def __init__(self, keywords=None, callback=None):
        # Set default keywords if none provided
        self.keywords = keywords or ["hey computer", "wake up", "listen", "start"]
        self.callback = callback
        
        # Set up Vosk model
        model_path = "model"
        if not os.path.exists(model_path):
            model_path = "vosk-model-small-en-us-0.15"
            if not os.path.exists(model_path):
                logger.error("ERROR: Model not found. Please install it first.")
                raise FileNotFoundError("Vosk model not found")
            
        self.model = Model(model_path)
        
        # Set up audio
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )
        
        # Create recognizer with partial results to improve responsiveness
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)  # Get timestamps for words
        
        # Running status
        self.running = False
        self.thread = None
    
    def start(self):
        """Start keyword detection in a background thread"""
        self.running = True
        self.thread = threading.Thread(target=self._recognition_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Started keyword detection for: {', '.join(self.keywords)}")
    
    def _recognition_loop(self):
        """Main recognition loop"""
        last_detection_time = 0
        min_time_between_detections = 3  # seconds
        
        while self.running:
            try:
                # Read audio chunk
                data = self.stream.read(4000, exception_on_overflow=False)
                
                # Process with recognizer
                if self.recognizer.AcceptWaveform(data):
                    # Get recognition result
                    result = json.loads(self.recognizer.Result())
                    self._process_result(result, last_detection_time)
                    
                # Also process partial results for faster response
                else:
                    partial = json.loads(self.recognizer.PartialResult())
                    if 'partial' in partial and partial['partial']:
                        current_time = time.time()
                        if current_time - last_detection_time > min_time_between_detections:
                            text = partial['partial'].lower()
                            
                            # Check each keyword
                            for keyword in self.keywords:
                                if keyword in text:
                                    logger.info(f"Keyword detected (partial): '{keyword}' in '{text}'")
                                    if self.callback:
                                        self.callback()
                                    last_detection_time = current_time
                                    break
            
            except Exception as e:
                logger.error(f"Error in recognition loop: {e}")
                time.sleep(0.5)  # Prevent tight loop on error
    
    def _process_result(self, result, last_detection_time):
        """Process a recognition result"""
        if 'text' in result and result['text']:
            text = result['text'].lower()
            logger.info(f"Recognized: '{text}'")
            
            current_time = time.time()
            if current_time - last_detection_time > 3:  # Prevent double triggers
                # Check each keyword
                for keyword in self.keywords:
                    if keyword in text:
                        logger.info(f"Keyword detected: '{keyword}' in '{text}'")
                        if self.callback:
                            self.callback()
                        last_detection_time = current_time
                        break
    
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
            logger.error(f"Error stopping: {e}")

# Demo code to test the detection
def keyword_callback():
    print("\n🎤 KEYWORD DETECTED! Now I would listen for a command...\n")

def main():
    print("Improved Keyword Detection Test")
    print("===============================")
    print("I'll listen for these keywords:")
    keywords = ["hey computer", "wake up", "listen", "start"]
    for kw in keywords:
        print(f"  - '{kw}'")
    
    print("\nWhen a keyword is detected, I'll notify you.")
    print("Press Ctrl+C to exit")
    
    # Create and start detector
    detector = ImprovedKeywordDetection(callback=keyword_callback)
    detector.start()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        detector.stop()
        print("Done!")

if __name__ == "__main__":
    main()