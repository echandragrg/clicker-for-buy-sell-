import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import time
import re
import ctypes

import mss
from PIL import Image
import pytesseract
import pyautogui


# Update this path if Tesseract is installed elsewhere.
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# PyAutoGUI safety setting.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


class ScreenTextReader:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Signal Monitor")
        self.root.geometry("650x520")
        self.root.attributes("-topmost", True)

        self.points = {
            "point1": None,
            "point2": None,
            "point3": None,
        }

        self.region = None
        self.current_signal = None
        self.running = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.last_keep_awake_click = time.monotonic()

        self.cond1 = False
        self.cond2 = False

        tk.Label(
            root,
            text="Screen Signal Monitor",
            font=("Arial", 18, "bold")
        ).pack(pady=10)

        self.status = tk.Label(
            root,
            text="Step 1: Select the signal area",
            font=("Arial", 11)
        )
        self.status.pack(pady=5)

        tk.Button(
            root,
            text="1. Select Monitoring Area",
            command=self.select_area
        ).pack(pady=4)

        tk.Button(
            root,
            text="2. Mark Point 1 (BUY)",
            command=lambda: self.mark_point("point1")
        ).pack(pady=4)

        tk.Button(
            root,
            text="3. Mark Point 2 (SELL)",
            command=lambda: self.mark_point("point2")
        ).pack(pady=4)

        tk.Button(
            root,
            text="4. Mark Point 3 (Every 60 Seconds)",
            command=lambda: self.mark_point("point3")
        ).pack(pady=4)

        buttons = tk.Frame(root)
        buttons.pack(pady=8)

        tk.Button(
            buttons,
            text="Start Monitoring",
            command=self.start_monitoring,
            bg="#16803c",
            fg="white"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            buttons,
            text="Stop Monitoring",
            command=self.stop_monitoring,
            bg="#b42318",
            fg="white"
        ).pack(side=tk.LEFT, padx=5)

        self.output = scrolledtext.ScrolledText(
            root,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        self.output.pack(
            fill="both", expand=True, padx=12, pady=8
        )

        self.log("Select the signal area first.")
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        # Ask for the screen area when the app opens.
        self.root.after(500, self.select_area)

    def log(self, text):
        """Safely write a message to the GUI."""
        if not self.root.winfo_exists():
            return

        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)

    # --------------------------------------------------
    # STEP 1: SELECT SCREEN REGION
    # --------------------------------------------------

    def select_area(self):
        if self.running:
            messagebox.showwarning(
                "Monitoring active",
                "Stop monitoring before changing the area."
            )
            return

        self.root.withdraw()

        self.overlay = tk.Toplevel(self.root)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.30)
        self.overlay.configure(bg="black")
        self.overlay.config(cursor="crosshair")

        self.canvas = tk.Canvas(
            self.overlay,
            bg="black",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_text(
            350, 40,
            text="Drag to select the signal area. Press ESC to cancel.",
            fill="white",
            font=("Arial", 16, "bold")
        )

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.draw_selection)
        self.canvas.bind("<ButtonRelease-1>", self.finish_selection)
        self.overlay.bind("<Escape>", self.cancel_selection)
        self.overlay.focus_force()

    def start_selection(self, event):
        self.start_x = event.x
        self.start_y = event.y

        self.rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="red", width=3
        )

    def draw_selection(self, event):
        self.canvas.coords(
            self.rect,
            self.start_x, self.start_y,
            event.x, event.y
        )

    def finish_selection(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)

        self.overlay.destroy()
        self.root.deiconify()

        if x2 - x1 < 5 or y2 - y1 < 5:
            self.log("Selection too small. Select again.")
            return

        self.region = {
            "left": x1,
            "top": y1,
            "width": x2 - x1,
            "height": y2 - y1
        }

        # Reset the signal baseline when selecting a new area.
        self.current_signal = None
        self.cond1 = False
        self.cond2 = False

        self.status.config(text="Monitoring area selected")
        self.log(f"Area selected: {self.region}")

        # Prompt for Point 1, then Point 2, then Point 3.
        self.root.after(
            300,
            lambda: self.mark_point("point1")
        )

    def cancel_selection(self, event=None):
        self.overlay.destroy()
        self.root.deiconify()
        self.log("Area selection cancelled.")

    # --------------------------------------------------
    # STEP 2: MARK POINTS BY CLICKING THE SCREEN
    # --------------------------------------------------

    def mark_point(self, name):
        if self.running:
            messagebox.showwarning(
                "Monitoring active",
                "Stop monitoring before marking points."
            )
            return

        if self.region is None:
            messagebox.showwarning(
                "Select area first",
                "Please select the monitoring area first."
            )
            return

        labels = {
            "point1": "BUY",
            "point2": "SELL",
            "point3": "Keep-awake"
        }

        messagebox.showinfo(
            "Mark " + labels[name],
            "Click OK, then click the desired position "
            "on your screen.\n\n"
            "Press ESC to cancel."
        )

        self.root.withdraw()

        self.point_overlay = tk.Toplevel(self.root)
        self.point_overlay.attributes("-fullscreen", True)
        self.point_overlay.attributes("-topmost", True)
        self.point_overlay.attributes("-alpha", 0.15)
        self.point_overlay.configure(bg="black")
        self.point_overlay.config(cursor="crosshair")

        canvas = tk.Canvas(
            self.point_overlay,
            bg="black",
            highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)

        canvas.create_text(
            450, 40,
            text=f"Click the screen location for {labels[name]}",
            fill="white",
            font=("Arial", 16, "bold")
        )

        self.point_overlay.bind(
            "<Button-1>",
            lambda event: self.save_point(
                name, event.x_root, event.y_root
            )
        )

        self.point_overlay.bind(
            "<Escape>",
            self.cancel_point
        )

        self.point_overlay.focus_force()

    def save_point(self, name, x, y):
        self.points[name] = (x, y)
        self.point_overlay.destroy()
        self.root.deiconify()

        self.log(f"{name} saved at X={x}, Y={y}")

        if name == "point1":
            self.root.after(
                300,
                lambda: self.mark_point("point2")
            )
        elif name == "point2":
            self.root.after(
                300,
                lambda: self.mark_point("point3")
            )
        else:
            self.status.config(
                text="All points saved. Ready to monitor."
            )
            self.log("All three points are ready.")

    def cancel_point(self, event=None):
        self.point_overlay.destroy()
        self.root.deiconify()
        self.log("Point selection cancelled.")

    # --------------------------------------------------
    # STEP 3: CONTINUOUS OCR MONITORING
    # --------------------------------------------------

    def start_monitoring(self):
        if self.running:
            return

        if self.region is None:
            messagebox.showwarning(
                "Missing area",
                "Select a monitoring area first."
            )
            return

        if any(p is None for p in self.points.values()):
            messagebox.showwarning(
                "Missing points",
                "Please mark Points 1, 2 and 3 first."
            )
            return

        self.running = True
        self.stop_event.clear()
        self.current_signal = None
        self.last_keep_awake_click = time.monotonic()

        # Request that Windows keep the system awake.
        ctypes.windll.kernel32.SetThreadExecutionState(
            0x80000000 | 0x00000001
        )

        self.status.config(text="Monitoring is running")
        self.log("Monitoring started.")

        self.monitor_thread = threading.Thread(
            target=self.monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()

        self.root.after(1000, self.keep_awake_loop)

    def monitor_loop(self):
        try:
            with mss.mss() as screen:
                while not self.stop_event.is_set():
                    screenshot = screen.grab(self.region)

                    image = Image.frombytes(
                        "RGB",
                        screenshot.size,
                        screenshot.rgb
                    )

                    # Enlarge the captured area for OCR.
                    image = image.resize(
                        (image.width * 2, image.height * 2)
                    )

                    text = pytesseract.image_to_string(
                        image, config="--psm 6"
                    ).strip()

                    # Only recognise whole words.
                    upper_text = text.upper()
                    has_buy = bool(
                        re.search(r"\bBUY\b", upper_text)
                    )
                    has_sell = bool(
                        re.search(r"\bSELL\b", upper_text)
                    )

                    if has_buy and not has_sell:
                        signal = "BUY"
                    elif has_sell and not has_buy:
                        signal = "SELL"
                    else:
                        signal = None

                    self.root.after(
                        0,
                        lambda t=text, s=signal:
                            self.process_signal(t, s)
                    )

                    # Poll approximately once per second.
                    self.stop_event.wait(1.0)

        except Exception as error:
            self.root.after(
                0,
                lambda e=str(error): self.monitor_error(e)
            )

    def process_signal(self, text, signal):
        if not self.running:
            return

        self.output.delete("1.0", tk.END)
        self.output.insert(
            tk.END,
            f"Recognised text:\n{text or '(no text detected)'}\n\n"
            f"Current signal: {signal or 'NONE'}\n"
            f"cond1 (BUY): {signal == 'BUY'}\n"
            f"cond2 (SELL): {signal == 'SELL'}"
        )

        self.cond1 = signal == "BUY"
        self.cond2 = signal == "SELL"

        # Click only when the signal changes to BUY or SELL.
        if signal is not None and signal != self.current_signal:
            self.log(
                f"Signal changed: {self.current_signal} -> {signal}"
            )

            if signal == "BUY":
                self.click_point("point1")
            elif signal == "SELL":
                self.click_point("point2")

            self.current_signal = signal

        # Keep the last BUY/SELL state through uncertain OCR frames.
        # This avoids re-clicking if OCR briefly misses the signal.

    # --------------------------------------------------
    # POINT 3: PERIODIC CLICK / KEEP AWAKE
    # --------------------------------------------------

    def keep_awake_loop(self):
        if not self.running:
            return

        now = time.monotonic()

        if now - self.last_keep_awake_click >= 60:
            self.click_point("point3")
            self.last_keep_awake_click = now
            self.log("Point 3 clicked.")

        self.root.after(1000, self.keep_awake_loop)

    def click_point(self, name):
        position = self.points.get(name)

        if position is not None:
            try:
                pyautogui.click(position[0], position[1])
                self.log(f"Clicked {name}: {position}")
            except Exception as error:
                self.log(f"Click failed: {error}")
                self.stop_monitoring()

    # --------------------------------------------------
    # STOP / ERROR / CLOSE
    # --------------------------------------------------

    def monitor_error(self, error):
        self.log(f"Monitoring error: {error}")
        self.stop_monitoring()

    def stop_monitoring(self):
        self.running = False
        self.stop_event.set()

        # Restore normal Windows sleep policy.
        ctypes.windll.kernel32.SetThreadExecutionState(
            0x80000000
        )

        self.status.config(text="Monitoring stopped")
        self.log("Monitoring stopped.")

    def close_app(self):
        self.stop_monitoring()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenTextReader(root)
    root.mainloop()
