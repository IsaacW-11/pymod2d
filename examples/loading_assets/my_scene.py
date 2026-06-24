import pymod

from sprite_renderer_component import SpriteRenderer

class MyScene(pymod.Scene):
    def on_enter(self):
        sprite_object = pymod.GameObject()
        sprite_object.add_component(SpriteRenderer())

        self.add_object(sprite_object)