import pymod
from player_health_component import PlayerHealthComponent
from item_component import Item

class MyScene(pymod.Scene):
    def on_enter(self):
        # game object 1
        self.item = pymod.GameObject() # create game object
        self.item.add_component(Item())

        self.add_object(self.item) # after adding all components, add that gameobject to the scene

        # game object 2
        self.player = pymod.GameObject()
        self.player.add_component(PlayerHealthComponent(self.item))

        self.add_object(self.player)