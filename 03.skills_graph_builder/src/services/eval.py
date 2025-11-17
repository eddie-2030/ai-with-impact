import os, json, time

try:
    import mlflow
    MLFLOW_AVAILABLE = True
    MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "skills_graph_case_study")
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT)
except ImportError:
    MLFLOW_AVAILABLE = False

def log_event(event_type: str, payload: dict):
    if MLFLOW_AVAILABLE:
        with mlflow.start_run(run_name=event_type, nested=True):
            mlflow.log_dict(payload, f"{event_type}.json")
            for k, v in payload.items():
                if isinstance(v, (int, float)):
                    mlflow.log_metric(k, v)
    else:
        # Fallback: just print the event
        print(f"Event: {event_type} - {payload}")
