# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:40:25 2026

@author: shiva_xjtzfpt
"""

"""
A safe wrapper that retries any function on failure.
Handles rate limits (429), network errors, and timeouts
so the agent doesn't crash on temporary failures.

Usage:
    result = safe_call(my_function, arg1, arg2, retries=3, delay=5)
"""

import time
from logger import logger


def safe_call(func, *args, retries: int = 3, delay: int = 5, **kwargs):
    """
    Call func(*args, **kwargs) with automatic retry on failure.

    Args:
        func:    The function to call
        *args:   Arguments to pass to the function
        retries: How many times to retry before giving up
        delay:   Seconds to wait between retries (doubles each attempt)
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of func(), or raises the last exception if all retries fail.
    """
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_error = e
            error_str = str(e)

            # Rate limit — wait longer
            if "429" in error_str or "ResourceExhausted" in error_str or "quota" in error_str.lower():
                wait = 60 * attempt   # 60s, 120s, 180s
                logger.warning(f"Rate limit hit (attempt {attempt}/{retries}). Waiting {wait}s...")
                time.sleep(wait)

            # Network or timeout error — short wait
            elif "timeout" in error_str.lower() or "connection" in error_str.lower():
                wait = delay * attempt
                logger.warning(f"Network error (attempt {attempt}/{retries}). Retrying in {wait}s... [{e}]")
                time.sleep(wait)

            # Unknown error — short wait, then retry
            else:
                wait = delay * attempt
                logger.error(f"Unexpected error (attempt {attempt}/{retries}): {e}. Retrying in {wait}s...")
                time.sleep(wait)

    logger.error(f"All {retries} attempts failed. Last error: {last_error}")
    raise last_error