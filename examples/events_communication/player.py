import pymod
from my_event import TakeDamage

class Player(pymod.Component):
    def on_attach(self):
        self.health = 10
        pymod.events.subscribe(TakeDamage, self.decrease_health) # subscribes to the TakeDamage event. self.decrease_health will now run every time the TakeDamage event is emitted

    def decrease_health(self, event: TakeDamage):
        # any callback function must take an event as an argument
        if event.critical_hit:
            self.health -= event.damage * 2
        else:
            self.health -= event.damage

        print(f"{self.health} health remaining.")