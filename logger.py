# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:40:41 2026

@author: shiva_xjtzfpt
"""

"""
logger.py
----------
Centralised logging for the job search agent.
Every run is recorded in agent.log with timestamps.
Replaces all print() calls with proper log levels:
  logger.info()    — normal progress
  logger.warning() — something unexpected but not fatal
  logger.error()   — something failed
"""

import logging
import os


def setup_logger(log_file: str = "agent.log") -> logging.Logger:
    """
    Set up and return the logger.
    Logs go to both the terminal (so you see progress)
    and to agent.log (so you have a permanent record).
    """
    logger = logging.getLogger("job_agent")
    logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler 1: write to agent.log
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler 2: print to terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Single shared logger instance — import this everywhere
logger = setup_logger()