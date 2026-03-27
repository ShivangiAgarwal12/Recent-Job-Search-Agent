# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:39:19 2026

@author: shiva_xjtzfpt
"""

"""
memory.py
----------
Persistent memory for the agent across runs.
Stores URLs of jobs already seen so the agent
never shows you the same listing twice.

How it works:
- On startup: load jobs_seen.json into a set of URLs
- After each run: add new URLs to the set and save
- Agent checks this before adding a job to results
"""

import json
import os
from logger import logger

MEMORY_FILE = "jobs_seen.json"


def load_seen_jobs() -> set:
    """Load previously seen job URLs from disk."""
    if not os.path.exists(MEMORY_FILE):
        logger.info("No memory file found — starting fresh.")
        return set()

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    seen = set(data)
    logger.info(f"Loaded {len(seen)} previously seen jobs from memory.")
    return seen


def save_seen_jobs(urls: set):
    """Save the updated set of seen job URLs to disk."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(urls), f, indent=2)
    logger.info(f"Saved {len(urls)} job URLs to memory.")


def is_new_job(url: str, seen: set) -> bool:
    """Return True if this job URL has not been seen before."""
    return url not in seen


def mark_as_seen(url: str, seen: set) -> set:
    """Add a URL to the seen set and return the updated set."""
    seen.add(url)
    return seen


def clear_memory():
    """Wipe the memory file — use if you want a completely fresh start."""
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
        logger.warning("Memory cleared — all job history deleted.")
    else:
        logger.info("No memory file to clear.")