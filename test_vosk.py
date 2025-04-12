#!/usr/bin/env python3
"""
Simple Vosk Speech Recognition Test
This test focuses on basic speech-to-text without keyword filtering
"""

import os
import json
import time
import pyaudio
from vosk import Model, KaldiRecognizer

def test_vosk_recognition():
    print("Vosk Speech Recognition Test")
    print("===========================")
    
    # Check if model exists
    model_path = "model"
    if not os.path.exists(model_path):
        model_path = "vosk-model-small-en-us-0.15"
        if not os.path.exists(model_path):
            print("ERROR: Model not found. Please install it first.")
            return False
    
    print(f"Using model: {model_path}")
    
    # Set up Vosk
    model = Model(model_path)
    
    # Set up audio
    p = pyaudio.PyAudio()
    
    # Print info about default input device
    default_input = p.get_default_input_device_info()
    print(f"\nDefault input device: {default_input['name']}")
    print(f"Sample rate: {int(default_input['defaultSampleRate'])} Hz")
    
    # Set up audio stream with 16KHz (required for Vosk)
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=8000
    )
    
    # Create recognizer
    rec = KaldiRecognizer(model, 16000)
    
    # Start listening
    print("\nListening for 30 seconds. Please speak clearly.")
    print("Try saying each of these phrases:")
    print("  - 'hey computer'")
    print("  - 'wake up'")
    print("  - 'listen'")
    print("  - 'start'")
    print("\nSpoken text will appear below:")
    print("-" * 50)
    
    # Countdown
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    # Track utterances for summary
    all_texts = []
    
    # Main listening loop
    start_time = time.time()
    while time.time() - start_time < 30:  # Listen for 30 seconds
        data = stream.read(4000, exception_on_overflow=False)
        
        if len(data) == 0:
            break
            
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").lower()
            
            if text:
                print(f"Recognized: '{text}'")
                all_texts.append(text)
    
    # Get final result
    result = json.loads(rec.FinalResult())
    text = result.get("text", "")
    if text:
        print(f"Final: '{text}'")
        all_texts.append(text)
    
    # Clean up
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Show summary
    print("-" * 50)
    print("\nTest complete!")
    
    if all_texts:
        print(f"\nRecognized {len(all_texts)} utterances:")
        for i, text in enumerate(all_texts, 1):
            print(f"  {i}. '{text}'")
            
        # Check if any keywords were detected
        keywords = ["hey computer", "wake up", "listen", "start"]
        matched_keywords = []
        
        for text in all_texts:
            for keyword in keywords:
                if keyword in text:
                    matched_keywords.append((keyword, text))
        
        if matched_keywords:
            print("\nDetected these keywords:")
            for keyword, text in matched_keywords:
                print(f"  - '{keyword}' in '{text}'")
            return True
        else:
            print("\nNo keywords were detected in the recognized text.")
            return False
    else:
        print("No speech was recognized during the test.")
        return False

if __name__ == "__main__":
    success = test_vosk_recognition()
    
    if not success:
        print("\nTroubleshooting tips:")
        print("1. Make sure your microphone is working (run mic_test.py first)")
        print("2. Speak clearly and loudly")
        print("3. Try in a quieter environment")
        print("4. Check that the Vosk model is correctly installed")