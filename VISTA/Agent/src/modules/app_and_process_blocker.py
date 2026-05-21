import ctypes
from ctypes import wintypes
import os
import sys
import time


def process_blocker(blocked, scan_interval=0.4):
  

    blocked = {p.casefold() for p in blocked}
    self_pid = os.getpid()

    # ---------- Admin check ----------
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise PermissionError("Run as Administrator")

    # ---------- Win32 constants ----------
    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_TERMINATE = 0x0001

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint32

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ULONG_PTR),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.CHAR * 260),
        ]

    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

    kernel32.Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]
    kernel32.Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE

    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    # ---------- helpers ----------
    def kill_process(pid):
        if pid <= 4 or pid == self_pid:
            return
        h = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if h:
            kernel32.TerminateProcess(h, 1)
            kernel32.CloseHandle(h)

    def scan_and_kill():
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == wintypes.HANDLE(-1).value:
            return

        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(entry)

        ok = kernel32.Process32First(snapshot, ctypes.byref(entry))
        while ok:
            pid = entry.th32ProcessID
            name = (
                bytes(entry.szExeFile)
                .split(b"\x00", 1)[0]
                .decode(errors="ignore")
                .casefold()
            )

            if name in blocked:
                kill_process(pid)

            ok = kernel32.Process32Next(snapshot, ctypes.byref(entry))

        kernel32.CloseHandle(snapshot)

    # ---------- main loop ----------
    print("[+] Process blocker started")
    print("[+] Blocked:", blocked)

    while True:
        scan_and_kill()
        time.sleep(scan_interval)





# WORKFLOW
# Program launch

# Python script starts execution.

# The current process ID (SELF_PID) is captured so the program does not kill itself.

# Administrator privilege verification

# Windows API IsUserAnAdmin() is called.

# If the program is NOT running as Administrator:

# Execution stops immediately.

# No monitoring or killing logic runs.

# If Administrator:

# Program continues.

# Configuration load

# A fixed in-memory set of blocked executable names is loaded.

# Names are lowercase and compared case-insensitively.

# Scan interval is defined (example: 0.4 seconds).

# Windows API preparation

# Kernel32.dll is loaded once.

# Required Windows constants are defined.

# PROCESSENTRY32 structure is defined to exactly match the Windows SDK layout.

# Function signatures are declared so ctypes does not guess types.

# This prevents crashes and memory corruption.

# Initial full process scan (critical step)

# CreateToolhelp32Snapshot is called with TH32CS_SNAPPROCESS.

# Windows returns a snapshot of ALL currently running processes.

# This snapshot is static and safe to iterate.

# Snapshot iteration

# Process32First is called to get the first process entry.

# Process32Next is repeatedly called to iterate through all processes.

# For each process:

# Process ID (PID) is read.

# Executable name is extracted from szExeFile.

# Name is decoded, stripped of null bytes, and converted to lowercase.

# Initial termination pass

# Each process name is checked against the blocked list.

# If a match is found:

# OpenProcess(PROCESS_TERMINATE) is called.

# If a valid handle is returned:

# TerminateProcess is executed immediately.

# Handle is closed to prevent leaks.

# This step kills all blocked processes that were already running before the script started.

# Initial scan completion

# Snapshot handle is closed.

# At this point:

# No blocked applications should be running.

# Continuous monitoring loop starts

# The script enters an infinite loop.

# This loop is responsible for killing newly launched processes.

# Periodic rescan

# On every loop iteration:

# A new process snapshot is created.

# The full process list is scanned again.

# This is NOT event-based.

# This is intentional for stability and predictability.

# New process detection (implicit)

# Any process that appears in the snapshot:

# Is evaluated immediately.

# There is no need to track “new vs old” explicitly.

# If a blocked process exists at scan time:

# It is killed, regardless of when it started.

# Repeated enforcement

# If a blocked application restarts itself:

# It will be killed again in the next scan cycle.

# If a user launches a blocked app manually:

# It will live only until the next scan (usually < 0.5s).

# CPU efficiency behavior

# Toolhelp snapshots are lightweight.

# The script sleeps between scans.

# CPU usage remains low and stable.

# No busy-waiting occurs.

# Error containment

# If a process exits between snapshot and termination:

# OpenProcess fails silently.

# Script continues without crashing.

# If access is denied:

# Process is skipped.

# Next scan may still catch it.

# Long-running stability

# No COM objects are used.

# No WMI queries are used.

# No callbacks or blocking API calls exist.

# Script can run for hours or days without degradation.

# Exit conditions

# Script runs indefinitely.

# It only stops if:

# Manually terminated

# System shuts down

# Python process crashes (unlikely with this design)