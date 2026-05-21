#!/usr/bin/env python3
import os
import time
import json
import ctypes
import re
import threading
from ctypes import wintypes
from tempfile import NamedTemporaryFile

# ================== PATH CONFIG ==================
# File:
# VISTA\Agent\src\analysis_modules\cheating_analysis\raw_data_collector.py
# Move up 4 levels to reach VISTA

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

OCR_DIR = os.path.join(BASE_DIR, "assets", "ocr_texts")
SCREEN_LOG_FILE = os.path.join(BASE_DIR, "assets", "logs", "screen_detect.log")
KEYLOG_FILE = os.path.join(BASE_DIR, "assets", "logs", "keylog.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "raw_data_for_analysis")

POLL_INTERVAL = 3
LAST_SCREEN_LINES = 10
LAST_KEYLOG_CHARS = 400

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OCR_DIR, exist_ok=True)

# ================== THREAD CONTROL ==================

_stop_event = threading.Event()
_worker_thread = None

# ================== CLIPBOARD CODE ==================

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CF_UNICODETEXT = 13

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL


def get_clipboard_text():
    try:
        if not user32.OpenClipboard(None):
            return ""
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    except Exception:
        return ""
    finally:
        try:
            user32.CloseClipboard()
        except Exception:
            pass

# ================== FILE HELPERS ==================

def read_file_safe(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def tail_last_n_lines(path, n):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            block = 4096
            data = b""
            while pos > 0 and data.count(b"\n") <= n:
                read_size = min(block, pos)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size) + data
            return data.decode("utf-8", errors="replace").splitlines()[-n:]
    except Exception:
        return []


def extract_keylog_text(path, n):
    if not os.path.exists(path):
        return ""
    raw = read_file_safe(path)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "txt" in parsed:
            return parsed["txt"][-n:]
    except Exception:
        pass
    return raw[-n:]

# ================== OCR SANITIZER ==================

def sanitize_ocr_text(text):
    if not text:
        return ""
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = text.replace("\\", " ")
    text = re.sub(r"[^\x20-\x7E]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ================== ATOMIC WRITE ==================

def atomic_json_write(path, payload):
    with NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=os.path.dirname(path)) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        temp_name = tmp.name
    os.replace(temp_name, path)

# ================== CORE PROCESS ==================

def process_txt_file(txt_path):
    base = os.path.basename(txt_path)
    json_name = os.path.splitext(base)[0] + ".json"
    out_path = os.path.join(OUTPUT_DIR, json_name)

    try:
        if os.path.exists(out_path):
            if os.path.getmtime(out_path) >= os.path.getmtime(txt_path):
                return
    except Exception:
        pass

    ocr_text = sanitize_ocr_text(read_file_safe(txt_path))
    screen_log = "\n".join(tail_last_n_lines(SCREEN_LOG_FILE, LAST_SCREEN_LINES))
    keylog = extract_keylog_text(KEYLOG_FILE, LAST_KEYLOG_CHARS)
    clipboard = get_clipboard_text()

    payload = {
        "data": {
            "ocr_text": ocr_text,
            "screen_log": screen_log,
            "keylog": keylog,
            "clipboard": clipboard
        }
    }

    atomic_json_write(out_path, payload)
    print(f"[RAW_DATA] processed -> {json_name}")

# ================== WORKER LOOP ==================

def _collector_loop():
    processed = {}
    while not _stop_event.is_set():
        try:
            files = sorted(f for f in os.listdir(OCR_DIR) if f.lower().endswith(".txt"))
            for fname in files:
                full = os.path.join(OCR_DIR, fname)
                try:
                    mtime = os.path.getmtime(full)
                except Exception:
                    continue

                if fname not in processed or processed[fname] != mtime:
                    process_txt_file(full)
                    processed[fname] = mtime

            _stop_event.wait(POLL_INTERVAL)

        except Exception as e:
            print("[RAW_DATA ERROR]", e)
            time.sleep(1)

# ================== PUBLIC API ==================

def start_raw_data_collector():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_collector_loop,
        name="RawDataCollector",
        daemon=True
    )
    _worker_thread.start()
    print("[RAW_DATA] started")


def stop_raw_data_collector():
    _stop_event.set()
    if _worker_thread:
        _worker_thread.join(timeout=5)
    print("[RAW_DATA] stopped")

# ================== ENTRY ==================

if __name__ == "__main__":
    start_raw_data_collector()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_raw_data_collector()
