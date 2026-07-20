from dataclasses import dataclass
import pymod

# this is an example of a simple event
# they don't have to be a @dataclass, but it helps with simplicity
# they also don't have to inherit from pymod.Event, but it allows for cancellation support and is easier to know what classes are events
@dataclass
class TakeDamage(pymod.Event):
    damage: int = 5
    critical_hit: bool = False