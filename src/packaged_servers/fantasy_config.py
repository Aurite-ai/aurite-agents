import os
import json
import logging
from typing import Dict, List, Any, Optional

# Default configuration file path
DEFAULT_CONFIG_PATH = "fantasy_league.json"

class FantasyConfigManager:
    """Manager for fantasy baseball league configuration file"""

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the configuration manager

        Args:
            logger (logging.Logger, optional): Logger for tracking operations
        """
        self.logger = logger or logging.getLogger(__name__)

    def read_config(self, config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
        """
        Read the fantasy baseball league configuration file

        Args:
            config_path (str): Path to the configuration file

        Returns:
            Dict containing the configuration or error information
        """
        try:
            if not os.path.exists(config_path):
                error_msg = f"Configuration file not found at {config_path}"
                self.logger.error(error_msg)
                return {"error": error_msg}

            with open(config_path, 'r') as file:
                config = json.load(file)

            # Validate basic structure
            if not isinstance(config, dict):
                return {"error": "Invalid configuration format"}

            if "teams" not in config or not isinstance(config["teams"], list):
                return {"error": "No teams found in configuration"}

            self.logger.info(f"Successfully read configuration from {config_path}")
            return {"config": config}

        except json.JSONDecodeError as e:
            error_msg = f"Error parsing configuration file: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error reading configuration: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def get_team(self, team_name: str, config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
        """
        Get a specific team's information from the configuration

        Args:
            team_name (str): Name of the team to retrieve
            config_path (str): Path to the configuration file

        Returns:
            Dict containing the team information or error information
        """
        try:
            result = self.read_config(config_path)
            if "error" in result:
                return result

            config = result["config"]

            for team in config.get("teams", []):
                if team.get("name") == team_name:
                    self.logger.info(f"Found team '{team_name}' in configuration")
                    return {"team": team}

            error_msg = f"Team '{team_name}' not found in configuration"
            self.logger.warning(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error getting team information: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}