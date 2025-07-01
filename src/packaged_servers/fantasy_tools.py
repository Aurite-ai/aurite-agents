import os
import re
import logging
import json
import requests
import asyncio
from typing import Dict, List, Union, Any, Optional

from fantasy_config import FantasyConfigManager, DEFAULT_CONFIG_PATH

class FantasyBaseballTools:
    """Tools for Fantasy Baseball MCP server with MLB data integration"""

    # Standard MLB team mapping with common names/aliases and IDs
    MLB_TEAM_MAPPING = {
        # American League East
        "baltimore": 110, "orioles": 110, "baltimore orioles": 110,
        "boston": 111, "red sox": 111, "boston red sox": 111,
        "new york yankees": 147, "yankees": 147, "ny yankees": 147,
        "tampa bay": 139, "rays": 139, "tampa bay rays": 139,
        "toronto": 141, "blue jays": 141, "toronto blue jays": 141,
        
        # American League Central
        "chicago white sox": 145, "white sox": 145, "chw": 145,
        "cleveland": 114, "guardians": 114, "cleveland guardians": 114,
        "detroit": 116, "tigers": 116, "detroit tigers": 116,
        "kansas city": 118, "royals": 118, "kansas city royals": 118,
        "minnesota": 142, "twins": 142, "minnesota twins": 142,
        
        # American League West
        "houston": 117, "astros": 117, "houston astros": 117,
        "los angeles angels": 108, "angels": 108, "la angels": 108,
        "oakland": 133, "athletics": 133, "a's": 133, "oakland athletics": 133,
        "seattle": 136, "mariners": 136, "seattle mariners": 136,
        "texas": 140, "rangers": 140, "texas rangers": 140,
        
        # National League East
        "atlanta": 144, "braves": 144, "atlanta braves": 144,
        "miami": 146, "marlins": 146, "miami marlins": 146,
        "new york mets": 121, "mets": 121, "ny mets": 121,
        "philadelphia": 143, "phillies": 143, "philadelphia phillies": 143,
        "washington": 120, "nationals": 120, "washington nationals": 120,
        
        # National League Central
        "chicago cubs": 112, "cubs": 112, "chc": 112,
        "cincinnati": 113, "reds": 113, "cincinnati reds": 113,
        "milwaukee": 158, "brewers": 158, "milwaukee brewers": 158,
        "pittsburgh": 134, "pirates": 134, "pittsburgh pirates": 134,
        "st. louis": 138, "cardinals": 138, "st louis": 138, "st. louis cardinals": 138,
        
        # National League West
        "arizona": 109, "diamondbacks": 109, "d-backs": 109, "arizona diamondbacks": 109,
        "colorado": 115, "rockies": 115, "colorado rockies": 115,
        "los angeles dodgers": 119, "dodgers": 119, "la dodgers": 119,
        "san diego": 135, "padres": 135, "san diego padres": 135,
        "san francisco": 137, "giants": 137, "san francisco giants": 137
    }

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize FantasyBaseballTools with optional logging

        Args:
            logger (logging.Logger, optional): Logger for tracking operations
        """
        self.logger = logger or logging.getLogger(__name__)
        self.mlb_stats_api_url = "https://statsapi.mlb.com/api"
        # Add the config manager instance
        self.config_manager = FantasyConfigManager(logger=self.logger)

    # Add these new methods to the FantasyBaseballTools class
    def get_fantasy_config(self, config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
        """
        Get the fantasy baseball league configuration

        Args:
            config_path (str, optional): Path to the configuration file

        Returns:
            Dict containing the configuration or error information
        """
        return self.config_manager.read_config(config_path)

    def get_team_roster(self, team_name: str, config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
        """
        Get a team's roster from the fantasy league configuration

        Args:
            team_name (str): Name of the team to retrieve
            config_path (str, optional): Path to the configuration file

        Returns:
            Dict containing the team roster or error information
        """
        result = self.config_manager.get_team(team_name, config_path)
        if "error" in result:
            return result

        team = result["team"]
        return {
            "team_name": team.get("name", "Unknown"),
            "hitters": team.get("hitters", []),
            "pitchers": team.get("pitchers", [])
        }

    def get_mlb_roster(self, team_id: int, season: Optional[int] = 2025) -> Dict[str, Any]:
        """
        Get the main starting roster of an MLB team for a specified season

        Args:
            team_id (int): MLB team ID
            season (int, optional): Season year (default: 2025)

        Returns:
            Dict containing the team roster or error information
        """
        try:
            # Validate inputs
            if not isinstance(team_id, int) or team_id <= 0:
                return {"error": "Invalid team ID provided"}

            # Construct the URL for team roster
            url = f"{self.mlb_stats_api_url}/v1/teams/{team_id}/roster"
            params = {
                "season": season,
                "rosterType": "active"  # Get active roster (40-man roster also available)
            }

            # Make the request
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract team name and roster information
            if "roster" not in data:
                return {"error": f"No roster found for team ID {team_id} in season {season}"}

            # Get team details
            team_url = f"{self.mlb_stats_api_url}/v1/teams/{team_id}"
            team_response = requests.get(team_url)
            team_data = team_response.json()
            
            team_name = "Unknown"
            if "teams" in team_data and team_data["teams"]:
                team_name = team_data["teams"][0].get("name", "Unknown")

            # Organize players by position
            position_groups = {
                "pitchers": [],
                "catchers": [],
                "infielders": [],
                "outfielders": [],
                "designated_hitters": []
            }

            for player in data["roster"]:
                player_info = {
                    "id": player.get("person", {}).get("id"),
                    "name": player.get("person", {}).get("fullName"),
                    "jersey": player.get("jerseyNumber"),
                    "position": player.get("position", {}).get("abbreviation")
                }
                
                position = player.get("position", {}).get("type", "").lower()
                if position == "pitcher":
                    position_groups["pitchers"].append(player_info)
                elif position == "catcher":
                    position_groups["catchers"].append(player_info)
                elif position == "infielder":
                    position_groups["infielders"].append(player_info)
                elif position == "outfielder":
                    position_groups["outfielders"].append(player_info)
                elif position == "designated hitter":
                    position_groups["designated_hitters"].append(player_info)

            self.logger.info(f"Successfully retrieved roster for {team_name} (ID: {team_id})")
            return {
                "team_id": team_id,
                "team_name": team_name,
                "season": season,
                "roster": position_groups,
                "total_players": len(data["roster"])
            }

        except requests.RequestException as e:
            error_msg = f"API request error retrieving team roster: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error retrieving team roster: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def search_team(self, team_name: str) -> Dict[str, Any]:
        """
        Search for MLB teams by name and get their team IDs

        Args:
            team_name (str): Team name to search for (can be full name, city, or common nickname)

        Returns:
            Dict containing team search results or error information
        """
        try:
            # Method 1: Use the built-in mapping for quick lookup
            sanitized_name = team_name.lower().strip()
            
            # Check if the name is in our mapping
            if sanitized_name in self.MLB_TEAM_MAPPING:
                team_id = self.MLB_TEAM_MAPPING[sanitized_name]
                
                # Get the full team details from the API
                team_url = f"{self.mlb_stats_api_url}/v1/teams/{team_id}"
                team_response = requests.get(team_url)
                team_response.raise_for_status()
                team_data = team_response.json()
                
                if "teams" in team_data and team_data["teams"]:
                    team_info = team_data["teams"][0]
                    self.logger.info(f"Found team {team_info.get('name')} with ID {team_id} (direct mapping)")
                    return {"results": [team_info]}
            
            # Method 2: Use the API to search
            # Make request to MLB Stats API for team search
            url = f"{self.mlb_stats_api_url}/v1/teams"
            params = {"sportIds": 1}  # MLB is sport ID 1
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            teams = []
            if "teams" in data:
                # Filter teams based on the search term
                search_terms = sanitized_name.split()
                for team in data["teams"]:
                    # Check if any of the search terms are in the team name, location, or teamName fields
                    team_full = team.get("name", "").lower()
                    team_location = team.get("locationName", "").lower()
                    team_name = team.get("teamName", "").lower()
                    
                    for term in search_terms:
                        if (term in team_full or term in team_location or term in team_name):
                            teams.append(team)
                            break
            
            self.logger.info(f"Found {len(teams)} teams matching '{team_name}'")
            return {"results": teams}

        except requests.RequestException as e:
            error_msg = f"API request error during team search: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error in team search: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def search_players(self, name: str) -> Dict[str, Any]:
        """
        Search for MLB players by name

        Args:
            name (str): Player name to search for

        Returns:
            Dict containing search results or error information
        """
        try:
            # Sanitize input
            sanitized_name = re.sub(r'[^\w\s]', '', name)

            # Make request to MLB Stats API
            url = f"{self.mlb_stats_api_url}/v1/people/search"
            params = {"names": sanitized_name, "limit": 10}

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            players = data.get("people", [])
            self.logger.info(f"Found {len(players)} players matching '{name}'")

            return {"results": players}

        except requests.RequestException as e:
            error_msg = f"API request error during player search: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error in player search: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def search_multiple_players(self, names: List[str]) -> Dict[str, Any]:
        """
        Search for multiple MLB players by name in a single call

        Args:
            names (List[str]): List of player names to search for

        Returns:
            Dict containing search results or error information
        """
        try:
            if not names:
                return {"error": "No player names provided"}

            all_results = {}

            for name in names:
                # Sanitize input
                sanitized_name = re.sub(r'[^\w\s]', '', name)

                # Make request to MLB Stats API
                url = f"{self.mlb_stats_api_url}/v1/people/search"
                params = {"names": sanitized_name, "limit": 5}  # Limiting to 5 per player for readability

                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                players = data.get("people", [])
                self.logger.info(f"Found {len(players)} players matching '{name}'")

                all_results[name] = players

            self.logger.info(f"Successfully searched for {len(names)} player names")
            return {"results": all_results}

        except requests.RequestException as e:
            error_msg = f"API request error during multiple player search: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error in multiple player search: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def get_player_data(self, player_id: int, season: Optional[int] = 2025) -> Dict[str, Any]:
        """
        Get comprehensive player profile and statistics

        Args:
            player_id (int): MLB player ID
            season (int, optional): Season year (default: 2025)

        Returns:
            Dict containing player data or error information
        """
        try:
            # Get player info
            player_url = f"{self.mlb_stats_api_url}/v1/people/{player_id}"
            params = {"hydrate": "currentTeam,stats"}

            if season:
                params["season"] = season

            response = requests.get(player_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "people" not in data or not data["people"]:
                return {"error": f"No player found with ID {player_id}"}

            player_info = data["people"][0]

            # Get additional stats if not already included
            if "stats" not in player_info and season:
                stats_url = f"{self.mlb_stats_api_url}/v1/people/{player_id}/stats"
                stats_params = {
                    "stats": "season",
                    "season": season,
                    "group": "hitting,pitching,fielding"
                }

                stats_response = requests.get(stats_url, params=stats_params)
                stats_data = stats_response.json()
                player_info["stats"] = stats_data.get("stats", [])

            self.logger.info(f"Successfully retrieved data for player {player_id}")
            return {"player": player_info}

        except requests.RequestException as e:
            error_msg = f"API request error retrieving player data: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error retrieving player data: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def get_multiple_players_data(self, player_ids: List[int], season: Optional[int] = 2025) -> Dict[str, Any]:
        """
        Get comprehensive profiles and statistics for multiple players in a single call

        Args:
            player_ids (List[int]): List of MLB player IDs
            season (int, optional): Season year (default: 2025)

        Returns:
            Dict containing player data or error information
        """
        try:
            if not player_ids:
                return {"error": "No player IDs provided"}

            players_data = []
            for player_id in player_ids:
                # Get player info for each player
                result = self.get_player_data(player_id, season)
                if "player" in result:
                    players_data.append(result["player"])
                elif "error" in result:
                    self.logger.warning(f"Error fetching player {player_id}: {result['error']}")

            if not players_data:
                return {"error": "Could not retrieve data for any of the requested players"}

            self.logger.info(f"Successfully retrieved data for {len(players_data)} players")
            return {"players": players_data}

        except Exception as e:
            error_msg = f"Unexpected error retrieving multiple player data: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def get_league_leaders(self, stat_type: str, season: Optional[int] = 2025) -> Dict[str, Any]:
        """
        Get league leaders for a specific statistic

        Args:
            stat_type (str): Statistic to get leaders for (e.g., homeRuns, battingAverage)
            season (int, optional): Season year (default: 2025)

        Returns:
            Dict containing leader data or error information
        """
        try:
            # Map common terms to API stat types if needed
            stat_mapping = {
                "hr": "homeRuns",
                "avg": "battingAverage",
                "rbi": "rbi",
                "sb": "stolenBases",
                "wins": "wins",
                "era": "earnedRunAverage",
                "so": "strikeOuts",
                "whip": "whip"
                # Add more mappings as needed
            }

            # Use mapping if available, otherwise use as-is
            actual_stat = stat_mapping.get(stat_type.lower(), stat_type)

            # Set up parameters
            params = {
                "leaderCategories": actual_stat,
                "limit": 10
            }

            if season:
                params["season"] = season

            # Make request
            url = f"{self.mlb_stats_api_url}/v1/stats/leaders"
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract leader data
            leader_data = []
            if "leagueLeaders" in data:
                for category in data["leagueLeaders"]:
                    if category.get("leaderCategory") == actual_stat:
                        leader_data = category.get("leaders", [])
                        break

            self.logger.info(f"Retrieved {len(leader_data)} leaders for {actual_stat}")
            return {"leaders": leader_data, "stat_type": actual_stat}

        except requests.RequestException as e:
            error_msg = f"API request error retrieving league leaders: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Unexpected error retrieving league leaders: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def recommend_daily_lineup(self, player_ids: List[int]) -> Dict[str, Any]:
        """
        Get recommendations for which players to start in daily lineup

        Args:
            player_ids (List[int]): List of player IDs in your roster

        Returns:
            Dict containing recommendations or error information
        """
        try:
            if not player_ids:
                return {"error": "No player IDs provided"}

            # Get data for all players
            player_data = []
            for player_id in player_ids:
                result = self.get_player_data(player_id)
                if "player" in result:
                    player_data.append(result["player"])

            # This is where we would implement complex lineup optimization logic
            # For now, using a simple placeholder recommendation system
            start_recommendations = []
            bench_recommendations = []

            for player in player_data:
                # Placeholder logic - in a real implementation, we would use recent performance,
                # matchups, ballpark factors, etc.
                player_info = {
                    "id": player.get("id"),
                    "name": player.get("fullName"),
                    "position": player.get("primaryPosition", {}).get("abbreviation", "Unknown"),
                    "team": player.get("currentTeam", {}).get("name", "Unknown")
                }

                # Simple alternating recommendation for demo purposes
                if len(start_recommendations) < len(player_data) * 0.7:
                    start_recommendations.append(player_info)
                else:
                    bench_recommendations.append(player_info)

            self.logger.info(f"Generated lineup recommendations for {len(player_data)} players")
            return {
                "start": start_recommendations,
                "bench": bench_recommendations
            }

        except Exception as e:
            error_msg = f"Error generating lineup recommendations: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def identify_waiver_pickups(self, available_player_ids: List[int]) -> Dict[str, Any]:
        """
        Get recommendations for waiver wire pickups

        Args:
            available_player_ids (List[int]): List of player IDs available on the waiver wire

        Returns:
            Dict containing recommendations or error information
        """
        try:
            if not available_player_ids:
                return {"error": "No player IDs provided"}

            # Get data for available players
            available_players = []
            for player_id in available_player_ids:
                result = self.get_player_data(player_id)
                if "player" in result:
                    available_players.append(result["player"])

            # Placeholder recommendation logic
            recommendations = []

            for player in available_players[:5]:  # Limit to top 5 for example
                player_info = {
                    "id": player.get("id"),
                    "name": player.get("fullName"),
                    "position": player.get("primaryPosition", {}).get("abbreviation", "Unknown"),
                    "team": player.get("currentTeam", {}).get("name", "Unknown"),
                    "reason": "Recent strong performance" # Placeholder
                }
                recommendations.append(player_info)

            self.logger.info(f"Generated waiver pickup recommendations from {len(available_players)} players")
            return {"recommendations": recommendations}

        except Exception as e:
            error_msg = f"Error generating waiver pickup recommendations: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}

    def evaluate_trade(self, players_to_give: List[int], players_to_receive: List[int]) -> Dict[str, Any]:
        """
        Evaluate a potential trade between fantasy teams

        Args:
            players_to_give (List[int]): List of player IDs you are giving up in the trade
            players_to_receive (List[int]): List of player IDs you are receiving in the trade

        Returns:
            Dict containing trade evaluation or error information
        """
        try:
            if not players_to_give or not players_to_receive:
                return {"error": "Invalid trade parameters"}

            # Get data for all players involved
            giving_players = []
            for player_id in players_to_give:
                result = self.get_player_data(player_id)
                if "player" in result:
                    giving_players.append(result["player"])

            receiving_players = []
            for player_id in players_to_receive:
                result = self.get_player_data(player_id)
                if "player" in result:
                    receiving_players.append(result["player"])

            # Placeholder trade evaluation logic - in a real implementation,
            # we would compare stats, positions, team needs, etc.
            giving_value = len(giving_players) * 10  # Placeholder value
            receiving_value = len(receiving_players) * 10  # Placeholder value

            assessment = ""
            if receiving_value > giving_value * 1.1:
                assessment = "This trade is favorable for you."
            elif giving_value > receiving_value * 1.1:
                assessment = "This trade is unfavorable for you."
            else:
                assessment = "This trade is relatively even."

            self.logger.info(f"Evaluated trade with {len(giving_players)} players given and {len(receiving_players)} received")
            return {
                "giving": [{"id": p.get("id"), "name": p.get("fullName")} for p in giving_players],
                "receiving": [{"id": p.get("id"), "name": p.get("fullName")} for p in receiving_players],
                "assessment": assessment
            }

        except Exception as e:
            error_msg = f"Error evaluating trade: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}