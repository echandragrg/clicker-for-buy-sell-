import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import time
import re
import ctypes
import sys

import mss
from PIL import Image
import pytesseract
import pyautogui


# Update this path if Tesseract is installed somewhere else.
# Example: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

pyautogui.FAILSAFE = True
# Keep PyAutoGUI's built-in pause low; explicit waits are used for action timing.
pyautogui.PAUSE = 0.02


class ScreenTextReader:
    """OCR-driven click helper.

    OCR rules:
      - BUY / SELL: close any open position first (if needed), then click the matching trade button, then Change Order.
      - HIT1B / HIT1S: execute TP1 for BUY / SELL.
      - HIT2B / HIT2S: execute TP2 for BUY / SELL.
      - HIT3B / HIT3S: execute TP3 for BUY / SELL.
      - Standalone HIT: click SL, then Change Order.
      - Keep-awake position is clicked every 60 seconds while monitoring.
    """

    CHANGE_ORDER_DELAY = 0.15
    KEEP_AWAKE_SECONDS = 60
    OCR_POLL_SECONDS = 0.5

    def perform_tp_level(self, side, level):
        with self.action_lock:
            key = f"tp_{side.lower()}{level}"

            if level == 1:
                self.click_point("change_order_trade")
                if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                    return

                self.click_point(key)
                self.log(f"{side} HIT1: Change Order, then TP1.")

            elif level == 2:
                self.click_point(key)
                self.log(f"{side} HIT2: TP2 clicked.")

            elif level == 3:
                self.click_point(key)

                if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                    return

                self.click_point("change_order_exit")
                self.log(f"{side} HIT3: TP3 clicked, then Change Order.")

            self.tp_counts[side] = max(self.tp_counts[side], level)

    def __init__(self, root):
        self.root = root
        self.root.title("Screen Signal & TP Monitor")
        self.root.geometry("720x750")
        self.root.attributes("-topmost", True)

        self.points = {
            "change_order_trade": None,
            "change_order_exit": None,
            "close_all": None,          # NEW: close all positions
            "buy": None,
            "sell": None,
            "tp_buy1": None,
            "tp_buy2": None,
            "tp_buy3": None,
            "tp_sell1": None,
            "tp_sell2": None,
            "tp_sell3": None,
            "sl": None,
            "keep_awake": None,
        }
        self.region = None
        self.current_signal = None
        # Trading clicks stay disabled until a BUY or SELL signal appears.
        self.trade_active = False
        self.running = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.last_keep_awake_click = time.monotonic()

        self.tp_counts = {"BUY": 0, "SELL": 0}
        self.active_markers = set()
        self.action_lock = threading.Lock()

        tk.Label(
            root, text="Screen Signal & TP Monitor",
            font=("Arial", 17, "bold")
        ).pack(pady=(10, 4))

        self.status = tk.Label(
            root, text="Step 1: Select the signal area",
            font=("Arial", 10)
        )
        self.status.pack(pady=4)

        tk.Button(
            root, text="1. Select Monitoring Area",
            command=self.select_area
        ).pack(pady=3)

        point_frame = tk.Frame(root)
        point_frame.pack(pady=5, fill="x", padx=12)

        # Position setup buttons are arranged in two columns.
        point_buttons = [
            ("Change Order (BUY/SELL)", "change_order_trade"),
            ("Change Order (SL/TP3)", "change_order_exit"),
            ("Close All Positions", "close_all"),          # NEW
            ("BUY", "buy"),
            ("SELL", "sell"),
            ("TP Buy 1", "tp_buy1"),
            ("TP Buy 2", "tp_buy2"),
            ("TP Buy 3", "tp_buy3"),
            ("TP Sell 1", "tp_sell1"),
            ("TP Sell 2", "tp_sell2"),
            ("TP Sell 3", "tp_sell3"),
            ("Stop Loss (SL)", "sl"),
            ("Stay Awake", "keep_awake"),
        ]
        for i, (label, name) in enumerate(point_buttons):
            tk.Button(
                point_frame,
                text=f"Mark {label}",
                command=lambda n=name: self.mark_point(n)
            ).grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=3)
        point_frame.grid_columnconfigure(0, weight=1)
        point_frame.grid_columnconfigure(1, weight=1)

        controls = tk.Frame(root)
        controls.pack(pady=7)

        tk.Button(
            controls, text="Start Monitoring", command=self.start_monitoring,
            bg="#16803c", fg="white"
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            controls, text="Stop Monitoring", command=self.stop_monitoring,
            bg="#b42318", fg="white"
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            controls, text="Reset TP Counts", command=self.reset_tp_counts
        ).pack(side=tk.LEFT, padx=5)

        self.output = scrolledtext.ScrolledText(
            root, height=12, wrap=tk.WORD, font=("Consolas", 9)
        )
        self.output.pack(fill="both", expand=True, padx=12, pady=8)

        self.log("Select the monitoring area, then mark all click positions.")
        self.log(
            "OCR markers: BUY, SELL, HIT1B/HIT2B/HIT3B, "
            "HIT1S/HIT2S/HIT3S, and standalone HIT."
        )
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        self.root.after(500, self.select_area)

    def log(self, text):
        """Queue GUI logging safely, including calls from the worker thread."""
        try:
            if self.root.winfo_exists():
                self.root.after(0, self._append_log, text)
        except (RuntimeError, tk.TclError):
            pass

    def _append_log(self, text):
        try:
            if not self.root.winfo_exists():
                return
            self.output.insert(tk.END, text + "\n")
            self.output.see(tk.END)
        except tk.TclError:
            pass

    def select_area(self):
        if self.running:
            messagebox.showwarning(
                "Monitoring active", "Stop monitoring before changing the area."
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
            self.overlay, bg="black", highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            500, 40,
            text="Drag to select the signal area. Press ESC to cancel.",
            fill="white", font=("Arial", 16, "bold")
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
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=3
        )

    def draw_selection(self, event):
        if self.rect is not None:
            self.canvas.coords(
                self.rect, self.start_x, self.start_y, event.x, event.y
            )

    def finish_selection(self, event):
        x1, x2 = sorted((self.start_x, event.x))
        y1, y2 = sorted((self.start_y, event.y))
        self.overlay.destroy()
        self.root.deiconify()

        if x2 - x1 < 5 or y2 - y1 < 5:
            self.log("Selection too small. Select the area again.")
            return

        self.region = {
            "left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1
        }
        self.current_signal = None
        self.active_markers.clear()
        self.tp_counts = {"BUY": 0, "SELL": 0}
        self.status.config(text="Monitoring area selected")
        self.log(f"Monitoring area selected: {self.region}")

    def cancel_selection(self, event=None):
        try:
            self.overlay.destroy()
        except (AttributeError, tk.TclError):
            pass
        self.root.deiconify()
        self.log("Area selection cancelled.")

    def mark_point(self, name):
        if self.running:
            messagebox.showwarning(
                "Monitoring active", "Stop monitoring before marking positions."
            )
            return
        if self.region is None:
            messagebox.showwarning(
                "Select area first", "Please select the monitoring area first."
            )
            return

        labels = {
            "change_order_trade": "CHANGE ORDER (BUY/SELL)",
            "change_order_exit": "CHANGE ORDER (SL/TP3)",
            "close_all": "CLOSE ALL POSITIONS",          # NEW
            "buy": "BUY",
            "sell": "SELL",
            "tp_buy1": "TP BUY 1",
            "tp_buy2": "TP BUY 2",
            "tp_buy3": "TP BUY 3",
            "tp_sell1": "TP SELL 1",
            "tp_sell2": "TP SELL 2",
            "tp_sell3": "TP SELL 3",
            "sl": "STOP LOSS",
            "keep_awake": "STAY AWAKE",
        }
        messagebox.showinfo(
            "Mark " + labels[name],
            "Click OK, then click the desired screen position for "
            + labels[name] + ".\n\nPress ESC to cancel."
        )

        self.root.withdraw()
        self.point_overlay = tk.Toplevel(self.root)
        self.point_overlay.attributes("-fullscreen", True)
        self.point_overlay.attributes("-topmost", True)
        self.point_overlay.attributes("-alpha", 0.15)
        self.point_overlay.configure(bg="black")
        self.point_overlay.config(cursor="crosshair")

        canvas = tk.Canvas(
            self.point_overlay, bg="black", highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)
        canvas.create_text(
            500, 40, text=f"Click the screen location for {labels[name]}",
            fill="white", font=("Arial", 16, "bold")
        )
        self.point_overlay.bind(
            "<Button-1>",
            lambda event: self.save_point(name, event.x_root, event.y_root)
        )
        self.point_overlay.bind("<Escape>", self.cancel_point)
        self.point_overlay.focus_force()

    def save_point(self, name, x, y):
        self.points[name] = (x, y)
        self.point_overlay.destroy()
        self.root.deiconify()
        self.log(f"{name} saved at X={x}, Y={y}")
        missing = [key for key, value in self.points.items() if value is None]
        if missing:
            self.status.config(text=f"Positions remaining: {len(missing)}")
        else:
            self.status.config(text="All positions saved. Ready to monitor.")
            self.log("All click positions are ready.")

    def cancel_point(self, event=None):
        try:
            self.point_overlay.destroy()
        except (AttributeError, tk.TclError):
            pass
        self.root.deiconify()
        self.log("Position marking cancelled.")

    def reset_tp_counts(self):
        self.tp_counts = {"BUY": 0, "SELL": 0}
        self.active_markers.clear()
        self.log("TP counters reset: Buy=0, Sell=0.")

    def start_monitoring(self):
        if self.running:
            return
        if self.region is None:
            messagebox.showwarning("Missing area", "Select a monitoring area first.")
            return
        missing = [key for key, value in self.points.items() if value is None]
        if missing:
            messagebox.showwarning(
                "Missing positions",
                "Mark every position before starting:\n" + ", ".join(missing)
            )
            return

        self.running = True
        self.stop_event.clear()
        self.current_signal = None
        self.active_markers.clear()
        self.last_keep_awake_click = time.monotonic()
        self.status.config(text="Monitoring is running")
        self.log("Monitoring started.")

        # Ask Windows to prevent automatic sleep while monitoring.
        try:
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetThreadExecutionState(
                    0x80000000 | 0x00000001
                )
        except Exception as error:
            self.log(f"Windows keep-awake request unavailable: {error}")

        self.monitor_thread = threading.Thread(
            target=self.monitor_loop, daemon=True
        )
        self.monitor_thread.start()
        self.root.after(1000, self.keep_awake_loop)

    def monitor_loop(self):
        try:
            with mss.mss() as screen:
                while not self.stop_event.is_set():
                    screenshot = screen.grab(self.region)
                    image = Image.frombytes(
                        "RGB", screenshot.size, screenshot.rgb
                    )
                    image = image.resize(
                        (image.width * 2, image.height * 2)
                    )
                    text = pytesseract.image_to_string(
                        image, config="--psm 6"
                    ).strip()
                    self.root.after(
                        0, lambda captured=text: self.process_ocr(captured)
                    )
                    self.stop_event.wait(self.OCR_POLL_SECONDS)
        except Exception as error:
            self.root.after(0, lambda e=str(error): self.monitor_error(e))

    @staticmethod
    def has_word(text, word):
        return bool(re.search(rf"\b{re.escape(word)}\b", text))

    def process_ocr(self, text):
        if not self.running:
            return

        upper = text.upper()

        has_buy = self.has_word(upper, "BUY")
        has_sell = self.has_word(upper, "SELL")

        # Detect each TP level and trade direction separately.
        tp_markers = {
            "HIT1B": ("BUY", 1),
            "HIT2B": ("BUY", 2),
            "HIT3B": ("BUY", 3),
            "HIT1S": ("SELL", 1),
            "HIT2S": ("SELL", 2),
            "HIT3S": ("SELL", 3),
        }

        visible_markers = {
            marker
            for marker in tp_markers
            if self.has_word(upper, marker)
        }

        # Standalone HIT indicates SL, not a TP marker.
        has_hit = self.has_word(upper, "HIT")

        signal = "BUY" if has_buy and not has_sell else (
            "SELL" if has_sell and not has_buy else None
        )

        # Only a BUY/SELL signal may activate the trading click sequence.
        # SL/TP text alone must never start a new sequence.
        if signal is not None and (not self.trade_active or signal != self.current_signal):
            self.log(f"Trade signal detected: {signal}; enabling trading clicks.")
            self.perform_trade(signal)
            self.current_signal = signal
            self.trade_active = True

        # Track marker visibility even while inactive, so old SL/TP text does
        # not trigger later just because a BUY/SELL signal appears.
        if has_hit:
            visible_markers.add("HIT")

        new_markers = visible_markers - self.active_markers
        self.active_markers = visible_markers

        # Ignore every SL/TP click until a BUY or SELL signal has activated us.
        if not self.trade_active:
            return

        # Process SL before TP markers if both appear together.
        if "HIT" in new_markers:
            self.perform_sl()
            self.trade_active = False
            self.current_signal = None
            self.active_markers.clear()
            return

        # Each TP marker directly selects its corresponding button.
        for marker, (side, level) in tp_markers.items():
            if marker in new_markers:
                self.perform_tp_level(side, level)

    def perform_trade(self, side):
        with self.action_lock:
            # If a trade is already active, close all positions first
            if self.trade_active:
                self.click_point("close_all")
                self.log(f"Closing all positions before new {side} signal.")
                if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                    return

                # Also click Change Order (SL/TP3) after Close All
                self.click_point("change_order_exit")
                self.log("Change Order (SL/TP3) clicked after Close All.")
                if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                    return

            trade_key = "buy" if side == "BUY" else "sell"
            self.click_point(trade_key)
            if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                return
            self.click_point("change_order_trade")
            self.log(f"{side}: trade clicked, then Change Order.")

    def perform_tp(self, side):
        with self.action_lock:
            self.tp_counts[side] += 1
            level = self.tp_counts[side]

            if level > 3:
                self.log(f"{side} TP marker detected, but all 3 TP levels are used.")
                self.tp_counts[side] = 3
                return

            key = f"tp_{side.lower()}{level}"
            if level == 1:
                # TP1 needs Change Order and then the TP click.
                self.click_point("change_order_trade")
                if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                    return
                self.click_point(key)
                self.log(f"{side} TP1: Change Order, then TP1.")
            elif level == 2:
                self.click_point(key)
                self.log(f"{side} TP2 clicked.")
            else:
                self.click_point(key)
                if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                    return
                self.click_point("change_order_exit")
                self.log(f"{side} TP3 clicked, then Change Order.")

    def perform_sl(self):
        with self.action_lock:
            self.click_point("sl")
            if self.stop_event.wait(self.CHANGE_ORDER_DELAY):
                return
            self.click_point("change_order_exit")
            self.log("SL detected: SL clicked, then Change Order.")
            # A stop-loss ends the current TP sequence for both sides.
            self.tp_counts = {"BUY": 0, "SELL": 0}

    def keep_awake_loop(self):
        if not self.running:
            return
        now = time.monotonic()
        if now - self.last_keep_awake_click >= self.KEEP_AWAKE_SECONDS:
            self.click_point("keep_awake")
            self.last_keep_awake_click = now
            self.log("Stay-awake position clicked.")
        self.root.after(1000, self.keep_awake_loop)

    def click_point(self, name):
        position = self.points.get(name)
        if position is None:
            self.log(f"Click skipped: position '{name}' is not configured.")
            return
        try:
            pyautogui.click(position[0], position[1])
            self.log(f"Clicked {name}: {position}")
        except Exception as error:
            self.log(f"Click failed at {name}: {error}")
            self.stop_monitoring()

    def monitor_error(self, error):
        self.log(f"Monitoring error: {error}")
        self.stop_monitoring()

    def stop_monitoring(self):
        self.running = False
        self.stop_event.set()
        try:
            if sys.platform == "win32":
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception:
            pass
        try:
            self.status.config(text="Monitoring stopped")
        except tk.TclError:
            pass
        self.log("Monitoring stopped.")

    def close_app(self):
        self.stop_monitoring()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenTextReader(root)
    root.mainloop()