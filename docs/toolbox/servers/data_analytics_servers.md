# Data Analytics MCP Servers

This document provides a list of pre-configured MCP servers for Data Analytics tasks that are included with the `aurite` package. The servers listed below are defined in the `config/mcp_servers/data_analytics_servers.json` file.

## Available Servers

### `game_trends_mcp`

*   **Description**: A server that provides tools to get real-time data about trending, top-selling, and most-played games from Steam and Epic Games.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**

| Tool Name | Description |
| --- | --- |
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

**Relevant Agents:**
*   **`game_trends_agent`**: An agent that can answer questions about video game trends using the game_trends_mcp server.
    *   **Configuration File**: `config/agents/data_analytics_agents.json`

### `healthcare_mcp_public`

*   **Description**: A server that provides tools to access public healthcare data from the FDA, PubMed, and other sources.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**

| Tool Name | Description |
| --- | --- |
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

**Relevant Agents:**
*   **`healthcare_agent`**: An agent that can answer questions about healthcare using the healthcare_mcp_public server.
    *   **Configuration File**: `config/agents/data_analytics_agents.json`

### `national_weather_service`

*   **Description**: A server that provides access to weather data from the US National Weather Service.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**

| Tool Name | Description |
| --- | --- |
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

### `pubmed_mcp_server`

*   **Description**: A server that provides tools to search for and retrieve articles from PubMed.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**

| Tool Name | Description |
| --- | --- |
| `search_pubmed_key_words` | Searches PubMed using keywords |
| `search_pubmed_advanced` | Performs advanced PubMed search with multiple criteria |
| `get_pubmed_article_metadata` | Retrieves metadata for a specific PubMed article |
| `download_pubmed_pdf` | Downloads PDF of a PubMed article |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "pubmed_mcp_server"}' "Use the 'search_pubmed_key_words' tool to search for 'cancer treatment'"
```

**Relevant Agents:**
*   **`pubmed_agent`**: An agent that can search for and retrieve articles from PubMed.
    *   **Configuration File**: `config/agents/data_analytics_agents.json`

### `appinsightmcp`

*   **Description**: A server that provides tools to search for and retrieve information about apps from the Apple App Store and Google Play Store.
*   **Configuration File**: `config/mcp_servers/data_analytics_servers.json`

**Tools:**

| Tool Name | Description |
| --- | --- |
| `app-store-search` | Search for apps |
| `app-store-details` | Get detailed app information |
| `app-store-reviews` | Get app reviews |
| `app-store-similar` | Find similar apps |
| `app-store-developer` | Get apps by a developer |
| `app-store-suggest` | Get search suggestions |
| `app-store-ratings` | Get app ratings |
| `app-store-version-history` | Get app version history |
| `app-store-privacy` | Get app privacy details |
| `app-store-list` | Get apps from iTunes collections (top charts, new apps, etc.) |
| `google-play-search` | Search for apps |
| `google-play-details` | Get detailed app information |
| `google-play-reviews` | Get app reviews |
| `google-play-similar` | Find similar apps |
| `google-play-developer` | Get apps by a developer |
| `google-play-suggest` | Get search suggestions |
| `google-play-permissions` | Get app permissions |
| `google-play-datasafety` | Get data safety information |
| `google-play-categories` | Get list of all categories |
| `google-play-list` | Get apps from collections (top charts) |

**Example Usage:**
```
python tests/functional_mcp_client.py '{"name": "appinsightmcp"}' "Use the 'app-store-search' tool to search for 'twitter'"
```

**Relevant Agents:**
*   **`app_insight_agent`**: An agent that can answer questions about mobile apps using the appinsightmcp server.
    *   **Configuration File**: `config/agents/data_analytics_agents.json`
