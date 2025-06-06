# Data Analytics MCP Servers

This document provides a list of pre-configured MCP servers for Data Analytics tasks that are included with the `aurite` package. The servers listed below are defined in the `config/mcp_servers/data_analytics_servers.json` file.

## Available Servers

### `game_trends_mcp`

*   **Description**: A server that provides tools to get real-time data about trending, top-selling, and most-played games from Steam and Epic Games.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `get_steam_trending_games` | Shows currently trending games on Steam with live data |
| `get_steam_top_sellers` | Displays top-selling games on Steam with real sales data |
| `get_steam_most_played` | Shows real-time most played games on Steam with current player counts |
| `get_epic_free_games` | Shows current and upcoming free games on Epic Games Store |
| `get_epic_trending_games` | Shows trending games on Epic Games Store |
| `get_all_trending_games` | Provides comprehensive trending games data from both Steam and Epic Games platforms |
| `get_api_health` | Checks the health status of the Gaming Trend Analytics API |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "game_trends_mcp"}' "Use the 'get_all_trending_games' tool"
```

### `healthcare_mcp_public`

*   **Description**: A server that provides tools to access public healthcare data from the FDA, PubMed, and other sources.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `fda_drug_lookup` | Looks up drug information from FDA database |
| `pubmed_search` | Searches medical literature in PubMed |
| `health_topics` | Gets evidence-based health information |
| `clinical_trials_search` | Searches for clinical trials |
| `lookup_icd_code` | Looks up ICD-10 codes |
| `get_usage_stats` | Shows API usage statistics for current session |
| `get_all_usage_stats` | Shows API usage statistics across all sessions |

**Exclusions:**
The `clinical_trials_search` and `lookup_icd_code` tools are currently excluded due to intermittent server-side errors.

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "healthcare_mcp_public"}' "Use the 'fda_drug_lookup' tool to look up 'aspirin'"
```

### `national_weather_service`

*   **Description**: A server that provides access to weather data from the US National Weather Service.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `get_current_weather` | Gets current weather conditions for any US location |
| `get_weather_forecast` | Provides multi-day weather forecast (up to 7 days) |
| `get_hourly_forecast` | Shows hour-by-hour weather forecast (up to 48 hours) |
| `get_weather_alerts` | Shows active weather alerts, warnings, watches, and advisories |
| `find_weather_stations` | Locates nearby weather observation stations |
| `get_local_time` | Shows current local time for a US location |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "national_weather_service"}' "Use the 'get_current_weather' tool to get the current weather for location '40.7128,-74.0060'"
```

**Relevant Agents:**
*   **`national_weather_service_agent`**: An agent that can answer questions about the weather using the national_weather_service server.
    *   **Configuration File**: `config/agents/data_analytics_agents.json`
