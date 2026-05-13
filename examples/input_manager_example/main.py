import pymod

DEFAULT_BINDINGS = {
    # change colour
    'red': ["r", "mouse_left"],
    'green': ["g", "mouse_middle"],
    'blue': ["b", "mouse_right"],
}

class ChangeBackgroundColour(pymod.Component):
    def on_attach(self):
        self.bg_colour = (0, 0, 0)

    def update(self):
        if pymod.input.action_pressed("red"):
            self.bg_colour = (255, 0, 0)
        elif pymod.input.action_pressed("green"):
            self.bg_colour = (0, 255, 0)
        elif pymod.input.action_pressed("blue"):
            self.bg_colour = (0, 0, 255)

    def draw(self):
        pymod.Game.get().screen.fill(self.bg_colour)

class GameScene(pymod.Scene):
    def on_enter(self):
        for action, keys in DEFAULT_BINDINGS.items():
            pymod.input.create_action(action, keys)

        # background colour component
        background_colour_changer = pymod.GameObject()
        background_colour_changer.add_component(ChangeBackgroundColour())
        self.add_object(background_colour_changer)

game = pymod.Game()
game.run(GameScene())