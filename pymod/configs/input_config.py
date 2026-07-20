from dataclasses import dataclass, field

@dataclass
class InputConfig:
    default_bindings: dict = field(default_factory=dict)