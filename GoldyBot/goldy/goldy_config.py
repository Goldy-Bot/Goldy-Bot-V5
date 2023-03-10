from __future__ import annotations

from typing import List, Tuple

from ..config import Config
from ..errors import GoldyBotError

class GoldyConfig(Config):
    """
    Class that allows you to retrieve configuration data from the ``goldy.json`` config file.

    All properties return None when not found in the config.
    """
    def __init__(self):
        try:
            super().__init__("./goldy.json")
        except FileNotFoundError as e:
            raise GoldyBotError(
                f"Goldy config not found in root! Please generate one by creating an environment with the command 'goldybot setup' in terminal. \nERROR -> {e}"
            )

    @property
    def ignored_extensions(self) -> List[str]:
        """Returns code name of all ignored extensions from ``goldy.json``."""
        return self.get("goldy", "extensions", "ignored_extensions")

    @property
    def extension_folder_location(self) -> str:
        """Returns location set for the extension folder in ``goldy.json``."""
        return self.get("goldy", "extensions", "folder_location")

    @property
    def raise_on_extension_loader_error(self) -> bool:
        """Returns whether the extension loader should raise on load errors stopping the entire framework or not."""
        return self.get("goldy", "extensions", "raise_on_load_error", default_value=True)

    @property
    def allowed_guilds(self) -> List[Tuple[str, str]]:
        """Returns list of tuples including ``guild id`` and ``guild code name`` that are allowed to operate in goldy bot."""
        tuple_list = []
        data = self.get("goldy", "allowed_guilds")

        if data is None:
            raise GoldyBotError(
                "allowed_guilds was not specified in goldy.json. Please don't alter this json file."
            )

        # Removes template from dict if it exists.
        if "{guild_id_here}" in data:
            del data["{guild_id_here}"]
        
        # Append each allowed guild as tuple.
        for key in data:
            tuple_list.append((key, data[key]))

        return tuple_list