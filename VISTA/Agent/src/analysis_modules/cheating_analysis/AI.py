import os
import json
import time
import re
import shutil
import threading
from datetime import datetime
from llama_cpp import Llama
from concurrent.futures import ThreadPoolExecutor

# =========================================================
# MODEL SETUP

# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "../../gemma-2-2b-it-Q3_K_L.gguf")
CPU_THREADS = os.cpu_count()

print("[AI] Loading Gemma model...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=720,
    n_threads=CPU_THREADS
)
print("[AI] Model Loaded")

llm_lock = threading.Lock()

# =========================================================
# PATH SETUP
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

for _ in range(4):
    BASE_DIR = os.path.dirname(BASE_DIR)

RAW_DATA_DIR = os.path.join(BASE_DIR, "assets", "raw_data_for_analysis")
AI_OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "ai_decisions")
LATEST_DECISION_FILE = os.path.join(AI_OUTPUT_DIR, "latest_decision.json")

os.makedirs(AI_OUTPUT_DIR, exist_ok=True)

# =========================================================
# HARD SIGNAL CHECK (Minimal Rule Layer)
# =========================================================

def hard_signal_check(ocr, clipboard, switches_per_min):

    ocr_lower = ocr.lower()
    ocr_norm = ocr_lower.replace(".", "").replace(" ", "")
    clipboard_lower = clipboard.lower()

    # -------------------------
    # Screen Switching
    # -------------------------
    if switches_per_min > 20:
        return {
            "risk": "WARNING",
            "confidence": 0.8,
            "reasons": ["Excessive screen switching detected"]
        }

    # --------------------------
    # External AI Websites (Hard FLAG)
    # --------------------------
    external_ai_keywords = [
        "chatgpt",
        "chatgptcom",
        "chatopenai",
        "perplexity",
        "grok",
        "claude"
    ]

    if any(k in ocr_norm for k in external_ai_keywords):
        return {
            "risk": "FLAG",
            "confidence": 0.95,
            "reasons": ["Unauthorized external AI platform detected"]
        }

    # --------------------------
    # Colab Gemini Handling
    # --------------------------
    is_colab = "colabresearchgooglecom" in ocr_norm
    has_gemini = "gemini" in ocr_norm

    if is_colab and has_gemini:

        gemini_active_signals = [
            "pleaseexplainthiserror",
            "error",
            "accept"
            "accep trun",
            "sureheres",
            "tofixthis",
            "theerrormeans",
            "heresthecode",
            "accept&run"
        ]

        if any(signal in ocr_norm for signal in gemini_active_signals):
            return {
                "risk": "FLAG",
                "confidence": 0.9,
                "reasons": ["Gemini AI panel actively used in Colab"]
            }

        return None  # passive Gemini UI allowed

    # -------------------------
    # Clipboard Logic 
    # -------------------------

    # External links in clipboard (hardened detection)

    clipboard_text = clipboard.strip().lower()

    # Detect real HTTP/HTTPS URLs
    url_pattern = r'https?://[^\s]+'


    # Detect real document extensions (as full words, not substrings inside code)
    file_pattern = r'\b[^\s]+\.(pdf|docx|xlsx)\b'

    # Only treat as suspicious if:
    # 1) A real URL exists OR a real document file is referenced
    # 2) Clipboard is relatively short (likely a copied link, not full source code)
    if (
        (re.search(url_pattern, clipboard_text) or re.search(file_pattern, clipboard_text))
        and len(clipboard_text) < 500
    ):
        return {
            "risk": "WARNING",
            "confidence": 0.8,
            "reasons": ["External link or document detected in clipboard"]
        }

    return None


# =========================================================
# LLM INTENT CLASSIFIER
# =========================================================

