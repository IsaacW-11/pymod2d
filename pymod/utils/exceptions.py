"""This file contains a list of custom exceptions."""

class MissingComponentError(Exception):
    """Raised when a component is not found."""
    pass

class EmptySceneManagerStack(Exception):
    """Raised when the scene manager stack is accessed, but is empty."""
    pass