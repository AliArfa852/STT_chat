# Fully Offline Speech-to-Text: Setup Guide

This guide will help you set up and run the fully offline speech-to-text application on both Windows and Raspberry Pi 5, with absolutely no internet dependencies after initial setup.

## Requirements

- Python 3.6 or higher
- Microphone
- For Raspberry Pi 5: GPIO pins for LED and button (optional)

## Initial Setup

You'll need internet connectivity only for the initial setup. After that, the application runs 100% offline.

### Windows

1. Make sure Python is installed and in your PATH
2. Download the script
3. Open Command Prompt and navigate to the script directory
4. Install dependencies and download speech model:
   ```
   python stt_app.py --install
   ```

### Raspberry Pi 5

1. Make sure Python is installed
2. Download the script
3. Open Terminal and navigate to the script directory
4. Install dependencies and download speech model:
   ```
   python3 stt_app.py --install
   ```
5. (Optional) Connect hardware:
   - Connect an LED to GPIO pin 17 and GND
   - Connect a button to GPIO pin 27 and GND

## Completely Offline Setup

If you need to install on a computer with no internet access:

1. On a computer with internet, run:
   ```
   python stt_app.py --model-info
   ```
   
2. Follow the instructions to manually download the Vosk model

3. Transfer the script and model folder to your offline computer

4. Install required packages on your offline machine using offline installation methods:
   - PyAudio
   - numpy
   - sounddevice
   - vosk
   - (For Raspberry Pi) RPi.GPIO

## Using the Application

The application uses Vosk for offline speech recognition:

```
python stt_app.py
```

### Hardware Interaction (Raspberry Pi only)

If you've connected the recommended hardware:
- Press the button to start listening
- The LED will light up while the system is listening
- Speaking will be transcribed to text and saved in transcript.txt

On Windows or without hardware, press Enter to start listening.

## Troubleshooting

### Common Issues on Windows

1. **PyAudio installation fails**: 
   - Download the appropriate .whl file from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
   - Install with `pip install [downloaded-file.whl]`

2. **"No Default Input Device Found"**: 
   - Select the correct microphone in Windows Sound settings

3. **Model loading error**:
   - Make sure the 'model' folder is in the same directory as the script
   - Check the folder structure matches what Vosk expects

### Common Issues on Raspberry Pi

1. **Permission denied for /dev/mem**: Run with sudo
2. **Microphone not detected**: 
   - Use `arecord -l` to list audio devices
   - Make sure your microphone is properly connected

3. **Missing modules**:
   - Install Python dev packages: `sudo apt-get install python3-dev`
   - Install PortAudio: `sudo apt-get install portaudio19-dev`

## Model Customization

Vosk supports different models with varying sizes and accuracies:

- **Small model** (default): ~50MB, good for simple commands
- **Large model**: ~1.5GB, much higher accuracy

To use a different model:
1. Download from https://alphacephei.com/vosk/models
2. Extract and rename to "model"
3. Replace the existing model folder

## Offline Mode Details

This application is designed to work without any internet connection:

- Uses Vosk for offline speech recognition
- Saves all transcriptions locally to `transcript.txt`
- No data is sent to any external servers
- All processing happens on your local device

## Hardware Diagram (Raspberry Pi)

```
Raspberry Pi GPIO
-----------------
       3.3V Power ── ▭ ▭ ── 5V Power
                  ── ▭ ▭ ──
                  ── ▭ ▭ ──
                  ── ▭ ▭ ──
                  ── ▭ ▭ ──
                  ── ▭ ▭ ──
           Ground ── ▭ ▭ ── GPIO 17 (LED)
                  ── ▭ ▭ ──
                  ── ▭ ▭ ── 
                  ── ▭ ▭ ──
                  ── ▭ ▭ ── GPIO 27 (Button)
                  ── ▭ ▭ ──
```

LED: Connect to GPIO 17 with a resistor (220-330Ω) to ground
Button: Connect to GPIO 27 and ground