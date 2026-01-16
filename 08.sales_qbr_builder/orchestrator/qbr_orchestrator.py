from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generator, List, TypedDict

from models.qbr_analyzer import aggregate_qbr_data, generate_qbr_insights
from tools.mcp_clients import fetch_analytics_data, fetch_crm_data, fetch_support_data


@dataclass
class QBRRunEvent:
    """Streaming-style step event for durable audit logging."""
    step: str
    event_type: str  # started | completed | error | checkpoint
    payload: Dict[str, Any]
    ts: datetime


@dataclass
class QBRContext:
    request_id: str
    pack_id: str
    account_id: str
    account_name: str
    period_start: Any
    period_end: Any
    goals: List[str]


class QBRState(TypedDict, total=False):
    """LangGraph state container."""
    plan: Dict[str, Any]
    crm_data: Dict[str, Any]
    analytics_data: Dict[str, Any]
    support_data: Dict[str, Any]
    aggregated_data: Dict[str, Any]
    insights_result: Dict[str, Any]


class QBROrchestrator:
    """
    Agent Runtime / Orchestrator implemented as a LangGraph StateGraph.

    We keep the same external contract as before:
    - `run()` yields QBRRunEvent (for trace logging)
    - `run()` returns a dict with crm/analytics/support, aggregated_data, insights_result
    """

    def __init__(self, ctx: QBRContext):
        self.ctx = ctx
        # LangGraph is an optional dependency at runtime; if not installed, we fall back
        # to a sequential execution while keeping the same step/event contract.
        self._graph = self._build_graph()

    def _emit(self, step: str, event_type: str, payload: Dict[str, Any]) -> QBRRunEvent:
        return QBRRunEvent(step=step, event_type=event_type, payload=payload, ts=datetime.utcnow())

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph  # type: ignore
        except Exception:
            return None

        g: StateGraph = StateGraph(QBRState)

        def plan_node(state: QBRState) -> QBRState:
            goals_lower = [g.lower() for g in self.ctx.goals]
            plan = {"fetch_crm": True, "fetch_analytics": True, "fetch_support": True, "notes": []}
            if any("support" in g for g in goals_lower):
                plan["notes"].append("Support/CSAT is prioritized for this run.")
            if any("renewal" in g for g in goals_lower):
                plan["notes"].append("Renewal signals will be emphasized.")
            if any("product adoption" in g for g in goals_lower) or any("adoption" in g for g in goals_lower):
                plan["notes"].append("Product adoption signals will be emphasized.")
            return {"plan": plan}

        def fetch_node(state: QBRState) -> QBRState:
            crm_data = fetch_crm_data(self.ctx.account_id, self.ctx.period_start, self.ctx.period_end)
            analytics_data = fetch_analytics_data(self.ctx.account_id, self.ctx.period_start, self.ctx.period_end)
            support_data = fetch_support_data(self.ctx.account_id, self.ctx.period_start, self.ctx.period_end)
            return {"crm_data": crm_data, "analytics_data": analytics_data, "support_data": support_data}

        def aggregate_node(state: QBRState) -> QBRState:
            aggregated = aggregate_qbr_data(state.get("crm_data", {}), state.get("analytics_data", {}), state.get("support_data", {}))
            return {"aggregated_data": aggregated}

        def generate_node(state: QBRState) -> QBRState:
            insights = generate_qbr_insights(
                account_name=self.ctx.account_name,
                aggregated_data=state.get("aggregated_data", {}),
                goals=self.ctx.goals,
                period_start=self.ctx.period_start,
                period_end=self.ctx.period_end,
            )
            return {"insights_result": insights}

        def finalize_node(state: QBRState) -> QBRState:
            insights = state.get("insights_result", {}) or {}
            insights.setdefault("executive_summary", "")
            insights.setdefault("account_health_score", 0.5)
            insights.setdefault("insights", [])
            insights.setdefault("action_items", [])
            insights.setdefault("metrics", [])
            for ai in insights.get("action_items", []) or []:
                if isinstance(ai, dict):
                    ai.setdefault("assignee", "Customer Success Manager")
                    ai.setdefault("due_date", None)
                    ai.setdefault("priority", "medium")
            return {"insights_result": insights}

        # NOTE: LangGraph disallows node names that collide with state keys.
        # Our state keys include plan/crm_data/etc, so we suffix node names with _node.
        g.add_node("plan_node", plan_node)
        g.add_node("fetch_data_node", fetch_node)
        g.add_node("aggregate_validate_node", aggregate_node)
        g.add_node("generate_insights_node", generate_node)
        g.add_node("finalize_node", finalize_node)

        g.set_entry_point("plan_node")
        g.add_edge("plan_node", "fetch_data_node")
        g.add_edge("fetch_data_node", "aggregate_validate_node")
        g.add_edge("aggregate_validate_node", "generate_insights_node")
        g.add_edge("generate_insights_node", "finalize_node")
        g.add_edge("finalize_node", END)

        return g.compile()

    def run(self) -> Generator[QBRRunEvent, None, Dict[str, Any]]:
        # Emit explicit step events around LangGraph execution to preserve the existing trace model.
        # LangGraph requires the initial input to write at least one state key at __start__.
        # Seed with an empty plan (it will be overwritten by the plan node).
        state: QBRState = {"plan": {}}

        # If LangGraph isn't available in the current environment, run sequentially.
        if self._graph is None:
            yield self._emit("plan", "checkpoint", {"note": "LangGraph not installed; using sequential fallback orchestrator."})

            # plan
            yield self._emit("plan", "started", {})
            goals_lower = [g.lower() for g in self.ctx.goals]
            plan = {"fetch_crm": True, "fetch_analytics": True, "fetch_support": True, "notes": []}
            if any("support" in g for g in goals_lower):
                plan["notes"].append("Support/CSAT is prioritized for this run.")
            if any("renewal" in g for g in goals_lower):
                plan["notes"].append("Renewal signals will be emphasized.")
            if any("product adoption" in g for g in goals_lower) or any("adoption" in g for g in goals_lower):
                plan["notes"].append("Product adoption signals will be emphasized.")
            state["plan"] = plan
            yield self._emit("plan", "completed", {"updated_keys": ["plan"]})

            # fetch_data
            yield self._emit("fetch_data", "started", {})
            state["crm_data"] = fetch_crm_data(self.ctx.account_id, self.ctx.period_start, self.ctx.period_end)
            yield self._emit("fetch_data", "checkpoint", {"source": "crm", "keys": list(state["crm_data"].keys())})
            state["analytics_data"] = fetch_analytics_data(self.ctx.account_id, self.ctx.period_start, self.ctx.period_end)
            yield self._emit("fetch_data", "checkpoint", {"source": "analytics", "keys": list(state["analytics_data"].keys())})
            state["support_data"] = fetch_support_data(self.ctx.account_id, self.ctx.period_start, self.ctx.period_end)
            yield self._emit("fetch_data", "checkpoint", {"source": "support", "keys": list(state["support_data"].keys())})
            yield self._emit("fetch_data", "completed", {"updated_keys": ["crm_data", "analytics_data", "support_data"]})

            # aggregate_validate
            yield self._emit("aggregate_validate", "started", {})
            state["aggregated_data"] = aggregate_qbr_data(state["crm_data"], state["analytics_data"], state["support_data"])
            warnings = (state["aggregated_data"] or {}).get("data_quality_warnings", [])
            yield self._emit("aggregate_validate", "checkpoint", {"warnings": warnings})
            yield self._emit("aggregate_validate", "completed", {"updated_keys": ["aggregated_data"]})

            # generate_insights
            yield self._emit("generate_insights", "started", {})
            state["insights_result"] = generate_qbr_insights(
                account_name=self.ctx.account_name,
                aggregated_data=state["aggregated_data"],
                goals=self.ctx.goals,
                period_start=self.ctx.period_start,
                period_end=self.ctx.period_end,
            )
            ins = state["insights_result"] or {}
            yield self._emit(
                "generate_insights",
                "checkpoint",
                {
                    "insights_count": len(ins.get("insights", []) or []),
                    "action_items_count": len(ins.get("action_items", []) or []),
                    "metrics_count": len(ins.get("metrics", []) or []),
                    "has_error": bool(ins.get("error")),
                },
            )
            yield self._emit("generate_insights", "completed", {"updated_keys": ["insights_result"]})

            # finalize
            yield self._emit("finalize", "started", {})
            insights = state.get("insights_result", {}) or {}
            insights.setdefault("executive_summary", "")
            insights.setdefault("account_health_score", 0.5)
            insights.setdefault("insights", [])
            insights.setdefault("action_items", [])
            insights.setdefault("metrics", [])
            for ai in insights.get("action_items", []) or []:
                if isinstance(ai, dict):
                    ai.setdefault("assignee", "Customer Success Manager")
                    ai.setdefault("due_date", None)
                    ai.setdefault("priority", "medium")
            state["insights_result"] = insights
            yield self._emit("finalize", "completed", {"updated_keys": ["insights_result"]})

            return {
                "crm_data": state.get("crm_data", {}) or {},
                "analytics_data": state.get("analytics_data", {}) or {},
                "support_data": state.get("support_data", {}) or {},
                "aggregated_data": state.get("aggregated_data", {}) or {},
                "insights_result": state.get("insights_result", {}) or {},
            }

        node_map = {
            "plan": "plan_node",
            "fetch_data": "fetch_data_node",
            "aggregate_validate": "aggregate_validate_node",
            "generate_insights": "generate_insights_node",
            "finalize": "finalize_node",
        }

        for step_name in ["plan", "fetch_data", "aggregate_validate", "generate_insights", "finalize"]:
            yield self._emit(step_name, "started", {})
            # Invoke one step at a time by running the compiled graph and capturing updates for that node.
            # We use graph.stream to get per-node updates deterministically.
            out_state = None
            internal = node_map[step_name]
            for update in self._graph.stream(state, stream_mode="updates"):  # type: ignore[union-attr]
                # update is like {"node_name": {"key": value}}
                if internal in update:
                    state.update(update[internal])
                    out_state = update[internal]
                    break

            # Add step-specific checkpoints
            if step_name == "fetch_data":
                for src in ("crm_data", "analytics_data", "support_data"):
                    if src in state and isinstance(state[src], dict):
                        yield self._emit(step_name, "checkpoint", {"source": src.replace("_data", ""), "keys": list(state[src].keys())})
            if step_name == "aggregate_validate":
                warnings = (state.get("aggregated_data", {}) or {}).get("data_quality_warnings", [])
                yield self._emit(step_name, "checkpoint", {"warnings": warnings})
            if step_name == "generate_insights":
                ins = state.get("insights_result", {}) or {}
                yield self._emit(
                    step_name,
                    "checkpoint",
                    {
                        "insights_count": len(ins.get("insights", []) or []),
                        "action_items_count": len(ins.get("action_items", []) or []),
                        "metrics_count": len(ins.get("metrics", []) or []),
                        "has_error": bool(ins.get("error")),
                    },
                )

            yield self._emit(step_name, "completed", {"updated_keys": list((out_state or {}).keys())})

        return {
            "crm_data": state.get("crm_data", {}) or {},
            "analytics_data": state.get("analytics_data", {}) or {},
            "support_data": state.get("support_data", {}) or {},
            "aggregated_data": state.get("aggregated_data", {}) or {},
            "insights_result": state.get("insights_result", {}) or {},
        }

