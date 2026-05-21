import asyncio
import websockets

async def main():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello Servr")
        print("Sent: Hello Server")

        response = await websocket.recv()
        print(f"Received: {response}")

if __name__ == "__main__":
    asyncio.run(main())
