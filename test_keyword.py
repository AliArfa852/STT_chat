#!/usr/bin/env python3
"""
Test script to verify keyword detection is working properly
"""
import os
import time
import json
import logging
from vosk import Model, KaldiRecognizer
import pyaudio
import threading
from collections import deque
import webrtcvad

# Set up logging with console output only
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("KeywordTest")

def test_keyword_detection():
    # Define the keywords we want to detect
    keywords = ["hey computer", "wake up", "listen", "start"]
    logger.info(f"Testing detection of keywords: {keywords}")
    
    # Set up the model
    model_path = "model"
    if not os.path.exists(model_path):
        model_path = "vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            logger.error("ERROR: Model not found. Please install it first.")
            return
    
    model = Model(model_path)
    
    # Set up audio
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=960  # 60ms frames for VAD
    )
    
    # Set up Voice Activity Detection
    vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (highest)
    speech_frames = deque(maxlen=30)  # Store ~1.8 seconds of audio
    
    # Create recognizer - no grammar restrictions
    recognizer = KaldiRecognizer(model, 16000)
    
    # State variables
    speech_active = False
    potential_command = False
    silence_counter = 0
    detected_count = 0
    
    # Countdown before starting
    logger.info("Starting in:")
    for i in range(3, 0, -1):
        logger.info(f"{i}...")
        time.sleep(1)
    
    logger.info("LISTENING - speak one of the keywords clearly")
    logger.info("Press Ctrl+C to stop")
    
    start_time = time.time()
    try:
        # Main listening loop
        while time.time() - start_time < 60:  # Run for 1 minute max
            # Read audio frame (60ms)
            frame = stream.read(960, exception_on_overflow=False)
            
            # Check for voice activity
            try:
                is_speech = vad.is_speech(frame, 16000)
            except Exception:
                is_speech = False
            
            # State machine for keyword detection
            if is_speech:
                # Reset counters when speech is detected
                silence_counter = 0
                speech_frames.append(frame)
                
                if not speech_active and len(speech_frames) > 5:  # ~300ms of speech
                    speech_active = True
                    potential_command = True
                    logger.info("Speech detected, listening...")
            
            else:  # Silence detected
                if speech_active:
                    silence_counter += 1
                    
                    # After 500ms of silence, process the collected audio
                    if silence_counter > 8 and potential_command:
                        # Combine collected frames for processing
                        buffered_audio = bytearray()
                        for f in speech_frames:
                            buffered_audio.extend(f)
                        
                        # Process audio with keyword recognizer
                        recognizer.AcceptWaveform(bytes(buffered_audio))
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").lower()
                        
                        if text:
                            logger.info(f"Heard: '{text}'")
                            
                            # Check if any keyword was detected
                            for keyword in keywords:
                                if keyword in text:
                                    logger.info(f"SUCCESS! Keyword detected: '{keyword}' in '{text}'")
                                    detected_count += 1
                                    break
                        
                        # Reset for next detection
                        potential_command = False
                        speech_frames.clear()
                    
                    # Reset speech active flag after enough silence
                    if silence_counter > 15:  # ~900ms of silence
                        speech_active = False
                        speech_frames.clear()
            
            time.sleep(0.01)  # Prevent tight loop
            
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    finally:
        # Clean up
        stream.stop_stream()
        stream.close()
        p.terminate()
    
    # Report results
    logger.info(f"Test complete. Detected {detected_count} keywords in {int(time.time() - start_time)} seconds")
    if detected_count > 0:
        logger.info("Keyword detection is working!")
    else:
        logger.info("No keywords were detected. Try the following:")
        logger.info("1. Speak more clearly and louder")
        logger.info("2. Check your microphone")
        logger.info("3. Make sure you're using one of these keywords: " + ", ".join(keywords))

if __name__ == "__main__":
    test_keyword_detection()