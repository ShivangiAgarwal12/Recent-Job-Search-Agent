# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:40:11 2026

@author: shiva_xjtzfpt
"""

"""
output.py
----------
Handles all output formats for the job search agent:
  - .txt  (human readable)
  - .csv  (open in Excel)
  - .json (use in other programs)
  - email (send results to yourself)

All files land in the output/ folder (configurable in config.json).
"""

import csv
import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from logger import logger


def _ensure_folder(folder: str):
    """Create output folder if it doesn't exist."""
    os.makedirs(folder, exist_ok=True)


def _base_filename(profile: dict) -> str:
    """Generate a timestamped filename base from the profile."""
    role     = profile["role"].lower().replace(" ", "_")
    location = profile["location"].lower().replace(" ", "_")
    date     = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{role}_jobs_{location}_{date}"


def save_txt(jobs: list, profile: dict, folder: str) -> str:
    """Save jobs as a human-readable .txt file."""
    _ensure_folder(folder)
    filename = os.path.join(folder, _base_filename(profile) + ".txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("Job Search Results\n")
        f.write(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Role      : {profile['role']}\n")
        f.write(f"Location  : {profile['location']}, India\n")
        f.write(f"Job Type  : {profile['job_type']}\n")
        f.write("=" * 60 + "\n\n")

        for i, job in enumerate(jobs, 1):
            score = job.get("score", "N/A")
            f.write(f"[Score: {score}/10] {job.get('title', 'Unknown')}\n")
            f.write(f"   Company    : {job.get('company', '—')}\n")
            f.write(f"   Location   : {job.get('location', '—')}\n")
            f.write(f"   Type       : {job.get('type', '—')}\n")
            f.write(f"   Description: {job.get('description', '—')}\n")
            f.write(f"   Apply at   : {job.get('url', '—')}\n")
            f.write("\n")

    logger.info(f"Saved TXT  → {os.path.abspath(filename)}")
    return filename


def save_csv(jobs: list, profile: dict, folder: str) -> str:
    """Save jobs as a .csv file (opens in Excel)."""
    _ensure_folder(folder)
    filename = os.path.join(folder, _base_filename(profile) + ".csv")

    fields = ["score", "title", "company", "location", "type", "description", "url"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)

    logger.info(f"Saved CSV  → {os.path.abspath(filename)}")
    return filename


def save_json(jobs: list, profile: dict, folder: str) -> str:
    """Save jobs as a .json file (use in other programs or RAG pipeline)."""
    _ensure_folder(folder)
    filename = os.path.join(folder, _base_filename(profile) + ".json")

    payload = {
        "generated": datetime.now().isoformat(),
        "profile":   profile,
        "total":     len(jobs),
        "jobs":      jobs
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved JSON → {os.path.abspath(filename)}")
    return filename


def save_all(jobs: list, profile: dict, formats: list, folder: str) -> dict:
    """
    Save jobs in all configured formats.
    Returns a dict of format -> filepath.
    """
    saved = {}
    for fmt in formats:
        if fmt == "txt":
            saved["txt"] = save_txt(jobs, profile, folder)
        elif fmt == "csv":
            saved["csv"] = save_csv(jobs, profile, folder)
        elif fmt == "json":
            saved["json"] = save_json(jobs, profile, folder)
        else:
            logger.warning(f"Unknown format '{fmt}' in config — skipping.")
    return saved


def send_email(jobs: list, profile: dict, email_config: dict, saved_files: dict):
    """
    Email the results to yourself.
    Requires a Gmail App Password (not your normal Gmail password).
    How to get one: Google Account → Security → 2-Step Verification → App Passwords
    """
    if not email_config.get("enabled", False):
        logger.info("Email disabled in config — skipping.")
        return

    sender      = email_config["sender"]
    receiver    = email_config["receiver"]
    password    = email_config["app_password"]
    smtp_server = email_config.get("smtp_server", "smtp.gmail.com")
    smtp_port   = email_config.get("smtp_port", 587)

    # Build email body
    body = f"Job Search Results — {profile['role']} in {profile['location']}\n"
    body += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    body += "=" * 50 + "\n\n"

    for job in jobs:
        body += f"[{job.get('score','?')}/10] {job.get('title','')}\n"
        body += f"  {job.get('company','')} — {job.get('location','')}\n"
        body += f"  {job.get('url','')}\n\n"

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = receiver
    msg["Subject"] = f"Job Results: {profile['role']} in {profile['location']}"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        logger.info(f"Email sent to {receiver}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")