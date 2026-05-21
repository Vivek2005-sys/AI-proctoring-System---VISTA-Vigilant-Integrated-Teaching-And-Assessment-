import ctypes
import time
import sys


def block_input_15min():
    """
    Blocks keyboard + mouse input.
    Auto-restores after 15 minutes or if process is killed.
    No parameters. No external timer.
    """

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    # -------- APIs --------
    BlockInput = user32.BlockInput
    BlockInput.argtypes = [ctypes.c_bool]
    BlockInput.restype = ctypes.c_bool

    ClipCursor = user32.ClipCursor
    ClipCursor.argtypes = [ctypes.c_void_p]
    ClipCursor.restype = ctypes.c_bool

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    # confine cursor to 1px box
    rect = RECT(0, 0, 1, 1)

    # 15 minutes hard limit
    END_TIME = time.monotonic() + (1* 60)

    if not BlockInput(True):
        raise PermissionError("BlockInput failed — run as Administrator")

    try:
        print("[+] Input blocked (15 min max)")

        while time.monotonic() < END_TIME:
            # BlockInput is global but ClipCursor can be lost → reapply both
            BlockInput(True)
            ClipCursor(ctypes.byref(rect))
            time.sleep(2)

    finally:
        # ABSOLUTE GUARANTEE restore
        ClipCursor(None)
        BlockInput(False)
        print("[+] Input restored")


