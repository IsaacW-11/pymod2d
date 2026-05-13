import pymod
import random

class RandomColour(pymod.Component):
    def on_attach(self):
        self.screen = pymod.Game.get().screen
        self.colour = (0, 0, 0)
        self.change_colour()
        pymod.time.add_timer(pymod.Timer(1, self.change_colour, True).start())

    def change_colour(self):
        self.colour = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def draw(self):
        self.screen.fill(self.colour)

class GameStopwatch(pymod.Component):
    def on_attach(self):
        self.stopwatch = pymod.time.add_stopwatch(pymod.Stopwatch().start())

    def fixed_update(self):
        print(self.stopwatch.elapsed)

class MyScene(pymod.Scene):
    def on_enter(self):
        random_colour_generator = pymod.GameObject()
        random_colour_generator.add_component(RandomColour())
        self.add_object(random_colour_generator)

        game_stopwatch = pymod.GameObject()
        game_stopwatch.add_component(GameStopwatch())
        self.add_object(game_stopwatch)

game = pymod.Game()
game.run(MyScene())