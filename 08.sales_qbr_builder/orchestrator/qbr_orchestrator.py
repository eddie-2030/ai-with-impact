from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Generator, TypedDict

from models.qbr_analyzer import aggregate_qbr_data, generate_qbr_insights
from tools.mcp_clients import fetch_analytics_data, fetch_crm_data, fetch_support_data


@dataclass
class QBRRunEvent:
    """Step event for durable audit logging."""

    step: str
    event_type: str
    payload: dict[str, Any]
    ts: datetime


@dataclass
class QBRContext:
    request_id: str
    pack_id: str
    account_id: str
    account_name: str
    period_start: Any
    period_end: Any
    goals: list[str]


class QBRState(TypedDict, total=False):
    plan: dict[str, Any]
    crm_data: dict[str, Any]
    analytics_data: dict[str, Any]
    support_data: dict[str, Any]
    aggregated_data: dict[str, Any]
    insights_result: dict[str, Any]


class QBROrchestrator:
    """Run the QBR stages in order, yielding trace events before returning results."""

    def __init__(self, ctx: QBRContext):
        self.ctx = ctx
        self._stages: tuple[tuple[str, Callable[[QBRState], QBRState]], ...] = (
            ("plan", self._plan),
            ("fetch_data", self._fetch_data),
            ("aggregate_validate", self._aggregate),
            ("generate_insights", self._generate),
            ("finalize", self._finalize),
        )
        self._graph = self._build_graph()

    @staticmethod
    def _emit(step: str, event_type: str, payload: dict[str, Any]) -> QBRRunEvent:
        return QBRRunEvent(step, event_type, payload, datetime.now(UTC).replace(tzinfo=None))

    def _plan(self, state: QBRState) -> QBRState:
        goals = [goal.lower() for goal in self.ctx.goals]
        priorities = {
            "support": "Support/CSAT is prioritized for this run.",
            "renewal": "Renewal signals will be emphasized.",
            "adoption": "Product adoption signals will be emphasized.",
        }
        return {
            "plan": {
                "fetch_crm": True,
                "fetch_analytics": True,
                "fetch_support": True,
                "notes": [note for keyword, note in priorities.items() if any(keyword in goal for goal in goals)],
            }
        }

    def _fetch_data(self, state: QBRState) -> QBRState:
        ctx = self.ctx
        return {
            "crm_data": fetch_crm_data(ctx.account_id, ctx.period_start, ctx.period_end),
            "analytics_data": fetch_analytics_data(ctx.account_id, ctx.period_start, ctx.period_end),
            "support_data": fetch_support_data(ctx.account_id, ctx.period_start, ctx.period_end),
        }

    def _aggregate(self, state: QBRState) -> QBRState:
        aggregated = aggregate_qbr_data(state["crm_data"], state["analytics_data"], state["support_data"])
        return {"aggregated_data": aggregated}

    def _generate(self, state: QBRState) -> QBRState:
        ctx = self.ctx
        insights = generate_qbr_insights(
            account_name=ctx.account_name,
            aggregated_data=state["aggregated_data"],
            goals=ctx.goals,
            period_start=ctx.period_start,
            period_end=ctx.period_end,
        )
        return {"insights_result": insights}

    @staticmethod
    def _finalize(state: QBRState) -> QBRState:
        insights = {
            "executive_summary": "",
            "account_health_score": 0.5,
            "insights": [],
            "action_items": [],
            "metrics": [],
            **(state["insights_result"] or {}),
        }
        insights["action_items"] = [
            {"assignee": "Customer Success Manager", "due_date": None, "priority": "medium", **item}
            for item in (insights["action_items"] or [])
        ]
        return {"insights_result": insights}

    def _build_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except ModuleNotFoundError as error:
            if error.name != "langgraph":
                raise
            return None

        graph = StateGraph(QBRState)
        previous = START
        for step, handler in self._stages:
            # Node names must differ from the state keys.
            node = f"{step}_node"
            graph.add_node(node, handler)
            graph.add_edge(previous, node)
            previous = node
        graph.add_edge(previous, END)
        return graph.compile()

    def _sequential_updates(self, state: QBRState):
        for step, handler in self._stages:
            update = handler(state)
            state.update(update)
            yield {f"{step}_node": update}

    def _checkpoints(self, step: str, update: QBRState):
        if step == "fetch_data":
            for source in ("crm", "analytics", "support"):
                yield self._emit(step, "checkpoint", {"source": source, "keys": list(update[f"{source}_data"])})
        elif step == "aggregate_validate":
            warnings = update["aggregated_data"].get("data_quality_warnings", [])
            yield self._emit(step, "checkpoint", {"warnings": warnings})
        elif step == "generate_insights":
            insights = update["insights_result"] or {}
            yield self._emit(
                step,
                "checkpoint",
                {
                    "insights_count": len(insights.get("insights") or []),
                    "action_items_count": len(insights.get("action_items") or []),
                    "metrics_count": len(insights.get("metrics") or []),
                    "has_error": bool(insights.get("error")),
                },
            )

    def run(self) -> Generator[QBRRunEvent, None, dict[str, Any]]:
        initial: QBRState = {"plan": {}}
        state: QBRState = {}

        if self._graph is None:
            yield self._emit("plan", "checkpoint", {"note": "LangGraph not installed; using sequential fallback orchestrator."})
            updates = self._sequential_updates(initial)
        else:
            updates = self._graph.stream(initial, stream_mode="updates")

        # Advancing a single stream runs the next node using the same graph state.
        with closing(updates):
            for step, _ in self._stages:
                yield self._emit(step, "started", {})
                node = f"{step}_node"
                chunk = next(updates, None)
                if chunk is None or chunk.keys() != {node}:
                    raise RuntimeError(f"QBR graph did not produce the expected {step} update")
                update = chunk[node]
                state.update(update)
                yield from self._checkpoints(step, update)
                yield self._emit(step, "completed", {"updated_keys": list(update)})

            if next(updates, None) is not None:
                raise RuntimeError("QBR graph produced an unexpected update after finalize")

        return {
            "crm_data": state["crm_data"],
            "analytics_data": state["analytics_data"],
            "support_data": state["support_data"],
            "aggregated_data": state["aggregated_data"],
            "insights_result": state["insights_result"],
        }

