import os
from typing import Optional

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("alpha-vantage")

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")


def _alpha_vantage_request(function: str, **params):
    """Make a request to the Alpha Vantage API with the given function and parameters.

    Args:
        function: The Alpha Vantage API function to call (e.g., 'TIME_SERIES_DAILY')
        **params: Additional parameters to include in the request

    Returns:
        dict: JSON response from the Alpha Vantage API
    """
    url_params = {"function": function, "apikey": API_KEY}

    url_params.update(params)

    r = requests.get(url="https://www.alphavantage.co/query", params=url_params)
    return r.json()


@mcp.tool()
def time_series_intraday(symbol: str, interval: str):
    """Returns raw (as-traded) intraday time series of the global equity specified

    Args:
        symbol (str): The name of the equity of your choice. For example: IBM
        interval (str): Time interval between two consecutive data points in the time series. The following values are supported: 1min, 5min, 15min, 30min, 60min
    """
    return _alpha_vantage_request("TIME_SERIES_DAILY", symbol=symbol, interval=interval)


@mcp.tool()
def time_series_daily(symbol: str):
    """Returns raw (as-traded) daily time series of the global equity specified

    Args:
        symbol (str): The name of the equity of your choice. For example: IBM
    """
    return _alpha_vantage_request("TIME_SERIES_DAILY", symbol=symbol)


@mcp.tool()
def time_series_weekly(symbol: str):
    """Returns raw (as-traded) weekly time series of the global equity specified

    Args:
        symbol (str): The name of the equity of your choice. For example: IBM
    """
    return _alpha_vantage_request("TIME_SERIES_WEEKLY", symbol=symbol)


@mcp.tool()
def time_series_monthly(symbol: str):
    """Returns raw (as-traded) monthly time series of the global equity specified

    Args:
        symbol (str): The name of the equity of your choice. For example: IBM
    """
    return _alpha_vantage_request("TIME_SERIES_MONTHLY", symbol=symbol)


@mcp.tool()
def market_news_sentiment(tickers: Optional[str] = None, topics: Optional[str] = None):
    """Returns live and historical market news & sentiment data from a large & growing selection of premier news outlets around the world, covering stocks, cryptocurrencies, forex, and a wide range of topics such as fiscal policy, mergers & acquisitions, IPOs, etc.

    Args:
        tickers (Optional[str]): The stock/crypto/forex symbols of your choice. For example: 'IBM' will filter for articles that mention the IBM ticker; 'COIN,CRYPTO:BTC,FOREX:USD' will filter for articles that simultaneously mention Coinbase (COIN), Bitcoin (CRYPTO:BTC), and US Dollar (FOREX:USD) in their content.
        topics (Optional[str]): The news topics of your choice. For example: 'technology' will filter for articles that write about the technology sector; 'technology,ipo' will filter for articles that simultaneously cover technology and IPO in their content. Supported topic: blockchain, earnings, ipo, mergers_and_acquisitions, financial_markets, economy_fiscal, economy_monetary, economy_macro, energy_transportation, finance, life_sciences, manufacturing, real_estate, retail_wholesale, technology
    """

    return _alpha_vantage_request("NEWS_SENTIMENT", tickers=tickers, topics=topics, sort="RELEVANCE", limit=3)


@mcp.tool()
def company_overview(symbol: str):
    """Returns the company information, financial ratios, and other key metrics for the equity specified. Data is generally refreshed on the same day a company reports its latest earnings and financials.

    Args:
        symbol (str): The symbol of the ticker of your choice. For example: symbol=IBM.
    """

    return _alpha_vantage_request("OVERVIEW", symbol=symbol)


@mcp.tool()
def symbol_search(keywords: str):
    """Returns the best-matching symbols and market information based on keywords. Use this tool if you are unsure what the symbol for a company

    Args:
        keywords (str): A text string of your choice. For example: 'microsoft'
    """

    return _alpha_vantage_request("SYMBOL_SEARCH", keywords=keywords)


@mcp.tool()
def curreny_exchange_rate(from_currency: str, to_currency: str):
    """Returns the realtime exchange rate for a pair of digital currency (e.g., Bitcoin) and physical currency (e.g., USD).

    Args:
        from_currency (str): The currency you would like to get the exchange rate for. It can either be a physical currency or digital/crypto currency. For example: 'USD' or 'BTC'
        to_currency (str): The destination currency for the exchange rate. It can either be a physical currency or digital/crypto currency. For example: 'USD' or 'BTC'
    """

    return _alpha_vantage_request("CURRENCY_EXCHANGE_RATE", from_currency=from_currency, to_currency=to_currency)


if __name__ == "__main__":
    mcp.run(transport="stdio")
