import os
import tkinter as tk
from PIL import Image, ImageTk


def fullscreen_image_slideshow(
    image_dir,
    change_interval_ms=1000,
    folder_scan_interval_ms=2000,
    supported_ext=(".png", ".jpg", ".jpeg", ".bmp"),
):
    """
    Fullscreen slideshow that watches a folder and displays new images.

    :param image_dir: folder path to watch
    :param change_interval_ms: time per image
    :param folder_scan_interval_ms: how often to rescan folder
    :param supported_ext: allowed image extensions
    """

    if not os.path.isdir(image_dir):
        raise ValueError(f"Invalid folder path: {image_dir}")

    # ---------- TK SETUP ----------
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.configure(bg="black")
    root.bind("<Escape>", lambda e: root.destroy())

    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    label = tk.Label(root, bg="black")
    label.pack(fill="both", expand=True)

    # ---------- STATE ----------
    shown_files = set()
    pending_files = []
    current_image = None  # prevent GC

    # ---------- HELPERS ----------
    def scan_folder():
        nonlocal pending_files

        files = []
        for f in os.listdir(image_dir):
            if f.lower().endswith(supported_ext):
                full_path = os.path.join(image_dir, f)
                if full_path not in shown_files:
                    files.append(full_path)

        files.sort(key=os.path.getmtime)

        if files:
            pending_files.extend(files)

        root.after(folder_scan_interval_ms, scan_folder)

    def show_next_image():
        nonlocal current_image

        if not pending_files:
            root.after(500, show_next_image)
            return

        path = pending_files.pop(0)
        shown_files.add(path)

        try:
            img = Image.open(path).convert("RGB")
            img = img.resize((screen_w, screen_h), Image.LANCZOS)
            current_image = ImageTk.PhotoImage(img)
            label.config(image=current_image)
        except Exception as e:
            print(f"Failed to load {path}: {e}")

        root.after(change_interval_ms, show_next_image)

    # ---------- START ----------
    scan_folder()
    show_next_image()
    root.mainloop()
