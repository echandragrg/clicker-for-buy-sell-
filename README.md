# RSI Divergence — Screen Signal & TP Monitor

A Python desktop application for monitoring TradingView indicator signals using OCR (Optical Character Recognition) and automating mouse clicks on a configured trading interface.

The application uses **Python, Tkinter, Tesseract OCR, MSS, Pillow, and PyAutoGUI** to detect BUY/SELL signals and trade-status markers displayed on the screen, then perform configured trading actions.

> **Disclaimer:** This is an experimental screen-automation tool, not a broker API integration. It relies on OCR recognition and screen coordinates, so missed signals, incorrect clicks, timing issues, or unexpected interface changes can cause unintended trading actions. Test thoroughly in a demo environment before considering live use.

## Features

- **Screen monitoring:** Select a screen region to monitor for visible trading signals.
- **OCR signal detection:** Uses Tesseract OCR to recognize BUY, SELL, and trade-status markers.
- **Automated BUY/SELL clicks:** Clicks configured trade buttons and the associated Change Order control.
- **Take-profit handling:** Supports TP1, TP2, and TP3 markers for BUY and SELL trades.
- **Stop-loss handling:** Detects the standalone `HIT` status and clicks the configured stop-loss and Change Order controls.
- **Close-all support:** Includes a Close All Positions click sequence before switching to an opposite-side signal when a trade is marked active.
- **Custom screen coordinates:** Configure the location of each button directly on your screen.
- **Keep-awake action:** Periodically clicks a configured position while monitoring.
- **Desktop interface:** Tkinter provides monitoring controls, setup buttons, status information, and a scrolling activity log.
- **Emergency stop control:** Stop monitoring from the application interface.

## How It Works

The application periodically captures the selected screen area, processes the screenshot with OCR, and checks the recognized text for supported markers.

### Supported signals and markers

| Marker | Intended action |
|---|---|
| `BUY` | Click BUY, then Change Order |
| `SELL` | Click SELL, then Change Order |
| `HIT1B` | Execute BUY TP1 sequence |
| `HIT2B` | Click BUY TP2 |
| `HIT3B` | Click BUY TP3, then Change Order |
| `HIT1S` | Execute SELL TP1 sequence |
| `HIT2S` | Click SELL TP2 |
| `HIT3S` | Click SELL TP3, then Change Order |
| `HIT` | Click Stop Loss, then Change Order |

The TP and SL markers are intended to come from the status displayed by the trading indicator. The application does not calculate RSI divergence or independently determine whether a target or stop-loss price has been reached.

## Requirements

- Windows is recommended for the current configuration.
- Python 3.10 or newer is recommended.
- Tesseract OCR installed on your computer.
- A compatible trading interface displayed on your screen.
- TradingView or another signal display showing the expected text markers.

### Python dependencies

- `tkinter` — desktop interface (normally included with the standard Windows Python installer).
- `mss` — screen capture.
- `Pillow` — screenshot image processing.
- `pytesseract` — Python interface to Tesseract OCR.
- `PyAutoGUI` — mouse automation.

## Installation

### 1. Install Python

Download and install Python from:

https://www.python.org/downloads/

On Windows, enable the option to add Python to PATH during installation.

### 2. Install Tesseract OCR

Install Tesseract OCR and note its installation location.

Official project:

https://github.com/tesseract-ocr/tesseract

The current script uses this Windows path:

```python
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)
```

If Tesseract is installed elsewhere, update the path to match your computer.

### 3. Download the project

