import os
import threading

from ultralytics import YOLO


class DetectionModelProvider:
    _model = None
    _model_name = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls) -> YOLO:
        with cls._lock:
            if cls._model is None:
                cls._load_model(os.getenv("DETECTION_YOLO_MODEL", "yolo11n"))
            return cls._model

    @classmethod
    def preload(cls, model_name: str | None = None):
        """Download and load model in background thread. Called at startup and on config change."""
        name = model_name or os.getenv("DETECTION_YOLO_MODEL", "yolo11n")

        def _load():
            with cls._lock:
                if name == cls._model_name and cls._model is not None:
                    return
                cls._load_model(name)

        threading.Thread(target=_load, daemon=True).start()

    @classmethod
    def reload(cls, model_name: str):
        """Download and load a new model (blocking for config change feedback)."""
        with cls._lock:
            if model_name == cls._model_name and cls._model is not None:
                return
            cls._load_model(model_name)

    @classmethod
    def _load_model(cls, model_name: str):
        print(f"Loading YOLO model: {model_name}")
        cls._model = YOLO(f"{model_name}.pt")
        cls._model_name = model_name
        print(f"YOLO model {model_name} loaded successfully")
