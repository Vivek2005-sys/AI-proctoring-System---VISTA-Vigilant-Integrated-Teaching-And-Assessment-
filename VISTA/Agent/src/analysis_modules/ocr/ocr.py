import os
import time
import shutil
from PIL import Image
import pytesseract


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

INPUT_DIR = os.path.join(BASE_DIR, "assets", "images", "ss_for_ocr")
PROCESSED_DIR = os.path.join(INPUT_DIR, "processed")
TEMP_DIR = os.path.join(
    BASE_DIR, "Agent", "src", "analysis_modules", "ocr", "temp"
)
OCR_TEXT_DIR = os.path.join(BASE_DIR, "assets", "ocr_texts")

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

CROP_TOP = 35
CROP_BOTTOM = 50
CROP_LEFT = 90
CROP_RIGHT = 90

SLEEP_SECONDS = 5

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

for d in (INPUT_DIR, PROCESSED_DIR, TEMP_DIR, OCR_TEXT_DIR):
    os.makedirs(d, exist_ok=True)

OCR_CONFIG = "--oem 3 --psm 6 -l eng"

# =========================
# FUNCTIONS
# =========================

def crop_image(input_path, output_path):
    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        w, h = img.size

        cropped = img.crop((
            CROP_LEFT,
            CROP_TOP,
            w - CROP_RIGHT,
            h - CROP_BOTTOM
        ))

        cropped.save(output_path, format="PNG")


def run_ocr(image_path):
    img = Image.open(image_path)
    start = time.perf_counter()
    text = pytesseract.image_to_string(img, config=OCR_CONFIG)
    end = time.perf_counter()
    return text.strip(), (end - start) * 1000


# =========================
# SERVICE LOOP
# =========================

def start_ocr_service():
    print("[OCR] Service started")

    while True:
        png_files = [
            f for f in os.listdir(INPUT_DIR)
            if f.lower().endswith(".png")
            and os.path.isfile(os.path.join(INPUT_DIR, f))
        ]

        if not png_files:
            time.sleep(SLEEP_SECONDS)
            continue

        for filename in png_files:
            base_name = os.path.splitext(filename)[0]

            input_path = os.path.join(INPUT_DIR, filename)
            temp_path = os.path.join(TEMP_DIR, base_name + ".png")
            text_path = os.path.join(OCR_TEXT_DIR, base_name + ".txt")
            processed_path = os.path.join(PROCESSED_DIR, filename)

            if os.path.exists(text_path):
                continue

            try:
                crop_image(input_path, temp_path)

                text, ocr_time = run_ocr(temp_path)

                with open(text_path, "w", encoding="utf-8") as f:
                    f.write(text)

                print(f"[META] FILE={filename} | OCR_TIME_MS={ocr_time:.2f}")

                os.remove(temp_path)
                shutil.move(input_path, processed_path)

                print(f"[OK] {filename}")

            except Exception as e:
                print(f"[ERROR] {filename} -> {e}")

                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass

        time.sleep(SLEEP_SECONDS)


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    start_ocr_service()
