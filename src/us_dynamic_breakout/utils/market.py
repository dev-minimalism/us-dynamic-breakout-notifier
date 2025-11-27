"""Market hours and status utilities for US market."""

from datetime import datetime, time as dt_time
from typing import Dict


def get_market_status() -> Dict:
    """
    Check current US market status (based on Korean time).

    Returns:
        Dict with 'is_open', 'time', 'weekday' keys
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    is_weekend = weekday >= 5

    # US market in KST: 23:30 - 06:00 next day (regular hours)
    # Extended: 22:00 - 07:00
    us_open_night = dt_time(22, 0)
    us_close_morning = dt_time(7, 0)

    is_open = False
    if not is_weekend:
        if current_time >= us_open_night:
            is_open = True
        elif current_time <= us_close_morning:
            is_open = True

    return {
        'is_open': is_open,
        'time': now.strftime('%H:%M:%S'),
        'weekday': weekday
    }


def is_market_open() -> bool:
    """Check if US market is currently open."""
    return get_market_status()['is_open']
