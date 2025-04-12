# Background Speech-to-Text Service

This guide explains how to set up the speech-to-text application as a continuous background service on both Windows and Raspberry Pi 5.

## Features

- **Always Running**: Starts automatically and runs continuously in the background
- **Voice Keyword Activation**: Always listening for wake words like "hey computer" or "listen"
- **Fully Offline Processing**: No data sent to external servers
- **Resource Efficient**: Optimized for low CPU/memory usage
- **System Integration**: Proper service implementation for both Windows and Linux

## Installation

### Initial Setup (Both Platforms)

1. Download the script `voice_activated.py`
2. Open a terminal/command prompt and navigate to the script directory
3. Install dependencies and download speech model:
   ```
   python voice_activated.py --install
   ```

### Setting Up as Background Service

#### Windows

**Option 1: System Service**
1. Install as a Windows service:
   ```
   python voice_activated.py --install-service
   ```
2. Start the service from Services management console
   - Open Start menu, type "services.msc" and press Enter
   - Find "Speech-to-Text Background Service"
   - Right-click and select "Start"

**Option 2: Autostart with Windows**
1. Copy the `windows-autostart.bat` script to your script directory
2. Create a shortcut to this batch file
3. Move the shortcut to the Startup folder:
   - Press `Win+R`, type `shell:startup` and press Enter
   - Move the shortcut to this folder

#### Raspberry Pi (Linux)

**Option 1: Systemd Service**
1. Copy the `stt_service.service` file to systemd directory:
   ```
   sudo cp stt_service.service /etc/systemd/system/
   ```
2. Edit the service file to match your installation path:
   ```
   sudo nano /etc/systemd/system/stt_service.service
   ```
3. Enable and start the service:
   ```
   sudo systemctl enable stt_service
   sudo systemctl start stt_service
   ```

**Option 2: Run as Daemon**
1. Start manually as a daemon:
   ```
   python3 voice_activated.py --service
   ```
2. To run at startup, add to `/etc/rc.local` before the `exit 0` line:
   ```
   python3 /home/pi/path/to/voice_activated.py --service &
   ```

## Using the Service

Once running in the background, the service:

1. Continuously listens for wake words in the background
2. Default wake words: "hey computer", "wake up", "listen", "start"
3. When a wake word is detected:
   - On Raspberry Pi: The LED on GPIO 17 will blink twice
   - The system listens for your command/speech
   - Transcription is saved to daily transcript files

### Customizing Wake Words

To use custom wake words when starting the service:
```
python voice_activated.py --keywords "computer,jarvis,assistant,hello"
```

For systemd service, edit the service file to include your keywords.

### Transcript Location

Transcripts are saved to:
- Windows: `C:\Users\YourUsername\stt_transcripts\transcript_YYYY-MM-DD.txt`
- Linux: `/home/pi/stt_transcripts/transcript_YYYY-MM-DD.txt`

To change the output directory:
```
python voice_activated.py --output-dir "/path/to/directory"
```

## Resource Usage

The background service is designed to use minimal resources:

- Typical CPU usage: 1-3% on Raspberry Pi 5, <1% on modern Windows PC
- Memory usage: ~50MB
- Storage: Minimal (text files only)

If you notice high resource usage:
1. Check if another process is using the microphone
2. Restart the service
3. Use `top` (Linux) or Task Manager (Windows) to monitor resource usage

## Management

### Windows

- **System Tray**: When running, an icon appears in the system tray
  - Right-click to pause/resume or exit the service

- **Services Console**:
  - Open "services.msc"
  - Find "Speech-to-Text Background Service"
  - Use Start/Stop/Restart options

### Linux (Raspberry Pi)

- **View Status**:
  ```
  sudo systemctl status stt_service
  ```

- **View Logs**:
  ```
  journalctl -u stt_service
  ```

- **Start/Stop**:
  ```
  sudo systemctl start stt_service
  sudo systemctl stop stt_service
  ```

## Troubleshooting

### Service Not Starting

**Windows**:
1. Check Windows Event Viewer for errors
2. Make sure Python is in your PATH environment variable
3. Run the script manually with `python voice_activated.py` to check for errors
4. Make sure all dependencies are installed with `python voice_activated.py --install`

**Linux**:
1. Check logs with `journalctl -u stt_service`
2. Ensure proper permissions:
   ```
   sudo chmod +x /path/to/voice_activated.py
   ```
3. Check if Python and dependencies are installed:
   ```
   python3 --version
   pip3 list | grep vosk
   ```

### Microphone Issues

1. **No audio input detected**:
   - Check if your microphone is properly connected
   - On Windows: Select the correct microphone in Sound settings
   - On Raspberry Pi: Run `arecord -l` to list audio devices
   - If using USB microphone on RPi: Make sure it's set as default
   
2. **Creating ALSA default on Raspberry Pi**:
   ```
   sudo nano /etc/asound.conf
   ```
   
   Add the following (adjust card and device numbers as needed):
   ```
   pcm.!default {
     type asym
     playback.pcm {
       type plug
       slave.pcm "hw:0,0"
     }
     capture.pcm {
       type plug
       slave.pcm "hw:1,0"  # Change to your USB mic
     }
   }
   ```

### Service Running But Not Responding

1. Check if service is paused (Windows system tray)
2. Ensure microphone is working and not muted
3. Restart the service
4. Check the logs:
   - Windows: Check `stt_service.log` in the script directory
   - Linux: `journalctl -u stt_service -f` to follow logs

### High CPU Usage

1. Make sure you're using at least RPi 5 (RPi 4 may struggle)
2. Stop other resource-intensive processes
3. Check if system is running updates or other background tasks
4. Try restarting the service

## Hardware (Raspberry Pi)

If you want to see visual feedback:

1. Connect an LED to GPIO pin 17 and GND through a 220-330Ω resistor:
   ```
   GPIO 17 ──┬── LED ─── 220Ω Resistor ─── GND
             │
   3.3V ─────┘
   ```

2. The LED will:
   - Blink 3 times when service starts
   - Blink twice when a keyword is detected
   - Stay on while listening for your command
   - Turn off when done listening

## Uninstalling

### Windows Service

1. Open an administrator command prompt
2. Navigate to script directory
3. Run:
   ```
   python voice_activated.py --install-service --remove
   ```
   
### Linux Service

1. Stop and disable the service:
   ```
   sudo systemctl stop stt_service
   sudo systemctl disable stt_service
   ```

2. Remove service file:
   ```
   sudo rm /etc/systemd/system/stt_service.service
   sudo systemctl daemon-reload
   ```

## Advanced Configuration

You can modify the script to customize:
- Sensitivity of voice detection
- Timeout durations
- LED patterns
- Wake word sensitivity
- Transcript formatting

For specific advanced configurations, check the comments in the `voice_activated.py` source code.