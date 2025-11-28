"""US stock data provider using yfinance."""

import logging
import os
import sys
from contextlib import contextmanager
from typing import List, Optional

import pandas as pd
import yfinance as yf

# Suppress yfinance error messages
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


@contextmanager
def suppress_stderr():
    """Temporarily suppress stderr output."""
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


class USStockProvider:
    """Provider for US stock market data."""

    # S&P 500 major tickers (hardcoded due to Wikipedia access issues)
    SP500_TICKERS = [
        # Tech
        "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "AVGO", "ORCL",
        "CRM", "AMD", "ADBE", "CSCO", "ACN", "IBM", "INTC", "TXN", "QCOM", "AMAT",
        "INTU", "MU", "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "FTNT", "PANW",
        # Finance
        "JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "SCHW", "AXP", "SPGI",
        "BX", "CB", "PGR", "MMC", "ICE", "CME", "AON", "MCO", "TFC", "USB",
        # Healthcare
        "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "BMY",
        "AMGN", "CVS", "ELV", "MDT", "GILD", "CI", "REGN", "ISRG", "VRTX", "ZTS",
        # Consumer
        "WMT", "HD", "MCD", "COST", "NKE", "SBUX", "TJX", "LOW", "TGT", "DG",
        "BKNG", "ABNB", "MAR", "CMG", "YUM", "ORLY", "AZO", "ROST", "EBAY", "ETSY",
        # Industrial
        "GE", "CAT", "HON", "UNP", "RTX", "BA", "LMT", "DE", "UPS", "MMM",
        "GD", "NOC", "FDX", "NSC", "CSX", "EMR", "ETN", "PH", "ITW", "CARR",
        # Energy
        "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
        # Communication/Media
        "TMUS", "T", "VZ", "NFLX", "DIS", "CMCSA", "CHTR", "PARA", "WBD", "FOXA",
        # Other
        "BRK-B", "V", "MA", "PM", "PG", "KO", "PEP", "MO", "CL", "MDLZ"
    ]

    # NASDAQ 100 major tickers
    NASDAQ100_TICKERS = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "AVGO", "COST",
        "NFLX", "AMD", "PEP", "ADBE", "CSCO", "TMUS", "CMCSA", "INTC", "INTU", "TXN",
        "QCOM", "AMGN", "HON", "SBUX", "AMAT", "BKNG", "ISRG", "GILD", "ADI", "VRTX",
        "ADP", "REGN", "MDLZ", "PANW", "MU", "LRCX", "PYPL", "SNPS", "KLAC", "CDNS",
        "MELI", "CRWD", "ABNB", "MAR", "FTNT", "ORLY", "CSX", "MRVL", "DASH", "ADSK",
        "NXPI", "WDAY", "AZN", "CPRT", "MNST", "PCAR", "ROP", "PAYX", "ROST", "FAST",
        "ODFL", "AEP", "BKR", "EA", "CTSH", "XEL", "DXCM", "VRSK", "GEHC", "EXC",
        "CTAS", "CHTR", "IDXX", "KDP", "MCHP", "KHC", "CCEP", "TTWO", "FANG", "ZS",
        "DDOG", "ANSS", "TTD", "ON", "CDW", "BIIB", "GFS", "ILMN", "WBD", "MDB",
        "MRNA", "WBA", "TEAM", "ALGN", "CRWD", "ZM", "LCID", "RIVN"
    ]

    @classmethod
    def get_universe(cls) -> List[str]:
        """Get combined US stock universe (S&P 500 + NASDAQ 100)."""
        return list(set(cls.SP500_TICKERS + cls.NASDAQ100_TICKERS))

    @staticmethod
    def get_stock_data(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
        """
        Fetch stock data from yfinance.

        Args:
            ticker: Stock ticker symbol
            period: Data period (e.g., "6mo", "1y")

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            with suppress_stderr():
                stock = yf.Ticker(ticker)
                df = stock.history(period=period)
            if df.empty:
                return None
            return df
        except Exception:
            return None

    @staticmethod
    def get_stock_info(ticker: str) -> Optional[dict]:
        """
        Get stock info including market cap.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with stock info or None if failed
        """
        try:
            with suppress_stderr():
                stock = yf.Ticker(ticker)
                return stock.info
        except Exception:
            return None
