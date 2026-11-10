import logging
import os

logger = logging.getLogger(__name__)


def log_event(event_type: str, payload: dict):
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if not tracking_uri:
        return

    try:
        import mlflow

        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT", "skills_graph_case_study"))
        with mlflow.start_run(run_name=event_type, nested=True):
            mlflow.log_dict(payload, f"{event_type}.json")
            for key, value in payload.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, value)
    except Exception:
        logger.warning("Could not record the event in the configured MLflow tracker.")