def call_llm_classifier(ocr, keylog):

    prompt = f"""
You are an academic integrity classifier.

Your job is to determine whether a student is seeking help from an AI.

IMPORTANT RULES:
- Normal coding syntax is NOT cheating.
- Import statements are normal.
- Error tracebacks are normal.
- VS Code welcome screen is normal.
- R scripts are normal.
- Only classify FLAG if clear AI help-seeking or AI-generated explanation exists.
- If unsure, return NORMAL.

EXAMPLE 1:
Keylog: from sklearn.linear_model import LinearRegression
OCR: VS Code window
Output: {{"risk":"NORMAL","confidence":0.9,"reasons":["Normal coding activity"]}}

EXAMPLE 2:
Keylog: please explain this error
OCR: Gemini can make mistakes... What can I help you build?
Output: {{"risk":"FLAG","confidence":0.95,"reasons":["Student requested AI explanation"]}}

EXAMPLE 3:
Keylog: import linear_regression
OCR: ImportError: cannot import name...
Output: {{"risk":"NORMAL","confidence":0.9,"reasons":["Error without AI interaction"]}}

Now analyze:

Keylog:
{keylog[:400]}

OCR:
{ocr[:600]}

Return STRICT JSON only.
"""

    try:
        with llm_lock:
            response = llm(
                prompt,
                max_tokens=120,
                temperature=0
            )

        raw = response["choices"][0]["text"].strip()

        # Extract first JSON object safely (non-greedy)
        match = re.search(r'\{.*?\}', raw, re.DOTALL)

        if match:
            json_str = match.group()
            try:
                return json.loads(json_str)
            except:
                pass

        # Safe fallback (never FLAG automatically)
        return {
            "risk": "NORMAL",
            "confidence": 0.5,
            "reasons": ["LLM output malformed but no suspicious activity detected"]
        }


    except Exception as e:
        print("[LLM ERROR]", e)

    return {
        "risk": "NORMAL",
        "confidence": 0.6,
        "reasons": ["LLM parsing fallback"]
    }

    
# =========================================================
# ANALYSIS
# =========================================================

def analyze_file(file_path):

    start_time = time.time()
    filename = os.path.basename(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = raw.get("data", {})

    except:
        return

    ocr = data.get("ocr_text", "")
    keylog = data.get("keylog", "")
    screen = data.get("screen_log", "")
    clipboard = data.get("clipboard", "")

    # Calculate switches per minute
    timestamps = re.findall(r'(\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', screen)
    parsed = []

    for ts in timestamps:
        try:
            parsed.append(datetime.strptime(ts, '%d-%m-%y %H:%M:%S'))
        except:
            pass

    parsed.sort()
    switches_per_min = 0

    if len(parsed) > 1:
        duration = (parsed[-1] - parsed[0]).total_seconds()
        if duration > 0:
            switches_per_min = 60 * len(parsed) / duration

    # =====================================================
    # Layer 1 – Hard Rules
    # =====================================================

    decision = hard_signal_check(ocr, clipboard, switches_per_min)

    # =====================================================
    # Layer 2 – LLM Semantic Detection
    # =====================================================

    if decision is None:
        decision = call_llm_classifier(ocr, keylog)

    allowed_risks = ["NORMAL", "WARNING", "FLAG"]

    if decision.get("risk") not in allowed_risks:
        decision["risk"] = "FLAG" if "help" in decision.get("reasons", [""])[0].lower() else "NORMAL"
        decision["confidence"] = 0.6

    decision["timestamp"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    out_file = os.path.join(AI_OUTPUT_DIR, filename)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(decision, f, indent=2)

    shutil.copy(out_file, LATEST_DECISION_FILE)

    print(f"[AI] {filename} → {decision['risk']} | {round(time.time()-start_time,2)} sec")


# =========================================================
# REALTIME MONITOR
# =========================================================

processed_files = set()

def realtime_monitor(interval=1):

    with ThreadPoolExecutor(max_workers=2) as executor:

        while True:
            try:
                files = sorted(f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".json"))
                new_files = [f for f in files if f not in processed_files]

                for file in new_files:
                    full_path = os.path.join(RAW_DATA_DIR, file)
                    executor.submit(analyze_file, full_path)
                    processed_files.add(file)

                time.sleep(interval)

            except Exception as e:
                print("[MONITOR ERROR]", e)
                time.sleep(2)


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    print("[AI] Hybrid Proctor AI Started")
    realtime_monitor()