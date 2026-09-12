import os

os.environ["MIAI_PROVIDER"] = "mock"

from python.core.agent import AutonomousAgent
from python.tools.defaults import create_default_tool_registry
from python.tools.executor import ToolExecutor


class FakeProvider:
    name = "fake"
    model = "agent-test"

    def __init__(self):
        self.calls = 0

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        self.calls += 1
        if self.calls == 1:
            return '{"action":"tool","tool":"calculator","arguments":{"expression":"2+3*4"}}'
        return '{"action":"final","answer":"El resultado es 14."}'


def test_agent_executes_tool_and_finishes():
    registry = create_default_tool_registry()
    provider = FakeProvider()
    agent = AutonomousAgent(provider, registry, ToolExecutor(registry))

    result = agent.run("Calcula 2+3*4", max_steps=4)

    assert result.status == "completed"
    assert result.answer == "El resultado es 14."
    assert result.steps[0].tool == "calculator"
    assert result.steps[0].result == 14
    assert provider.calls == 2


def test_agent_respects_step_limit():
    class LoopProvider:
        name = "fake"
        model = "loop-test"
        def generate(self, prompt: str, temperature: float = 0.7) -> str:
            return '{"action":"tool","tool":"datetime","arguments":{}}'

    registry = create_default_tool_registry()
    agent = AutonomousAgent(LoopProvider(), registry, ToolExecutor(registry))
    result = agent.run("hazlo", max_steps=2)
    assert result.status == "max_steps_reached"
    assert len(result.steps) == 3