Clone your repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER
```

Alternatively, download the repository as a ZIP file from GitHub and extract it.

### 4. Install the Python packages

Open Command Prompt or PowerShell in the project folder and run:

```bash
python -m pip install mss Pillow pytesseract PyAutoGUI
```

If your Python installation does not include Tkinter, install a Python distribution that includes it.

## Configuration and Setup

### Step 1: Run the application

Save the script as `main.py`, then run:

```bash
python main.py
```

The **Screen Signal & TP Monitor** window will open.

### Step 2: Select the monitoring area

1. Select the region containing your indicator's signal and status text.
2. Drag across the screen to select the area.
3. Make sure the signal text is readable and large enough for OCR.

Avoid including unrelated text such as old signals, chart labels, or other indicators where possible.

### Step 3: Configure screen positions

Use the application's **Mark** buttons to select the screen coordinates of each control:

- Change Order (BUY/SELL)
- Change Order (SL/TP3)
- Close All Positions
- BUY
- SELL
- TP Buy 1, 2, and 3
- TP Sell 1, 2, and 3
- Stop Loss (SL)
- Stay Awake

For each position, click its Mark button and then click the corresponding location on the screen.

**Important:** These are screen coordinates, not broker API identifiers. If the window moves, the screen resolution changes, or the interface layout changes, you may need to configure the positions again.

### Step 4: Start monitoring

Click **Start Monitoring** to begin OCR scanning.

The application will log detected actions and mouse clicks in its activity window. Use **Stop Monitoring** to stop the automation loop.

## Trading Workflow

The intended workflow is:

1. The TradingView indicator displays a BUY or SELL signal.
2. The Python application detects the signal in the selected screen area.
3. It clicks the corresponding trade button and Change Order control.
4. As TP or SL status markers appear, the application detects the markers and performs the configured click sequences.
5. When an opposite-side signal appears while the application considers a trade active, the script attempts to close all positions and perform its configured order-change sequence before clicking the new side.

The exact outcome depends on the trading interface, OCR accuracy, configured coordinates, and the actions assigned to the buttons.

## TradingView Indicator

This Python tool is intended to complement a separate RSI divergence indicator.

**TradingView indicator:** [Insert your TradingView publication URL here]

The indicator and Python application are separate projects. The Python application reads text visible on the screen; it does not directly connect to TradingView's alert API.

## Safety and Limitations

Please read these limitations before using the application:

- **OCR errors:** Similar-looking text, small fonts, low contrast, or overlapping chart elements can cause missed or incorrect detections.
- **Screen coordinates:** Mouse clicks may land on the wrong control if the interface changes position or size.
- **Execution uncertainty:** A successful mouse click does not confirm that an order was accepted or filled.
- **Position verification:** The script does not independently verify account positions, order history, available margin, or execution prices.
- **Network and interface failures:** Delays, frozen windows, connection loss, and unexpected pop-ups can interrupt the workflow.
- **Keep-awake behavior:** The configured click is a screen interaction, not a guarantee that every system or application will remain awake.
- **Maximum trade duration:** This Python script does not independently count TradingView candles or enforce the indicator's 59-candle expiration rule.
- **Risk management:** Use broker-side protections where available. Never assume that a plotted stop-loss or a recognized marker guarantees a real order will close.

The application is provided as-is. Start with paper trading or a demo account, verify every configured coordinate, and supervise all automated activity.

## Troubleshooting

**Tesseract executable not found**

Check that Tesseract is installed and that `tesseract_cmd` points to the correct executable.

**Signals are not detected**

- Enlarge the monitoring area or improve text visibility.
- Check the OCR output and application log.
- Ensure the displayed markers match the expected text.
- Avoid including multiple conflicting BUY/SELL labels in the selected area.

**Mouse clicks are incorrect**

- Stop monitoring before reconfiguring positions.
- Re-mark each button using the current interface layout.
- Test every configured position manually in a safe environment.

**Python package errors**

Run:

```bash
python -m pip install --upgrade mss Pillow pytesseract PyAutoGUI
```

## Project Structure

```text
your-repository/
├── main.py
├── README.md
└── requirements.txt
```

An optional `requirements.txt` can contain:

```text
mss
Pillow
pytesseract
PyAutoGUI
```

## License

Choose a license before distributing the project publicly. For example, you can use the MIT License if you want others to use, modify, and redistribute your code under its terms. Add a `LICENSE` file to the repository if you choose that license.

## Contributions and Feedback

Suggestions, bug reports, and improvements are welcome. Please include relevant error messages, steps to reproduce an issue, and your Python and operating-system versions when reporting problems.

**Use responsibly. Test carefully. Protect your capital.**
