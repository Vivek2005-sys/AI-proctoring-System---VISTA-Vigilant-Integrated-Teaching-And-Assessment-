import time
from VISTA.Agent.src.orchestrator import AgentOrchestrator

def main():
    orch = AgentOrchestrator()
    orch.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Agent] Shutdown signal received")
        orch.stop()

if __name__ == "_main_":
    main()