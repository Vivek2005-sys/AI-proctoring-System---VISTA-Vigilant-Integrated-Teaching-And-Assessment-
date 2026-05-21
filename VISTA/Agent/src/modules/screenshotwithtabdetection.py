import threading
import time
from datetime import datetime
from mss import mss
from PIL import Image
from io import BytesIO
import os
import ctypes
from ctypes import wintypes
import json

# ================= CONFIG =================

PC_NO = "00"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Path to VISTA directory
VISTA_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

LOG_DIR = os.path.join(VISTA_DIR, "assets", "logs")
LOG_FILE = os.path.join(LOG_DIR, "screen_detect.log")
os.makedirs(LOG_DIR, exist_ok=True)

SS_DIR = os.path.join(VISTA_DIR, "assets", "images", "agent_ss")
OCR_DIR = os.path.join(VISTA_DIR, "assets", "images", "ss_for_ocr")

SS_INTERVAL = 1.0       # normal screenshots
OCR_INTERVAL = 5.0      # OCR screenshots

# ================= WIN32 SETUP (UNCHANGED LOGIC) =================

user32 = ctypes.windll.user32
last_hwnd = None

# ================= STATE =================

_running = False
_thread = None
_last_thumbnail = None

last_ss_time = 0
last_ocr_time = 0

# ================= SCREEN CHANGE STATE =================

STATE_DIR = os.path.join(BASE_DIR, "state")
STATE_FILE = os.path.join(STATE_DIR, "screen_state.json")
os.makedirs(STATE_DIR, exist_ok=True)

screen_change_count = 0


def write_screen_change_state():
    data = {
        "screen_change_count": screen_change_count,
        "last_update": datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= HELPERS =================

def get_foreground_hwnd():
    hwnd = user32.GetForegroundWindow()
    return hwnd


def save_screenshot(img, folder):
    timestamp = datetime.now().strftime("%d-%m-%y_%H-%M-%S")
    filename = f"PC-{PC_NO}_{timestamp}.png"
    path = os.path.join(folder, filename)
    img.save(path, "PNG")

# ================= MAIN CAPTURE LOOP =================

def _capture_loop():
    global last_hwnd, last_ss_time, last_ocr_time, _last_thumbnail
    global screen_change_count

    with mss() as sct:
        monitor = sct.monitors[0]

        while _running:
            start = time.monotonic()
            now = time.time()

            try:
                hwnd = get_foreground_hwnd()
                app_switched = False

                if hwnd and hwnd != last_hwnd:
                    screen_change_count += 1
                    last_hwnd = hwnd

                    ts = datetime.now().strftime("%d-%m-%y %H:%M:%S")
                    log_line = (
                        f"[screen_detect] App switch detected "
                        f"(count={screen_change_count},{ts})\n"
                    )

                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(log_line)

                    write_screen_change_state()
                    app_switched = True

                frame = sct.grab(monitor)
                img = Image.frombytes("RGB", frame.size, frame.rgb)

                # ---------------- NORMAL SS (1s) ----------------
                if now - last_ss_time >= SS_INTERVAL:
                    save_screenshot(img, SS_DIR)
                    last_ss_time = now

                # ---------------- OCR SS (5s) ----------------
                if now - last_ocr_time >= OCR_INTERVAL:
                    save_screenshot(img, OCR_DIR)
                    last_ocr_time = now

                # ---------------- APP SWITCH TRIGGER ----------------
                if app_switched:
                    save_screenshot(img, SS_DIR)
                    save_screenshot(img, OCR_DIR)

                # Thumbnail (unchanged behavior)
                thumb = img.resize((500, 350))
                buf = BytesIO()
                thumb.save(buf, "png", quality=50)
                _last_thumbnail = buf.getvalue()

            except Exception as e:
                print(f"[screenshots] Error:", e)

            time.sleep(max(0, 0.1 - (time.monotonic() - start)))

# ================= PUBLIC API =================

def start():
    global _running, _thread

    if _running:
        return False

    _running = True
    _thread = threading.Thread(
        target=_capture_loop,
        name="ScreenshotWorker",
        daemon=True
    )
    _thread.start()

    print("[screenshots] Screenshot worker started")
    return True


def stop():
    global _running
    _running = False
    print("[screenshots] Screenshot worker stopped")


def is_alive():
    return _thread is not None and _thread.is_alive()


def get_thumbnail():
    return _last_thumbnail or b""


def run_foreground():
    start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()

# ================= ENTRYPOINT =================

if __name__ == "__main__":
    run_foreground()
