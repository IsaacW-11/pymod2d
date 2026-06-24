import pygame
import pymod

class SpriteRenderer(pymod.Component):
    # WARNING: This component is a temporary component just to demonstrate the asset manager and how it stores the assets
    # In the near future, the official SpriteRenderer component will take over this.
    # The official SpriteRenderer will be a premade component that you can just attach to any game object, and pass an image asset to render
    def on_attach(self):
        # this is how you load an asset using the asset manager. in this example, it is a spritesheet.
        self.images = (pymod.assets.load_spritesheet('example_spritesheet', 32, 32)).copy()

    def draw(self):
        pymod.screen.render_surface.blit(pygame.transform.scale(self.images[3], (128, 128)), (0,0)) # this draws image to screen