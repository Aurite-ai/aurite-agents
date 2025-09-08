#!/usr/bin/env python3
"""
Test function for custom agent evaluation.

This file contains a 'run' function that simulates different quality levels
of weather agent responses for testing the run_agent functionality.
"""


def run(input_text: str, quality_level: str = "good") -> str:
    """
    Simulate a weather agent with different quality levels.

    Args:
        input_text: The user input to process
        quality_level: Quality level ("good", "average", "poor")

    Returns:
        Simulated agent response
    """

    if quality_level == "good":
        if "weather" in input_text.lower() and "san francisco" in input_text.lower():
            return """=== FULL CONVERSATION HISTORY ===
USER: What's the weather in San Francisco and create a plan for outdoor activities

TOOL CALL: weather_lookup
ARGUMENTS: {"location": "San Francisco, CA"}

TOOL RESPONSE (weather_lookup): {"location": "San Francisco, CA", "temperature": 68, "condition": "Partly Cloudy", "humidity": 65, "wind_speed": 12}

TOOL CALL: create_plan
ARGUMENTS: {"title": "San Francisco Outdoor Activities Plan", "activities": ["Golden Gate Park walk", "Pier 39 visit", "Outdoor lunch at Dolores Park"]}

TOOL RESPONSE (create_plan): {"plan_id": "sf_outdoor_123", "status": "created"}

TOOL CALL: save_plan
ARGUMENTS: {"plan_id": "sf_outdoor_123"}

TOOL RESPONSE (save_plan): {"status": "saved", "plan_id": "sf_outdoor_123"}

ASSISTANT: Great! I've checked the weather in San Francisco and created a perfect outdoor activity plan for you.

**Current Weather in San Francisco:**
- Temperature: 68°F
- Condition: Partly Cloudy
- Humidity: 65%
- Wind Speed: 12 mph

The weather is ideal for outdoor activities! I've created and saved a comprehensive plan that includes:

1. **Golden Gate Park Walk** - Perfect for the mild temperature and partly cloudy skies
2. **Pier 39 Visit** - Great for sightseeing with good visibility
3. **Outdoor Lunch at Dolores Park** - Enjoy the pleasant weather while dining outside

The plan has been saved with ID: sf_outdoor_123 for your reference. Have a wonderful time exploring San Francisco!

=== FINAL RESPONSE ===
Great! I've checked the weather in San Francisco and created a perfect outdoor activity plan for you.

**Current Weather in San Francisco:**
- Temperature: 68°F
- Condition: Partly Cloudy
- Humidity: 65%
- Wind Speed: 12 mph

The weather is ideal for outdoor activities! I've created and saved a comprehensive plan that includes:

1. **Golden Gate Park Walk** - Perfect for the mild temperature and partly cloudy skies
2. **Pier 39 Visit** - Great for sightseeing with good visibility
3. **Outdoor Lunch at Dolores Park** - Enjoy the pleasant weather while dining outside

The plan has been saved with ID: sf_outdoor_123 for your reference. Have a wonderful time exploring San Francisco!"""

        elif "weather" in input_text.lower() and ("london" in input_text.lower() and "tokyo" in input_text.lower()):
            return """=== FULL CONVERSATION HISTORY ===
USER: Check the weather in London and Tokyo, then compare them

TOOL CALL: weather_lookup
ARGUMENTS: {"location": "London, UK"}

TOOL RESPONSE (weather_lookup): {"location": "London, UK", "temperature": 45, "condition": "Rainy", "humidity": 85, "wind_speed": 15}

TOOL CALL: weather_lookup
ARGUMENTS: {"location": "Tokyo, Japan"}

TOOL RESPONSE (weather_lookup): {"location": "Tokyo, Japan", "temperature": 72, "condition": "Sunny", "humidity": 55, "wind_speed": 8}

ASSISTANT: I've checked the weather in both cities. Here's a detailed comparison:

**London, UK:**
- Temperature: 45°F
- Condition: Rainy
- Humidity: 85%
- Wind Speed: 15 mph

**Tokyo, Japan:**
- Temperature: 72°F
- Condition: Sunny
- Humidity: 55%
- Wind Speed: 8 mph

**Comparison:**
Tokyo is significantly warmer than London (72°F vs 45°F - a 27°F difference). Tokyo is enjoying sunny weather while London is experiencing rain. Tokyo also has much lower humidity (55% vs 85%) and calmer winds (8 mph vs 15 mph). Overall, Tokyo has much more pleasant weather conditions today compared to London's cold and wet conditions.

=== FINAL RESPONSE ===
I've checked the weather in both cities. Here's a detailed comparison:

**London, UK:**
- Temperature: 45°F
- Condition: Rainy
- Humidity: 85%
- Wind Speed: 15 mph

**Tokyo, Japan:**
- Temperature: 72°F
- Condition: Sunny
- Humidity: 55%
- Wind Speed: 8 mph

**Comparison:**
Tokyo is significantly warmer than London (72°F vs 45°F - a 27°F difference). Tokyo is enjoying sunny weather while London is experiencing rain. Tokyo also has much lower humidity (55% vs 85%) and calmer winds (8 mph vs 15 mph). Overall, Tokyo has much more pleasant weather conditions today compared to London's cold and wet conditions."""

    elif quality_level == "average":
        if "weather" in input_text.lower() and "san francisco" in input_text.lower():
            return """=== FULL CONVERSATION HISTORY ===
USER: What's the weather in San Francisco and create a plan for outdoor activities

TOOL CALL: weather_lookup
ARGUMENTS: {"location": "San Francisco"}

TOOL RESPONSE (weather_lookup): {"location": "San Francisco, CA", "temperature": 68, "condition": "Partly Cloudy", "humidity": 65, "wind_speed": 12}

ASSISTANT: I checked the weather in San Francisco and it's 68°F and partly cloudy. Here's a plan for outdoor activities:

1. Go to Golden Gate Park
2. Visit the pier
3. Have lunch outside

The weather looks good for being outdoors today!

=== FINAL RESPONSE ===
I checked the weather in San Francisco and it's 68°F and partly cloudy. Here's a plan for outdoor activities:

1. Go to Golden Gate Park
2. Visit the pier
3. Have lunch outside

The weather looks good for being outdoors today!"""

        elif "weather" in input_text.lower() and ("london" in input_text.lower() and "tokyo" in input_text.lower()):
            return """=== FULL CONVERSATION HISTORY ===
USER: Check the weather in London and Tokyo, then compare them

TOOL CALL: weather_lookup
ARGUMENTS: {"location": "London"}

TOOL RESPONSE (weather_lookup): {"location": "London, UK", "temperature": 45, "condition": "Rainy", "humidity": 85, "wind_speed": 15}

TOOL CALL: weather_lookup
ARGUMENTS: {"location": "Tokyo"}

TOOL RESPONSE (weather_lookup): {"location": "Tokyo, Japan", "temperature": 72, "condition": "Sunny", "humidity": 55, "wind_speed": 8}

ASSISTANT: London is 45°F and rainy. Tokyo is 72°F and sunny. Tokyo is warmer and has better weather than London.

=== FINAL RESPONSE ===
London is 45°F and rainy. Tokyo is 72°F and sunny. Tokyo is warmer and has better weather than London."""

    elif quality_level == "poor":
        if "weather" in input_text.lower():
            return (
                """=== FULL CONVERSATION HISTORY ===
USER: """
                + input_text
                + """

ASSISTANT: Weather can vary a lot depending on the location and time of year. Different cities have different climates and weather patterns.

=== FINAL RESPONSE ===
Weather can vary a lot depending on the location and time of year. Different cities have different climates and weather patterns."""
            )

    # Default fallback
    return f"I received your input: {input_text}. Quality level: {quality_level}"
