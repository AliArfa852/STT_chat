[Unit]
Description=Speech-to-Text Background Service
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/stt_service
ExecStart=/usr/bin/python3 /home/pi/stt_service/voice_activated.py --service
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target