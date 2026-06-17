import pymod

class PlayerHealthComponent(pymod.Component):
    def __init__(self, item_reference):
        super().__init__()

        self.item_reference: pymod.GameObject = item_reference
        # this is how you get a reference to an external game object
        # you should be creating an argument in the __init__ method, then saving that reference
        # you pass this reference in your scene when creating the game objects
        # remember to use on_start to access any of this game objects components or logic

    def on_attach(self):
        # initialise internal logic (example player)
        self.health = 5

    def on_start(self):
        from item_component import Item # to get a reference to a component, you need to import it. Do this at the beginning of on_start
        item = self.item_reference.require_component(Item) # this gets a reference to a specific component on the game object
        print(item.ability)