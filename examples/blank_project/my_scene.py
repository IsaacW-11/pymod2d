import pymod
from my_component import MyComponent

class MyScene(pymod.Scene):
    def on_enter(self):
        self.game_object = pymod.GameObject() # create game object
        self.game_object.add_component(MyComponent()) # add component(s)

        self.add_object(self.game_object) # after adding all components, add that gameobject to the scene