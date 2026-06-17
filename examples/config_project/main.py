import pymod

from my_scene import MyScene

# create configs as shown below. They should be created before the game
screen_config = pymod.ScreenConfig(
    title="Config Project",
    window_size=(500, 500)
)
input_config = pymod.InputConfig(
    default_bindings={
        "change_colour": ["space", "mouse_left"]
    }
)

game = pymod.Game(screen_config=screen_config, input_config=input_config) # create game

game.run(MyScene()) # initialize game with starting scene