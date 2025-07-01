import sys
import logging
import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from fantasy_tools import FantasyBaseballTools
from fantasy_config import DEFAULT_CONFIG_PATH

def setup_logging():
    """Configure logging for the server."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='fantasy_baseball_server.log'
    )
    return logging.getLogger(__name__)

def create_server() -> Server:
    """Create and configure the MCP server with fantasy baseball tools."""
    logger = setup_logging()
    tools_instance = FantasyBaseballTools(logger=logger)
    app = Server("fantasy-baseball-agent")

    @app.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Handle tool calls by routing to appropriate implementation
        with comprehensive error handling.
        """
        try:
            logger.info(f"Calling tool: {name} with arguments: {arguments}")
            result_text = ""

            if name == "search_player":
                # Check for required arguments
                if 'name' not in arguments or not arguments.get('name'):
                    return [types.TextContent(
                        text="Error: 'name' parameter is required for player search",
                        type="text"
                    )]

                result = tools_instance.search_players(arguments.get('name', ''))

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    players = result.get("results", [])
                    result_text = "Search results:\n\n"
                    for player in players:
                        result_text += f"ID: {player.get('id')}\n"
                        result_text += f"Name: {player.get('fullName')}\n"
                        result_text += f"Position: {player.get('primaryPosition', {}).get('abbreviation', 'N/A')}\n"
                        result_text += f"Team: {player.get('currentTeam', {}).get('name', 'N/A')}\n\n"

                    if not players:
                        result_text = f"No players found matching '{arguments.get('name', '')}'"

            elif name == "get_player_profile":
                # Check for required arguments
                if 'player_id' not in arguments or not arguments.get('player_id'):
                    return [types.TextContent(
                        text="Error: 'player_id' parameter is required for player profile",
                        type="text"
                    )]

                # Convert player_id to int if it's a string
                player_id = arguments.get('player_id')
                if isinstance(player_id, str) and player_id.isdigit():
                    player_id = int(player_id)

                # Handle season parameter
                season = arguments.get('season')
                if season and isinstance(season, str) and season.isdigit():
                    season = int(season)

                result = tools_instance.get_player_data(
                    player_id,
                    season
                )

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    player = result.get("player", {})
                    result_text = f"Player Profile: {player.get('fullName', 'Unknown')}\n\n"
                    result_text += f"ID: {player.get('id')}\n"
                    result_text += f"Position: {player.get('primaryPosition', {}).get('abbreviation', 'N/A')}\n"
                    result_text += f"Team: {player.get('currentTeam', {}).get('name', 'N/A')}\n"
                    result_text += f"Bats: {player.get('batSide', {}).get('description', 'N/A')}\n"
                    result_text += f"Throws: {player.get('pitchHand', {}).get('description', 'N/A')}\n"

                    # Add stats if available
                    if "stats" in player:
                        result_text += "\nStatistics:\n"
                        for stat_group in player["stats"]:
                            group = stat_group.get("group", {}).get("displayName", "")
                            season = stat_group.get("season", "")
                            result_text += f"\n{group} ({season}):\n"

                            for stat in stat_group.get("splits", []):
                                stat_name = stat.get("stat", {})
                                for key, value in stat_name.items():
                                    result_text += f"  {key}: {value}\n"

            elif name == "recommend_daily_lineup":
                # Check for required arguments
                if 'player_ids' not in arguments or not arguments.get('player_ids'):
                    return [types.TextContent(
                        text="Error: 'player_ids' parameter is required for daily lineup recommendations",
                        type="text"
                    )]

                # Ensure player_ids is a list of integers
                player_ids = arguments.get('player_ids', [])
                if not isinstance(player_ids, list):
                    return [types.TextContent(
                        text="Error: 'player_ids' should be a list of player IDs",
                        type="text"
                    )]

                # Convert string IDs to integers if needed
                player_ids = [int(pid) if isinstance(pid, str) and pid.isdigit() else pid
                             for pid in player_ids]

                result = tools_instance.recommend_daily_lineup(player_ids)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    start = result.get("start", [])
                    bench = result.get("bench", [])

                    result_text = "Daily Lineup Recommendations:\n\n"
                    result_text += "PLAYERS TO START:\n"
                    for player in start:
                        result_text += f"- {player.get('name')} ({player.get('position')}, {player.get('team')})\n"

                    result_text += "\nPLAYERS TO BENCH:\n"
                    for player in bench:
                        result_text += f"- {player.get('name')} ({player.get('position')}, {player.get('team')})\n"

            elif name == "recommend_waiver_pickups":
                # Check for required arguments
                if 'available_player_ids' not in arguments or not arguments.get('available_player_ids'):
                    return [types.TextContent(
                        text="Error: 'available_player_ids' parameter is required for waiver pickup recommendations",
                        type="text"
                    )]

                # Ensure available_player_ids is a list
                available_player_ids = arguments.get('available_player_ids', [])
                if not isinstance(available_player_ids, list):
                    return [types.TextContent(
                        text="Error: 'available_player_ids' should be a list of player IDs",
                        type="text"
                    )]

                # Convert string IDs to integers if needed
                available_player_ids = [int(pid) if isinstance(pid, str) and pid.isdigit() else pid
                                      for pid in available_player_ids]

                result = tools_instance.identify_waiver_pickups(available_player_ids)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    recommendations = result.get("recommendations", [])

                    result_text = "Waiver Wire Pickup Recommendations:\n\n"
                    for i, player in enumerate(recommendations, 1):
                        result_text += f"{i}. {player.get('name')} ({player.get('position')}, {player.get('team')})\n"
                        result_text += f"   Reason: {player.get('reason')}\n\n"

            elif name == "evaluate_trade":
                # Check for required arguments
                if 'players_to_give' not in arguments or not arguments.get('players_to_give'):
                    return [types.TextContent(
                        text="Error: 'players_to_give' parameter is required for trade evaluation",
                        type="text"
                    )]
                if 'players_to_receive' not in arguments or not arguments.get('players_to_receive'):
                    return [types.TextContent(
                        text="Error: 'players_to_receive' parameter is required for trade evaluation",
                        type="text"
                    )]

                # Ensure parameters are lists
                players_to_give = arguments.get('players_to_give', [])
                players_to_receive = arguments.get('players_to_receive', [])

                if not isinstance(players_to_give, list) or not isinstance(players_to_receive, list):
                    return [types.TextContent(
                        text="Error: 'players_to_give' and 'players_to_receive' should be lists of player IDs",
                        type="text"
                    )]

                # Convert string IDs to integers if needed
                players_to_give = [int(pid) if isinstance(pid, str) and pid.isdigit() else pid
                                  for pid in players_to_give]
                players_to_receive = [int(pid) if isinstance(pid, str) and pid.isdigit() else pid
                                     for pid in players_to_receive]

                result = tools_instance.evaluate_trade(players_to_give, players_to_receive)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    giving = result.get("giving", [])
                    receiving = result.get("receiving", [])
                    assessment = result.get("assessment", "")

                    result_text = "Trade Evaluation:\n\n"
                    result_text += "PLAYERS YOU GIVE:\n"
                    for player in giving:
                        result_text += f"- {player.get('name')}\n"

                    result_text += "\nPLAYERS YOU RECEIVE:\n"
                    for player in receiving:
                        result_text += f"- {player.get('name')}\n"

                    result_text += f"\nASSESSMENT:\n{assessment}"

            elif name == "get_league_leaders":
                # Check for required arguments
                if 'stat_type' not in arguments or not arguments.get('stat_type'):
                    return [types.TextContent(
                        text="Error: 'stat_type' parameter is required for league leaders",
                        type="text"
                    )]

                # Handle season parameter
                season = arguments.get('season')
                if season and isinstance(season, str) and season.isdigit():
                    season = int(season)

                result = tools_instance.get_league_leaders(
                    arguments.get('stat_type', ''),
                    season
                )

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    leaders = result.get("leaders", [])
                    stat_type = result.get("stat_type", "")

                    result_text = f"{stat_type} Leaders:\n\n"
                    for i, leader in enumerate(leaders, 1):
                        player = leader.get('person', {})
                        team = leader.get('team', {})
                        value = leader.get('value')
                        result_text += f"{i}. {player.get('fullName')} ({team.get('name')}): {value}\n"

            elif name == "get_multiple_players_profiles":
                # Check for required arguments
                if 'player_ids' not in arguments or not arguments.get('player_ids'):
                    return [types.TextContent(
                        text="Error: 'player_ids' parameter is required for multiple player profiles",
                        type="text"
                    )]

                # Ensure player_ids is a list
                player_ids = arguments.get('player_ids', [])
                if not isinstance(player_ids, list):
                    return [types.TextContent(
                        text="Error: 'player_ids' should be a list of player IDs",
                        type="text"
                    )]

                # Convert string IDs to integers if needed
                player_ids = [int(pid) if isinstance(pid, str) and pid.isdigit() else pid
                            for pid in player_ids]

                # Handle season parameter
                season = arguments.get('season')
                if season and isinstance(season, str) and season.isdigit():
                    season = int(season)

                result = tools_instance.get_multiple_players_data(player_ids, season)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    players = result.get("players", [])
                    result_text = "Multiple Player Profiles:\n\n"

                    for player in players:
                        result_text += f"--- {player.get('fullName', 'Unknown')} ---\n"
                        result_text += f"ID: {player.get('id')}\n"
                        result_text += f"Position: {player.get('primaryPosition', {}).get('abbreviation', 'N/A')}\n"
                        result_text += f"Team: {player.get('currentTeam', {}).get('name', 'N/A')}\n"
                        result_text += f"Bats: {player.get('batSide', {}).get('description', 'N/A')}\n"
                        result_text += f"Throws: {player.get('pitchHand', {}).get('description', 'N/A')}\n"

                        # Add stats if available
                        if "stats" in player:
                            result_text += "\nStatistics:\n"
                            for stat_group in player["stats"]:
                                group = stat_group.get("group", {}).get("displayName", "")
                                season = stat_group.get("season", "")
                                result_text += f"\n{group} ({season}):\n"

                                for stat in stat_group.get("splits", []):
                                    stat_name = stat.get("stat", {})
                                    for key, value in stat_name.items():
                                        result_text += f"  {key}: {value}\n"

                        result_text += "\n\n"  # Add extra spacing between player profiles

            elif name == "search_multiple_players":
                # Check for required arguments
                if 'names' not in arguments or not arguments.get('names'):
                    return [types.TextContent(
                        text="Error: 'names' parameter is required for multiple player search",
                        type="text"
                    )]

                # Ensure names is a list
                names = arguments.get('names', [])
                if not isinstance(names, list):
                    return [types.TextContent(
                        text="Error: 'names' should be a list of player names",
                        type="text"
                    )]

                result = tools_instance.search_multiple_players(names)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    all_results = result.get("results", {})
                    result_text = "Multiple Player Search Results:\n\n"

                    for name, players in all_results.items():
                        result_text += f"=== SEARCH RESULTS FOR '{name}' ===\n"

                        if not players:
                            result_text += f"No players found matching '{name}'\n\n"
                            continue

                        for player in players:
                            result_text += f"ID: {player.get('id')}\n"
                            result_text += f"Name: {player.get('fullName')}\n"
                            result_text += f"Position: {player.get('primaryPosition', {}).get('abbreviation', 'N/A')}\n"
                            result_text += f"Team: {player.get('currentTeam', {}).get('name', 'N/A')}\n\n"

                        result_text += "\n"  # Add extra spacing between search results

            elif name == "read_league_config":
                # Check for required arguments
                
                result = tools_instance.get_fantasy_config(DEFAULT_CONFIG_PATH)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    config = result.get("config", {})
                    league_name = config.get("league_name", "Unnamed League")
                    teams = config.get("teams", [])

                    result_text = f"Fantasy League Configuration: {league_name}\n\n"
                    result_text += f"Number of Teams: {len(teams)}\n\n"

                    for i, team in enumerate(teams, 1):
                        team_name = team.get("name", f"Team {i}")
                        hitters = team.get("hitters", [])
                        pitchers = team.get("pitchers", [])

                        result_text += f"Team {i}: {team_name}\n"
                        result_text += f"  Hitters: {len(hitters)}\n"
                        result_text += f"  Pitchers: {len(pitchers)}\n\n"

            elif name == "get_team_roster":
                # Check for required arguments
                if 'team_name' not in arguments:
                    return [types.TextContent(
                        text="Error: 'team_name' parameter is required",
                        type="text"
                    )]

                team_name = arguments.get('team_name')

                result = tools_instance.get_team_roster(team_name, DEFAULT_CONFIG_PATH)

                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    team_name = result.get("team_name", "Unknown Team")
                    hitters = result.get("hitters", [])
                    pitchers = result.get("pitchers", [])

                    result_text = f"Team Roster: {team_name}\n\n"

                    result_text += "HITTERS:\n"
                    for i, hitter in enumerate(hitters, 1):
                        result_text += f"{i}. {hitter}\n"

                    result_text += "\nPITCHERS:\n"
                    for i, pitcher in enumerate(pitchers, 1):
                        result_text += f"{i}. {pitcher}\n"

            elif name == "search_team":
                # Check for required arguments
                if 'team_name' not in arguments or not arguments.get('team_name'):
                    return [types.TextContent(
                        text="Error: 'team_name' parameter is required for team search",
                        type="text"
                    )]
                
                team_name = arguments.get('team_name')
                result = tools_instance.search_team(team_name)
                
                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    teams = result.get("results", [])
                    result_text = "Team Search Results:\n\n"
                    
                    if not teams:
                        result_text += f"No teams found matching '{team_name}'\n"
                    else:
                        for team in teams:
                            result_text += f"ID: {team.get('id')}\n"
                            result_text += f"Name: {team.get('name')}\n"
                            result_text += f"Location: {team.get('locationName')}\n"
                            result_text += f"Team Name: {team.get('teamName')}\n"
                            result_text += f"League: {team.get('league', {}).get('name', 'N/A')}\n"
                            result_text += f"Division: {team.get('division', {}).get('name', 'N/A')}\n\n"

            elif name == "get_mlb_roster":
                # Check for required arguments
                if 'team_id' not in arguments or not arguments.get('team_id'):
                    return [types.TextContent(
                        text="Error: 'team_id' parameter is required for MLB roster",
                        type="text"
                    )]
                
                # Convert team_id to int if it's a string
                team_id = arguments.get('team_id')
                if isinstance(team_id, str) and team_id.isdigit():
                    team_id = int(team_id)
                
                # Handle season parameter
                season = arguments.get('season')
                if season and isinstance(season, str) and season.isdigit():
                    season = int(season)
                
                result = tools_instance.get_mlb_roster(team_id, season)
                
                if "error" in result:
                    result_text = f"Error: {result['error']}"
                else:
                    team_name = result.get("team_name", "Unknown")
                    roster = result.get("roster", {})
                    
                    result_text = f"MLB Team Roster: {team_name} (ID: {result.get('team_id')})\n"
                    result_text += f"Season: {result.get('season')}\n"
                    result_text += f"Total Players: {result.get('total_players')}\n\n"
                    
                    # Output by position groups
                    for position, players in roster.items():
                        if players:
                            position_name = position.replace('_', ' ').title()
                            result_text += f"{position_name} ({len(players)}):\n"
                            
                            for player in players:
                                jersey = f"#{player.get('jersey')}" if player.get('jersey') else ""
                                result_text += f"- {player.get('name')} {jersey} ({player.get('position', 'N/A')})\n"
                            
                            result_text += "\n"

            else:
                raise ValueError(f"Unknown tool: {name}")

            logger.info(f"Tool {name} executed successfully")
            return [types.TextContent(text=result_text, type="text")]

        except Exception as e:
            logger.error(f"Tool call failed: {e}", exc_info=True)
            return [types.TextContent(
                text=f"Error: Tool call failed - {e}",
                type="text"
            )]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List all available fantasy baseball tools."""
        logger.info("Listing tools")
        return [
            types.Tool(
                name="search_player",
                description="Search for players by name",
                inputSchema={
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Player name to search for",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_player_profile",
                description="Get comprehensive player profile and statistics",
                inputSchema={
                    "type": "object",
                    "required": ["player_id"],
                    "properties": {
                        "player_id": {
                            "type": ["integer", "string"],
                            "description": "MLB player ID",
                        },
                        "season": {
                            "type": ["integer", "string"],
                            "description": "Season year (default: 2025)",
                        }
                    },
                },
            ),
            types.Tool(
                name="recommend_daily_lineup",
                description="Get recommendations for which players to start in daily lineup",
                inputSchema={
                    "type": "object",
                    "required": ["player_ids"],
                    "properties": {
                        "player_ids": {
                            "type": "array",
                            "items": {
                                "type": ["integer", "string"]
                            },
                            "description": "List of player IDs in your roster",
                        }
                    },
                },
            ),
            types.Tool(
                name="recommend_waiver_pickups",
                description="Get recommendations for waiver wire pickups",
                inputSchema={
                    "type": "object",
                    "required": ["available_player_ids"],
                    "properties": {
                        "available_player_ids": {
                            "type": "array",
                            "items": {
                                "type": ["integer", "string"]
                            },
                            "description": "List of player IDs available on the waiver wire",
                        }
                    },
                },
            ),
            types.Tool(
                name="evaluate_trade",
                description="Evaluate a potential trade between fantasy teams",
                inputSchema={
                    "type": "object",
                    "required": ["players_to_give", "players_to_receive"],
                    "properties": {
                        "players_to_give": {
                            "type": "array",
                            "items": {
                                "type": ["integer", "string"]
                            },
                            "description": "List of player IDs you are giving up in the trade",
                        },
                        "players_to_receive": {
                            "type": "array",
                            "items": {
                                "type": ["integer", "string"]
                            },
                            "description": "List of player IDs you are receiving in the trade",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_league_leaders",
                description="Get league leaders for a specific statistic",
                inputSchema={
                    "type": "object",
                    "required": ["stat_type"],
                    "properties": {
                        "stat_type": {
                            "type": "string",
                            "description": "Statistic to get leaders for (e.g., homeRuns, battingAverage)",
                        },
                        "season": {
                            "type": ["integer", "string"],
                            "description": "Season year (default: 2025)",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_multiple_players_profiles",
                description="Get comprehensive profiles and statistics for multiple players in a single call",
                inputSchema={
                    "type": "object",
                    "required": ["player_ids"],
                    "properties": {
                        "player_ids": {
                            "type": "array",
                            "items": {
                                "type": ["integer", "string"]
                            },
                            "description": "List of MLB player IDs",
                        },
                        "season": {
                            "type": ["integer", "string"],
                            "description": "Season year (default: 2025)",
                        }
                    },
                },
            ),
            types.Tool(
                name="search_multiple_players",
                description="Search for multiple players by name in a single call",
                inputSchema={
                    "type": "object",
                    "required": ["names"],
                    "properties": {
                        "names": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of player names to search for",
                        }
                    },
                },
            ),# New tools to add to the list_tools() function
            types.Tool(
                name="create_league_config",
                description="Create a new league configuration file",
                inputSchema={
                    "type": "object",
                    "required": ["config_path", "league_name", "team_name", "hitters", "pitchers"],
                    "properties": {
                        "config_path": {
                            "type": "string",
                            "description": "Path where to save the configuration file",
                        },
                        "league_name": {
                            "type": "string",
                            "description": "Name of the fantasy league",
                        },
                        "team_name": {
                            "type": "string",
                            "description": "Name of your team",
                        },
                        "hitters": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of hitter names in your team",
                        },
                        "pitchers": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of pitcher names in your team",
                        }
                    },
                },
            ),
            types.Tool(
                name="read_league_config",
                description="Read a league configuration file",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="update_team_roster",
                description="Update a team's roster in a league configuration",
                inputSchema={
                    "type": "object",
                    "required": ["config_path", "league_name", "team_name"],
                    "properties": {
                        "config_path": {
                            "type": "string",
                            "description": "Path to the configuration file",
                        },
                        "league_name": {
                            "type": "string",
                            "description": "Name of the fantasy league",
                        },
                        "team_name": {
                            "type": "string",
                            "description": "Name of the team to update",
                        },
                        "hitters": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of hitter names for the team",
                        },
                        "pitchers": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "List of pitcher names for the team",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_team_roster",
                description="Get a team's roster from a league configuration",
                inputSchema={
                    "type": "object",
                    "required": ["team_name"],
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "Name of the team",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_mlb_roster",
                description="Get an MLB team's roster given the team ID and year",
                inputSchema={
                   "type": "object",
                   "required": ["team_id"],
                   "properties": {
                       "team_id": {
                           "type": ["string" ,"integer"],
                           "description": "Number ID of the team"
                       },
                       "season": {
                            "type": ["integer", "string"],
                            "description": "Season year (default: 2025)",
                        }
                   }
                }
            ),
            types.Tool(
                name="search_team",
                description="Get an MLB's team ID given the name of the team",
                inputSchema={
                    "type": "object",
                    "required": ["team_name"],
                    "properties": {
                        "team_name": {
                            "type": ["integer", "string"],
                            "description": "MLB official Team name"
                        }
                    }
                }
            )
        ]

    return app

def main() -> int:
    """Entry point for the Fantasy Baseball MCP server."""
    logger = setup_logging()  # Fixed: Get logger instance

    try:
        logger.info("Starting Fantasy Baseball MCP Server...")
        print("Starting Fantasy Baseball MCP Server...", file=sys.stderr)

        app = create_server()

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0],
                    streams[1],
                    app.create_initialization_options()
                )

        anyio.run(arun)
        return 0

    except Exception as e:
        logger.error(f"Server startup failed: {e}", exc_info=True)
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())