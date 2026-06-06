from typing import Protocol

from atomic_agent.models import AgentInvocation, AgentRunResult


class AgentRuntimePort(Protocol):
    def invoke(self, invocation: AgentInvocation) -> AgentRunResult:
        ...


class AgentRuntimeRunner(Protocol):
    def run(self, invocation: AgentInvocation) -> AgentRunResult:
        ...


class BoardroomAgentRuntimePortAdapter:
    def __init__(self, runner: AgentRuntimeRunner):
        self.runner = runner

    def invoke(self, invocation: AgentInvocation) -> AgentRunResult:
        if not isinstance(invocation, AgentInvocation):
            raise TypeError("AgentRuntimePort.invoke requires AgentInvocation")
        result = self.runner.run(invocation)
        if not isinstance(result, AgentRunResult):
            raise TypeError("runner.run must return AgentRunResult")
        return result
