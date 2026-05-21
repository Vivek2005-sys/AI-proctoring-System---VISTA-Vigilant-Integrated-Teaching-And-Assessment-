import asyncio
import websockets
import json
import threading
import time

# ===== IMPORT YOUR MODULES =====
from modules.app_and_process_blocker import process_blocker
from modules.broadcast import fullscreen_image_slideshow
from modules.input_blocker import block_input_15min
from modules.external_device_detector import start_usb_watcher
from modules.keylog import start_keyboard_logger as _start_keyboard_logger
from modules.screenshotwithtabdetection import (
    start as _start_screen,
    stop as _stop_screen,
    is_alive as screen_is_alive
)

from analysis_modules.ocr.ocr import start_ocr_service
from analysis_modules.cheating_analysis.raw_data_collector import (
    start_raw_data_collector,
    stop_raw_data_collector
)

# ===== THREAD REGISTRY =====
threads = {}

# ===== START FUNCTIONS =====
def start_thread(name, target, kwargs=None):
    if name in threads and threads[name].is_alive():
        print(f"[WS] {name} already running")
        return

    t = threading.Thread(target=target, kwargs=kwargs or {}, daemon=True)
    t.start()
    threads[name] = t
    print(f"[WS] started {name}")


def stop_thread(name):
    print(f"[WS] stop requested for {name} (implement stop logic if needed)")


# ===== MODULE HANDLERS =====
def handle_start(module):
    if module == "process_blocker":
        start_thread("process_blocker", process_blocker, {
            "blocked": {"chrome.exe", "firefox.exe", "msedge.exe"},
            "scan_interval": 0.4
        })

    elif module == "slideshow":
        start_thread("slideshow", fullscreen_image_slideshow, {
            "image_dir": r"C:\coding\FP Project\images",
            "change_interval_ms": 1000,
            "folder_scan_interval_ms": 2000,
        })

    elif module == "input_blocker":
        start_thread("input_blocker", block_input_15min)

    elif module == "usb":
        start_usb_watcher(on_usb_connected, on_usb_disconnected)

    elif module == "keyboard":
        start_thread("keyboard", _start_keyboard_logger)

    elif module == "screen":
        start_thread("screen", _start_screen)

    elif module == "ocr":
        start_thread("ocr", start_ocr_service)

    elif module == "raw":
        start_thread("raw", start_raw_data_collector)


def handle_stop(module):
    if module == "screen":
        _stop_screen()

    elif module == "raw":
        stop_raw_data_collector()

    else:
        stop_thread(module)


# ===== USB CALLBACKS =====
def on_usb_connected():
    print("[USB] connected")


def on_usb_disconnected():
    print("[USB] disconnected")


# ===== WEBSOCKET CLIENT =====
async def ws_client():
    uri = "ws://localhost:8765"

    while True:
        try:
            async with websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=20
            ) as ws:

                print("[WS] Connected to server")

                # 🔥 SEND ROLE IMMEDIATELY (CRITICAL FIX)
                await ws.send(json.dumps({"role": "agent"}))
                print("[WS] Role sent as AGENT")

                while True:
                    try:
                        msg = await ws.recv()
                        data = json.loads(msg)

                        action = data.get("action")
                        module = data.get("module")

                        print(f"[WS] Received: {data}")

                        if action == "start":
                            handle_start(module)

                        elif action == "stop":
                            handle_stop(module)

                        elif action == "status":
                            status = {
                                name: t.is_alive()
                                for name, t in threads.items()
                            }
                            await ws.send(json.dumps(status))

                    except websockets.ConnectionClosed:
                        print("[WS] Connection closed by server")
                        break

        except Exception as e:
            print(f"[WS] Disconnected: {e}")

        # 🔁 RECONNECT DELAY
        await asyncio.sleep(3)


# ===== MAIN =====
if __name__ == "__main__":
    print("[WS CLIENT] Starting...")
    asyncio.run(ws_client())