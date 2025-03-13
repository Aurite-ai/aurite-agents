"""Weather tools for retrieving weather information from NWS API."""

from typing import Any, Dict, Optional
from dataclasses import dataclass
import httpx
import sys
import mcp.types as types

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


@dataclass
class AlertFeature:
    properties: Dict[str, str]


@dataclass
class ForecastPeriod:
    name: str
    temperature: float
    temperatureUnit: str
    windSpeed: str
    windDirection: str
    detailedForecast: str


async def make_nws_request(url: str) -> Optional[Dict[str, Any]]:
    """Make a request to the NWS API with proper error handling."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(30.0, connect=10.0)

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=timeout, limits=limits
    ) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data
        except httpx.TimeoutException:
            print("Error: Timeout accessing weather service", file=sys.stderr)
            return None
        except httpx.HTTPStatusError as e:
            print(
                f"Error: HTTP {e.response.status_code} from weather service",
                file=sys.stderr,
            )
            try:
                error_detail = e.response.json()
                print(f"Details: {error_detail}", file=sys.stderr)
            except:  # noqa: E722
                pass
            return None
        except httpx.RequestError:
            print("Error: Failed to connect to weather service", file=sys.stderr)
            return None
        except Exception as e:
            print(
                f"Error: Unexpected error accessing weather service: {e}",
                file=sys.stderr,
            )
            return None


def format_alert(feature: AlertFeature) -> str:
    """Format an alert feature into a readable string."""
    props = feature.properties
    return "\n".join(
        [
            f"Event: {props.get('event', 'Unknown')}",
            f"Area: {props.get('areaDesc', 'Unknown')}",
            f"Severity: {props.get('severity', 'Unknown')}",
            f"Status: {props.get('status', 'Unknown')}",
            f"Headline: {props.get('headline', 'No headline')}",
            "---",
        ]
    )


async def get_alerts(
    arguments: dict,
) -> list[Dict[str, Any]]:
    """Get weather alerts for a US state.

    Args:
        arguments: Dictionary containing:
            state (str): Two-letter US state code (e.g. CA, NY)

    Returns:
        List of content items containing the formatted alerts
    """
    if "state" not in arguments:
        raise ValueError("Missing required argument 'state'")

    state_code = arguments["state"].upper()
    url = f"{NWS_API_BASE}/alerts?area={state_code}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return [{"type": "text", "text": "Failed to retrieve alerts data"}]

    features = data["features"]
    if not features:
        return [{"type": "text", "text": f"No active alerts for {state_code}"}]

    alerts = [format_alert(AlertFeature(feature["properties"])) for feature in features]
    return [
        {
            "type": "text",
            "text": f"Active alerts for {state_code}:\n\n" + "\n".join(alerts),
        }
    ]


async def get_forecast(
    arguments: dict,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Get weather forecast for a location.

    Args:
        arguments: Dictionary containing:
            latitude (float): Latitude of the location (-90 to 90)
            longitude (float): Longitude of the location (-180 to 180)

    Returns:
        List of content items containing the formatted forecast
    """
    if "latitude" not in arguments or "longitude" not in arguments:
        raise ValueError("Missing required arguments 'latitude' and/or 'longitude'")

    latitude = float(arguments["latitude"])
    longitude = float(arguments["longitude"])

    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        return [
            types.TextContent(
                text="Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180.",
                type="text",
            )
        ]

    points_url = f"{NWS_API_BASE}/points/{latitude:.4f},{longitude:.4f}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return [
            types.TextContent(
                text=f"Failed to retrieve grid point data for coordinates: {latitude}, {longitude}. "
                "This location may not be supported by the NWS API (only US locations are supported).",
                type="text",
            )
        ]

    properties = points_data.get("properties", {})
    forecast_url = properties.get("forecast")

    if not forecast_url:
        if "detail" in points_data:
            return [
                types.TextContent(
                    text=f"API Error: {points_data['detail']}", type="text"
                )
            ]
        return [
            types.TextContent(
                text=f"No forecast URL found for coordinates: {latitude}, {longitude}. "
                "Location might be outside NWS coverage area.",
                type="text",
            )
        ]

    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return [
            types.TextContent(
                text=f"Failed to retrieve forecast data from {forecast_url}",
                type="text",
            )
        ]

    properties = forecast_data.get("properties", {})
    periods = properties.get("periods", [])

    if not periods:
        return [
            types.TextContent(
                text="No forecast periods available in the response", type="text"
            )
        ]

    forecasts = []
    for period in periods:
        try:
            forecast_period = ForecastPeriod(
                name=period.get("name", "Unknown"),
                temperature=period.get("temperature", 0),
                temperatureUnit=period.get("temperatureUnit", "F"),
                windSpeed=period.get("windSpeed", "Unknown"),
                windDirection=period.get("windDirection", ""),
                detailedForecast=period.get(
                    "detailedForecast", "No forecast available"
                ),
            )

            forecast_text = "\n".join(
                [
                    f"{forecast_period.name}:",
                    f"Temperature: {forecast_period.temperature}°{forecast_period.temperatureUnit}",
                    f"Wind: {forecast_period.windSpeed} {forecast_period.windDirection}",
                    f"{forecast_period.detailedForecast}",
                    "---",
                ]
            )
            forecasts.append(forecast_text)
        except Exception as e:
            print(f"Error: Failed to format forecast period: {e}", file=sys.stderr)
            continue

    if not forecasts:
        return [
            types.TextContent(text="Failed to format any forecast periods", type="text")
        ]

    forecast_text = f"Forecast for {latitude}, {longitude}:\n\n" + "\n".join(forecasts)
    return [types.TextContent(text=forecast_text, type="text")]
