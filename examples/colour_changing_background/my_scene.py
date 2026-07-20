import pymod
from colour_changer_component import ColourChanger

class MyScene(pymod.Scene):
    def on_enter(self):
        self.background_changer = pymod.GameObject() # create game object
        self.background_changer.add_component(ColourChanger()) # add component(s)

        self.add_object(self.background_changer) # after adding all components, add that gameobject to the scene