# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:40:57 2026

@author: shiva_xjtzfpt
"""

"""
config_loader.py
-----------------
Reads config.json and provides clean access to all settings.
This means your agent.py never hardcodes any values.
"""

import json
import os


def load_config(path: str = "config.json") -> dict:
    """Load and return the config file as a dict."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"config.json not found at '{path}'.\n"
            "Please create it using the template provided in the repo."
        )
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    _validate(config)
    return config


def _validate(config: dict):
    """Check required fields exist so errors are caught early."""
    required = {
        "profile": ["role", "skills", "experience", "location", "job_type"],
        "search":  ["job_boards", "max_results_per_search", "num_searches"],
        "output":  ["formats", "folder"],
    }
    for section, fields in required.items():
        if section not in config:
            raise KeyError(f"Missing section '{section}' in config.json")
        for field in fields:
            if field not in config[section]:
                raise KeyError(f"Missing field '{field}' under '{section}' in config.json")


def get_profile(config: dict) -> dict:
    return config["profile"]


def get_search_settings(config: dict) -> dict:
    return config["search"]


def get_output_settings(config: dict) -> dict:
    return config["output"]


def get_email_settings(config: dict) -> dict:
    return config.get("email", {"enabled": False})