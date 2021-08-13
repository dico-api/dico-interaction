import inspect
from dico import GuildMember, User, Channel, Role, ApplicationCommandOptionType


def read_function(func):
    params = [*inspect.signature(func).parameters.values()]
    if params[0].name in ["self", "cls"]:
        del params[0]  # Skip self or cls
    del params[0]  # skip InteractionContext
    ret = {}
    for x in params:
        ret[x.name] = {
            "required": x.default == inspect._empty,
            "default": x.default,
            "annotation": x.annotation,
            "kind": x.kind
        }
    return ret


def to_option_type(annotation):
    if annotation is str:
        return ApplicationCommandOptionType.STRING
    elif annotation is int:
        return ApplicationCommandOptionType.INTEGER
    elif annotation is bool:
        return ApplicationCommandOptionType.BOOLEAN
    elif annotation is User or annotation is GuildMember:
        return ApplicationCommandOptionType.USER
    elif annotation is Channel:
        return ApplicationCommandOptionType.CHANNEL
    elif annotation is Role:
        return ApplicationCommandOptionType.ROLE
    elif annotation is float:
        return ApplicationCommandOptionType.NUMBER
    else:
        raise NotImplementedError
