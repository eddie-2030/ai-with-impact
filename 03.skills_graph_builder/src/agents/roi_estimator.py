from ..services.eval import log_event
def log_assignment(person_id: str, role_id: str, plan_actions_count: int):
    log_event("plan_assigned", {"person_id": person_id, "role_id": role_id, "actions": plan_actions_count})
