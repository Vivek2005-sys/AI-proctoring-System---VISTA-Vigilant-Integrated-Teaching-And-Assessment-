import streamlit as st
import asyncio
import websockets
import json
import os
import time
import base64

# ================== WS CONFIG ==================
WS_URL = "ws://localhost:8765"

async def _send(data):
    try:
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({"role": "controller"}))
            await ws.send(json.dumps(data))
    except Exception as e:
        print("WebSocket Error:", e)

def send_command(action, module=None):
    payload = {"action": action}
    if module:
        payload["module"] = module

    asyncio.run(_send(payload))


# ================== PAGE ==================
st.set_page_config(page_title="Teacher Monitoring Dashboard", layout="wide")

if "mode" not in st.session_state:
    st.session_state.mode = "exam"


# ================== MODULES ==================
ALL_MODULES = [
    "input_blocker",
    "process_blocker",
    "slideshow",
    "keyboard",
    "screen",
    "usb",
    "ocr",
    "raw"
]

for m in ALL_MODULES:
    key = f"{m}_state"
    if key not in st.session_state:
        st.session_state[key] = False


# ================== MODE HANDLERS ==================
def activate_exam_mode():
    for m in ALL_MODULES:
        if m != "slideshow":
            send_command("start", m)
            st.session_state[f"{m}_state"] = True

    send_command("stop", "slideshow")
    st.session_state["slideshow_state"] = False


def activate_practical_mode():
    for m in ALL_MODULES:
        send_command("stop", m)
        st.session_state[f"{m}_state"] = False

    send_command("start", "slideshow")
    st.session_state["slideshow_state"] = True


# ================== TOGGLE ==================
def toggle_module(module, label):
    state_key = f"{module}_state"
    active = st.session_state[state_key]

    btn_label = f"🟢 Stop {label}" if active else label

    if st.button(btn_label, key=f"{module}_btn"):
        if active:
            send_command("stop", module)
            st.session_state[state_key] = False
        else:
            send_command("start", module)
            st.session_state[state_key] = True

        st.rerun()


# ================== SIDEBAR ==================
with st.sidebar:
    st.title("📚 Teacher Panel")

    st.markdown("### Session Mode")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Exam Mode"):
            st.session_state.mode = "exam"
            activate_exam_mode()

    with col2:
        if st.button("Practical Mode"):
            st.session_state.mode = "practical"
            activate_practical_mode()

    st.markdown("---")

    if st.session_state.mode == "exam":
        st.success("Current Mode: EXAM")
    else:
        st.error("Current Mode: PRACTICAL")

    st.markdown("---")
    st.markdown("### Controls")

    toggle_module("input_blocker", "🔒 Block All Inputs")
    toggle_module("process_blocker", "🚫 Block Browsers")
    toggle_module("slideshow", "🖼 Slideshow")
    toggle_module("keyboard", "⌨ Keylogger")
    toggle_module("screen", "📸 Screen Monitoring")
    toggle_module("usb", "🔌 USB Monitoring")
    toggle_module("ocr", "🧠 OCR")
    toggle_module("raw", "📊 Raw Data")

    st.markdown("---")

    if st.button("🛑 Freeze All Systems"):
        send_command("freeze_all")

    if st.button("▶ Resume All Systems"):
        send_command("resume_all")

    st.markdown("---")
    st.caption("Teacher Monitoring System")


# ================== CSS ==================
st.markdown("""
<style>
.grid-tile {
    border: 4px solid #2ecc71;
    border-radius: 12px;
    padding: 6px;
    margin-bottom: 14px;
    background: #0e1117;
}
.grid-tile img {
    width: 100%;
    border-radius: 8px;
}
.pc-label {
    display: flex;
    justify-content: space-between;
    margin-top: 6px;
    font-size: 13px;
}
.status {
    background: #2ecc71;
    color: black;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ================== CONFIG ==================
IMAGE_DIR = r"VISTA\\assets\\images\\agent_ss"
NUM_COLS = 1
TOTAL_PCS = 1
PLAYBACK_DELAY = 1

PCS = [f"PC-{i+1}" for i in range(TOTAL_PCS)]

if "selected_pc" not in st.session_state:
    st.session_state.selected_pc = None

if "global_frame" not in st.session_state:
    st.session_state.global_frame = 0


# ================== HEADER ==================
st.title("🧑‍🏫 Live Student Monitoring Dashboard")
st.write("---")


# ============================================================
# 🟢 GRID VIEW
# ============================================================
if st.session_state.selected_pc is None:

    st.subheader("🖥 Student Screens (Live Grid View)")

    if not os.path.exists(IMAGE_DIR):
        st.warning("Screen folder not found")
        st.stop()

    images = sorted(os.listdir(IMAGE_DIR))

    if len(images) == 0:
        st.warning("No images available")
        st.stop()

    cols = st.columns(NUM_COLS)

    frame = st.session_state.global_frame % len(images)

    for i, pc in enumerate(PCS):
        with cols[i % NUM_COLS]:

            img_path = os.path.join(IMAGE_DIR, images[frame])

            with open(img_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            st.markdown(
                f"""
                <div class="grid-tile">
                    <img src="data:image/png;base64,{img_b64}">
                    <div class="pc-label">
                        <span>{pc}</span>
                        <span class="status">LIVE</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("View", key=f"view_{pc}"):
                st.session_state.selected_pc = pc
                st.rerun()

    st.session_state.global_frame += 1
    time.sleep(PLAYBACK_DELAY)
    st.rerun()


# ============================================================
# 🔵 DETAIL VIEW
# ============================================================
else:
    pc = st.session_state.selected_pc
    st.subheader(f"🖥 Live View — {pc}")

    images = sorted(os.listdir(IMAGE_DIR))

    placeholder = st.empty()

    for img in images:
        placeholder.image(
            os.path.join(IMAGE_DIR, img),
            use_container_width=True
        )
        time.sleep(PLAYBACK_DELAY)

    st.write("---")

    if st.button("⬅ Back to Grid"):
        st.session_state.selected_pc = None
        st.rerun()

    st.rerun()