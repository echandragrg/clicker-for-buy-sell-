# Screen Signal Monitor

A Python desktop automation tool that monitors selected areas of the screen, detects trading signals using Optical Character Recognition (OCR), and performs configured mouse clicks when signals change.

Built with Python, Tkinter, Tesseract OCR, MSS, Pillow, and PyAutoGUI, the application is designed to automate interactions with screen-based trading indicators and interfaces.

## Features

- **Screen Area Selection:** Select specific screen regions to monitor using a drag-to-select overlay.
- **OCR Signal Detection:** Uses Tesseract OCR to recognise text displayed in selected screen areas.
- **BUY/SELL Detection:** Detects BUY and SELL signals and triggers the corresponding configured click.
- **Add Position Signals:** Supports separate Add BUY and Add SELL actions in the upgraded design.
- **Stop-Loss and Take-Profit Monitoring:** Supports monitoring SL HIT and TP1–TP5 HIT indicators.
- **Configurable Click Positions:** Select the screen coordinates where actions should be performed.
- **Keep-Active Click:** Performs a configurable mouse click at regular intervals.
- **Start/Stop Controls:** Start and stop monitoring from the graphical user interface.
- **Activity Logging:** Displays recognised signals, detected events, and click actions.
- **Windows Keep-Awake Support:** Requests that Windows prevent ordinary system sleep while monitoring is active.
- **Emergency Mouse Failsafe:** Uses PyAutoGUI's failsafe mechanism to help stop automation in an emergency.

## How It Works

1. Select the screen region containing the indicator or signal.
2. Configure the screen coordinates for the required actions.
3. The application captures the selected screen area.
4. Tesseract OCR extracts the visible text.
5. The application identifies relevant signals, such as BUY, SELL, or HIT.
6. When a new signal is detected, the corresponding mouse action is triggered.
7. The application records activity in the log and continues monitoring until stopped.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Tkinter | Desktop graphical user interface |
| Tesseract OCR | Text recognition |
| pytesseract | Python interface for Tesseract |
| MSS | Fast screen capture |
| Pillow | Image processing and resizing |
| PyAutoGUI | Mouse automation |
| Threading | Background monitoring |
| ctypes | Windows system execution-state controls |

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer recommended
- Tesseract OCR installed on the computer
- A display showing the signals or indicators to monitor

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/screen-signal-monitor.git
cd screen-signal-monitor
```

Replace `YOUR-USERNAME` with your GitHub username.

### 2. Install Python dependencies

```bash
pip install mss pillow pytesseract pyautogui
```

### 3. Install Tesseract OCR

Install Tesseract OCR for Windows and update the executable path in the Python script if necessary:

```python
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
```

Make sure the path matches your installation.

### 4. Run the application

```bash
python screen_signal_monitor.py
```

## Usage

1. Launch the application.
2. Select the monitoring area or areas.
3. Mark the screen positions corresponding to each action.
4. Start monitoring.
5. Observe the activity log to confirm detected signals and clicks.
6. Use **Stop Monitoring** to stop the automation.

The exact configuration options depend on which version of the application you are using.

## Safety and Limitations

- This application uses OCR and screen coordinates rather than a direct trading API.
- OCR can misread text because of low resolution, animations, overlapping text, or changes in the interface.
- Incorrect screen coordinates may trigger unintended actions.
- A detected HIT label does not independently confirm that an order was filled or a position was closed.
- The keep-awake feature does not guarantee that a trading platform or network connection remains active.
- Test the application using a demo account or non-trading environment before considering live use.
- Do not leave automated clicks unattended until the behaviour has been thoroughly tested.

**Important:** This project is a screen automation utility, not financial advice or a trading strategy. Use it at your own risk.

## Project Structure

```text
screen-signal-monitor/
├── screen_signal_monitor.py
├── README.md
├── requirements.txt
└── .gitignore
```

## Dependencies

You can create a `requirements.txt` file containing:

```text
mss
Pillow
pytesseract
PyAutoGUI
```

Note that Tesseract OCR itself is a separate system installation and is not installed by `pip`.

## Future Improvements

- Configurable monitoring intervals
- Improved OCR accuracy and signal validation
- Visual status indicators for each monitoring area
- Persistent configuration for screen regions and click positions
- Screenshot-based debugging
- Event history and exportable logs
- More robust handling of missed or duplicated signals
- Optional integration with trading APIs where supported

## License

This project is currently unlicensed. Add a `LICENSE` file before allowing others to reuse, modify, or distribute the code.

## Disclaimer

This software automates mouse interactions based on information displayed on the screen. It is provided for educational and experimental purposes. The author makes no guarantees regarding accuracy, reliability, trading outcomes, or suitability for live financial activity.
