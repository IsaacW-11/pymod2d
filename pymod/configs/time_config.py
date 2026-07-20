from dataclasses import dataclass

@dataclass
class TimeConfig:
    fps: int = 60
    fps_history_size: int = 60