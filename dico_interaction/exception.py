class InteractionException(Exception):
    """Base exception of this module."""


class InvalidOptionParameter(InteractionException):
    """Received option does not match to command parameter."""


class CheckFailed(InteractionException):
    """Check has failed."""


class AlreadyExists(InteractionException):
    """This command or callback already exists."""
    def __init__(self, error_type, name):
        super().__init__(f"{error_type} '{name}' already exists")


class NotExists(InteractionException):
    """This command or callback does not exist."""
    def __init__(self, error_type, name):
        super().__init__(f"{error_type} '{name}' does not exist")
