import pymod

class MyComponent(pymod.Component):
    def on_attach(self):
        print("Game Object Attached")

    def update(self):
        print("Game Object Updated")