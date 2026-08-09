"""Planner Agent — Creates governance execution plan."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.schemas.governance import PlanStep, PlannerResult, AgentStatus

async def run_planner(state):
    state.add_agent_execution('planner')
    steps = [
        PlanStep(step=1, agent='intent', action='Classify action intent and data sensitivity', status=AgentStatus.PENDING),
        PlanStep(step=2, agent='identity', action='Verify user identity and authorization', status=AgentStatus.PENDING),
        PlanStep(step=3, agent='policy_retrieval', action='Retrieve relevant enterprise policies', status=AgentStatus.PENDING),
        PlanStep(step=4, agent='compliance', action='Evaluate compliance against policies', status=AgentStatus.PENDING),
        PlanStep(step=5, agent='risk', action='Calculate risk score', status=AgentStatus.PENDING),
        PlanStep(step=6, agent='explainability', action='Generate human-readable explanation', status=AgentStatus.PENDING),
        PlanStep(step=7, agent='reviewer', action='Validate decision with second-level review', status=AgentStatus.PENDING),
    ]
    state.plan = PlannerResult(steps=steps, reasoning='Standard governance pipeline for data action request')
    state.complete_agent_execution('planner', AgentStatus.COMPLETED)
    return state
