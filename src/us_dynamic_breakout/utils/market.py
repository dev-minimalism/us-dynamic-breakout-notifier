"""Market hours and status utilities for US market."""

from datetime import datetime, time as dt_time
from typing import Dict, Optional


def get_market_session(current_time: dt_time) -> Optional[str]:
    """
    Get current market session name based on Korean time.

    Market sessions in KST:
    - Day Market: 10:00~17:50
    - Pre-Market: 18:00~23:29
    - Regular: 23:30~05:59
    - After-Market: 06:00~09:50
    - Closed: 09:51~09:59

    Returns:
        Session name or None if market is closed
    """
    # Define session boundaries
    day_start = dt_time(10, 0)
    day_end = dt_time(17, 50)
    pre_start = dt_time(18, 0)
    pre_end = dt_time(23, 29)
    regular_night_start = dt_time(23, 30)
    regular_morning_end = dt_time(5, 59)
    after_start = dt_time(6, 0)
    after_end = dt_time(9, 50)

    if day_start <= current_time <= day_end:
        return "day"
    elif pre_start <= current_time <= pre_end:
        return "pre"
    elif current_time >= regular_night_start or current_time <= regular_morning_end:
        return "regular"
    elif after_start <= current_time <= after_end:
        return "after"
    else:
        return None


def get_market_status() -> Dict:
    """
    Check current US market status (based on Korean time).

    Market sessions in KST:
    - Day Market: 10:00~17:50
    - Pre-Market: 18:00~23:29
    - Regular: 23:30~05:59
    - After-Market: 06:00~09:50
    - Closed: 09:51~09:59

    Weekend handling (KST):
    - Sat 00:00-09:50: Open (US Friday session)
    - Sat 10:00-Sun 09:50: Closed (US weekend)
    - Sun 10:00-Mon 09:50: Closed (US weekend)

    Returns:
        Dict with 'is_open', 'session', 'time', 'weekday' keys
    """
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    session = get_market_session(current_time)
    is_open = False

    if session is None:
        # Closed time (09:51~09:59)
        is_open = False
    elif session == "regular":
        # Regular session spans midnight (23:30~05:59)
        if current_time >= dt_time(23, 30):
            # Night portion (23:30~23:59): Check current day
            # Closed on: Sat night (US Sat), Sun night (US Sun)
            if weekday not in [5, 6]:
                is_open = True
        else:
            # Morning portion (00:00~05:59): Check previous day
            # Closed on: Sun morning (US Sat), Mon morning (US Sun)
            if weekday not in [0, 6]:
                is_open = True
    elif session == "after":
        # After-market (06:00~09:50): Same as morning regular
        # Closed on: Sun morning (US Sat), Mon morning (US Sun)
        if weekday not in [0, 6]:
            is_open = True
    elif session == "day":
        # Day market (10:00~17:50): KST daytime = US previous day
        # Closed on: Sat (US Fri night->Sat), Sun (US Sat)
        if weekday not in [5, 6]:
            is_open = True
    elif session == "pre":
        # Pre-market (18:00~23:29): KST evening = US same day morning
        # Closed on: Sat (US Sat), Sun (US Sun)
        if weekday not in [5, 6]:
            is_open = True

    session_names = {
        "day": "Day Market",
        "pre": "Pre-Market",
        "regular": "Regular",
        "after": "After-Market",
        None: "Closed"
    }

    return {
        'is_open': is_open,
        'session': session_names.get(session, "Closed"),
        'time': now.strftime('%H:%M:%S'),
        'weekday': weekday
    }


def is_market_open() -> bool:
    """Check if US market is currently open."""
    return get_market_status()['is_open']
