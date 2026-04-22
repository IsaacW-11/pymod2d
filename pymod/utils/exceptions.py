"""This file contains a list of custom exceptions."""

class MissingComponentError(Exception):
    """Raised when a component is not found."""
    pass

class EmptySceneManagerStack(Exception):
    """Raised when the scene manager stack is accessed, but is empty."""
    pass

class ExistingGameInstance(Exception):
    """Raised when a second game instance is attempted to be created."""
    pass

class MissingGameInstance(Exception):
    """Raised when trying to access a non-existent game instance."""