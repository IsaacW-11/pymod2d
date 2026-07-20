import pymod

class ColourChanger(pymod.Component):
    def draw(self):
        if pymod.input.action_held("change_colour"): # checks the action created in the config
            pymod.screen.render_surface.fill((255,255,255))
        else:
            pymod.screen.render_surface.fill((0,0,0))