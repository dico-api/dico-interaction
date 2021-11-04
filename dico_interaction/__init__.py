"""
dico-interaction
~~~~~~~~~~~~~~~~~~~~~~~~
Interaction module for dico.
:copyright: (c) 2021 dico-api
:license: MIT
"""

from .client import InteractionClient
from .command import InteractionCommand, AutoComplete, autocomplete
from .component import ComponentCallback
from .context import InteractionContext
from .deco import command, slash, context_menu, component_callback, checks, option
from .webserver import InteractionWebserver

__version__ = "0.0.6"
