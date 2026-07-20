import pymod
import random

class ColourChanger(pymod.Component):
    def on_attach(self):
        self.background_colour = (0, 0, 0) # initialize all class variables in on_attach or on_start

        self.my_timer = pymod.Timer(1, self.change_background, True) # this creates a timer that calls self.change_background every second, and it repeats until stopped
        pymod.time.add_timer(self.my_timer) # the timer won't start updating unless it is added to the time manager

        self.my_timer.start() # IMPORTANT. if your timer or stopwatch isn't working, make sure you have started it. you can start it before or after it is added to time manager

    def change_background(self):
        # you can create your own functions anywhere in a component
        self.background_colour = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

    def draw(self):
        pymod.screen.render_surface.fill(self.background_colour) # everything is rendered to screen.render_surface