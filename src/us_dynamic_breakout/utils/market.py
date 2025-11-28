"""Market hours and status utilities for US market."""

from datetime import datetime, time as dt_time
from typing import Dict


def get_market_status() -> Dict:
    """
    Check current US market status (based on Korean time).

    US market hours in KST:
    - Regular: 23:30 - 06:00 next day
    - Extended: 22:00 - 07:00

    Weekend handling (KST):
    - Sat 00:00-07:00: Open (US Friday session)
    - Sat 22:00-Sun 07:00: Closed (US Saturday)
    - Sun 22:00-Mon 07:00: Closed (US Sunday)

    Returns:
        Dict with 'is_open', 'time', 'weekday' keys
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    # US market in KST: 22:00 - 07:00 next day (extended hours)
    us_open_night = dt_time(22, 0)
    us_close_morning = dt_time(7, 0)

    is_open = False

    # Check if we're in a trading time window
    is_night_session = current_time >= us_open_night  # 22:00~23:59
    is_morning_session = current_time <= us_close_morning  # 00:00~07:00

    if is_night_session:
        # Night session (22:00-23:59 KST) = US same day morning
        # Closed on: Saturday night (US Sat), Sunday night (US Sun)
        if weekday not in [5, 6]:  # Not Sat/Sun night
            is_open = True
    elif is_morning_session:
        # Morning session (00:00-07:00 KST) = US previous day afternoon
        # Closed on: Saturday morning (US Fri->Sat), Sunday morning (US Sat)
        # Actually: Sat morning = US Friday session (open)
        #          Sun morning = US Saturday (closed)
        #          Mon morning = US Sunday (closed)
        if weekday not in [0, 6]:  # Not Mon/Sun morning
            is_open = True

    return {
        'is_open': is_open,
        'time': now.strftime('%H:%M:%S'),
        'weekday': weekday
    }


def is_market_open() -> bool:
    """Check if US market is currently open."""
    return get_market_status()['is_open']
