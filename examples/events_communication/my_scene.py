import pymod
from player import Player
from enemy import Enemy

class MyScene(pymod.Scene):
    def on_enter(self):
        # adds player game object with component
        self.player = pymod.GameObject().add_component(Player())
        self.add_object(self.player)

        # adds enemy game object with component
        self.enemy = pymod.GameObject().add_component(Enemy())
        self.add_object(self.enemy)