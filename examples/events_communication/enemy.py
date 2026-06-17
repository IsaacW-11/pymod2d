import pymod
from my_event import TakeDamage

class Enemy(pymod.Component):
    def on_attach(self):
        pymod.events.emit(TakeDamage(damage=2, critical_hit=True)) # this emits the TakeDamage event with the required arguments. That information is sent to all listeners for that Event, including the player (in this example)