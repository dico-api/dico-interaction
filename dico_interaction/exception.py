class InteractionException(Exception):
    """Base exception of this module."""


class InvalidOptionParameter(InteractionException):
    """Received option does not match to command parameter."""
