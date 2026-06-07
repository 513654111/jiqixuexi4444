from safety.input_guardrails import InputGuardrail
from agents.orchestrator import Orchestrator
def main():
    guard = InputGuardrail()
    orch = Orchestrator()
    test = "What is the remote work policy?"
    blocked, sanitized, inc = guard.check(test)
    if not blocked:
        print("User:", sanitized)
        ans = orch.process_query(sanitized)
        print("Assistant:", ans)
    else:
        print("Blocked:", inc["rule"])
if __name__ == "__main__":
    main()
