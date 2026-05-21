import asyncio
import websockets
import json

AGENTS = set()
CONTROLLERS = set()


# ================= SAFE SEND =================
async def safe_send(ws, message):
    try:
        await ws.send(message)
        return True
    except:
        return False


# ================= HANDLE CONNECTION =================
async def handle_connection(websocket):
    print("[SERVER] New connection")

    try:
        msg = await websocket.recv()
        data = json.loads(msg)

        role = data.get("role")

        if role == "agent":
            await handle_agent(websocket)

        elif role == "controller":
            await handle_controller(websocket)

        else:
            print("[SERVER] Invalid role")
            await websocket.close()

    except Exception as e:
        print(f"[SERVER ERROR] {e}")


# ================= AGENT =================
async def handle_agent(websocket):
    print("[AGENT] Connected")
    AGENTS.add(websocket)

    try:
        async for message in websocket:
            print(f"[AGENT → SERVER] {message}")

    except websockets.ConnectionClosed:
        print("[AGENT] Disconnected")

    finally:
        AGENTS.discard(websocket)


# ================= CONTROLLER =================
async def handle_controller(websocket):
    print("[CONTROLLER] Connected")
    CONTROLLERS.add(websocket)

    try:
        async for message in websocket:
            print(f"[CTRL → SERVER] {message}")

            try:
                data = json.loads(message)
            except:
                continue

            await broadcast_to_agents(data)

    except websockets.ConnectionClosed:
        print("[CONTROLLER] Disconnected")

    finally:
        CONTROLLERS.discard(websocket)


# ================= BROADCAST =================
async def broadcast_to_agents(command):
    if not AGENTS:
        print("[SERVER] No agents connected")
        return

    msg = json.dumps(command)

    dead = set()

    tasks = []
    for agent in AGENTS:
        tasks.append(send_and_check(agent, msg, dead))

    await asyncio.gather(*tasks)

    # remove dead sockets
    for d in dead:
        AGENTS.discard(d)

    print(f"[SERVER → AGENTS] {msg}")


async def send_and_check(ws, msg, dead_set):
    ok = await safe_send(ws, msg)
    if not ok:
        dead_set.add(ws)


# ================= MAIN =================
async def main():
    async with websockets.serve(
        handle_connection,
        "0.0.0.0",
        8765,
        ping_interval=20,
        ping_timeout=20,
    ):
        print("✅ WebSocket running on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())