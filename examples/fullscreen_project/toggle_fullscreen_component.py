import pygame.constants

import pymod


class ToggleFullscreen(pymod.Component):
    def update(self):
        if pymod.input.action_pressed("toggle_fullscreen"): # checks if the action group 'toggle_fullscreen' is pressed
            pymod.screen.toggle_fullscreen() # swaps screen between fullscreen and windowed

        # another option to check input is by checking the raw key input, rather than using action groups
        # if pymod.input.key_pressed("esc"):
        #    pymod.screen.toggle_fullscreen()

        if pymod.screen.display_mode == pymod.DisplayMode.WINDOWED: # checks if display is currently WINDOWED
            pymod.screen.add_display_flag(pygame.RESIZABLE) # makes it so window is resizable
