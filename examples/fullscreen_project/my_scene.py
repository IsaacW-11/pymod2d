import pymod
from toggle_fullscreen_component import ToggleFullscreen

class MyScene(pymod.Scene):
    def on_enter(self):
        pymod.screen.set_display_mode(pymod.DisplayMode.FULLSCREEN) # starts fullscreen by default

        self.background_changer = pymod.GameObject() # create game object
        self.background_changer.add_component(ToggleFullscreen()) # add component(s)

        self.add_object(self.background_changer) # after adding all components, add that gameobject to the scene

        # configuring inputs
        pymod.input.create_action("toggle_fullscreen", ["esc"]) # creates an action group called 'toggle_fullscreen', with the binding of ESC key