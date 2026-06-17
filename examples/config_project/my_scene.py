import pymod
from colour_changer_component import ColourChanger

class MyScene(pymod.Scene):
    def on_enter(self):
        self.game_object = pymod.GameObject()
        self.game_object.add_component(ColourChanger())

        self.add_object(self.game_object)