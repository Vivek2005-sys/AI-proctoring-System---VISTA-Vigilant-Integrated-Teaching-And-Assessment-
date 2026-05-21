import ctypes
import ctypes.wintypes as wintypes
import win32gui
import threading


def start_usb_watcher(on_connect, on_disconnect):
    """
    Starts USB watcher in background.
    Calls:
      - on_connect()    when a USB storage device is connected
      - on_disconnect() when it is removed
    """

    WM_DEVICECHANGE = 0x0219
    DBT_DEVICEARRIVAL = 0x8000
    DBT_DEVICEREMOVECOMPLETE = 0x8004
    DBT_DEVTYP_VOLUME = 0x0002

    class DEV_BROADCAST_HDR(ctypes.Structure):
        _fields_ = [
            ("size", wintypes.DWORD),
            ("type", wintypes.DWORD),
            ("reserved", wintypes.DWORD),
        ]

    def watcher_thread():
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_DEVICECHANGE and lparam:
                hdr = ctypes.cast(
                    lparam, ctypes.POINTER(DEV_BROADCAST_HDR)
                ).contents

                if hdr.type == DBT_DEVTYP_VOLUME:
                    if wparam == DBT_DEVICEARRIVAL:
                        on_connect()
                    elif wparam == DBT_DEVICEREMOVECOMPLETE:
                        on_disconnect()

            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

        wc = win32gui.WNDCLASS()
        wc.lpszClassName = "USBWatcher"
        wc.lpfnWndProc = wnd_proc
        atom = win32gui.RegisterClass(wc)

        win32gui.CreateWindow(
            atom, None, 0, 0, 0, 0, 0, 0, 0, 0, None
        )

        win32gui.PumpMessages()  # blocks inside thread forever

    threading.Thread(target=watcher_thread, daemon=True).start()

# 🧠 Flow of Execution

# ctypes sets up WinAPI access
# Python gains the ability to read raw Windows event data.

# You define the Windows device header struct
# This matches what Windows sends when a device changes.

# You create a window callback (wnd_proc)
# Windows will call this function when something happens.

# You register a hidden window class
# This tells Windows which function to notify.

# You create an invisible window
# Required — Windows only sends device events to windows.

# You enter the message loop (PumpMessages)
# Your script goes idle and waits. No polling, no CPU waste.

# USB is plugged in or removed
# Windows sends WM_DEVICECHANGE to your window.

# wnd_proc is called by Windows
# ctypes reads the raw event data.

# State is updated

# Insert → connected = True

# Remove → connected = False

