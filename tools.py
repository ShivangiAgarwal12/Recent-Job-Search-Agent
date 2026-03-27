# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:05:35 2026

@author: shiva_xjtzfpt
"""

"""
tools.py
---------
All tool definitions and the execute_tool() dispatcher.

FIX for 0 jobs collected:
--------------------------
The old approach relied on Gemini to pass jobs as a JSON string
to score_and_rank_jobs. This was fragile — Gemini often summarised
results in plain text instead of structured JSON, so _collected_jobs
stayed empty.

The fix: jobs are captured DIRECTLY inside the web_search executor
the moment a search runs. We don't wait for Gemini to pass them back.
Gemini still sees a clean text summary of results, but we've already
stored the raw structured data ourselves.
"""

import json
import time

from ddgs import DDGS

from logger import logger
from memory import is_new_job
from retry import safe_call


# ─────────────────────────────────────────────
# TOOL STUBS
# Gemini reads these to understand what tools
# exist and what arguments they take.
# Bodies are empty — real logic is in execute_tool()
# ─────────────────────────────────────────────

def web_search(query: str, max_results: int = 8) -> str:
    """Search the web for job postings on job boards like Indeed, Naukri, Wellfound.
    Always include site: operator to restrict to one job board.
    Call this multiple times with different queries to find diverse results.

    Args:
        query: Search query e.g. 'React developer jobs Bengaluru site:indeed.co.in'
        max_results: Number of results to fetch. Default is 8.
    """
    pass


def finish_and_save() -> str:
    """Call this tool once you have completed all searches.
    It will score, rank, and save all collected jobs automatically.
    No arguments needed.
    """
    pass


TOOL_DEFINITIONS = [web_search, finish_and_save]


# ─────────────────────────────────────────────
# SHARED STATE
# Jobs are collected here directly during
# web_search execution — not passed via Gemini.
# ─────────────────────────────────────────────

_collected_jobs = []   # raw jobs built up across all searches
_seen_urls      = set()
_delay          = 4
_profile        = {}   # injected by agent.py for scoring


def set_seen_urls(seen: set):
    global _seen_urls
    _seen_urls = seen


def set_delay(delay: int):
    global _delay
    _delay = delay


def set_profile(profile: dict):
    """Injected by agent.py so execute_tool can score against the profile."""
    global _profile
    _profile = profile


def get_collected_jobs() -> list:
    return _collected_jobs


# ─────────────────────────────────────────────
# TOOL EXECUTOR
# ─────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:
    global _collected_jobs

    # ── web_search ──────────────────────────────
    if tool_name == "web_search":
        query       = tool_input.get("query", "")
        max_results = int(tool_input.get("max_results", 8))

        logger.info(f"Searching: {query}")

        def _search():
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)
            return results

        try:
            raw = safe_call(_search, retries=3, delay=5)
        except Exception as e:
            return f"Search failed: {e}"

        if not raw:
            return "No results found. Try a different query."

        new_jobs_this_search = 0
        summary = f"Results for '{query}':\n\n"

        for r in raw:
            url   = r.get("href", "")
            title = r.get("title", "")
            body  = r.get("body", "")

            # Skip already seen jobs (memory check)
            if not is_new_job(url, _seen_urls):
                continue

            # ── KEY FIX ──────────────────────────────────
            # Capture the job directly into _collected_jobs
            # right here — don't rely on Gemini to pass it back
            # ─────────────────────────────────────────────
            job = {
                "title":       title,
                "company":     _extract_company(title, body),
                "location":    _extract_location(body, query),
                "type":        _extract_type(body),
                "description": body[:300],
                "url":         url,
                "score":       0    # scored later in finish_and_save
            }
            _collected_jobs.append(job)
            _seen_urls.add(url)
            new_jobs_this_search += 1

            # Give Gemini a readable summary (for its reasoning)
            summary += f"- {title}\n  {url}\n  {body[:150]}\n\n"

        logger.info(f"Captured {new_jobs_this_search} new jobs. Total so far: {len(_collected_jobs)}")
        time.sleep(_delay)

        return summary + f"\n[{new_jobs_this_search} new jobs captured. Total collected: {len(_collected_jobs)}]"

    # ── finish_and_save ─────────────────────────
    if tool_name == "finish_and_save":
        if not _collected_jobs:
            return "No jobs were collected during the searches."

        # Score each job against the profile
        _score_jobs(_collected_jobs, _profile)

        # Sort highest score first
        _collected_jobs.sort(key=lambda j: j.get("score", 0), reverse=True)

        top = _collected_jobs[:3]
        summary = f"Done. Scored and ranked {len(_collected_jobs)} jobs.\nTop results:\n"
        for j in top:
            summary += f"  [{j['score']}/10] {j['title']} at {j['company']}\n"

        return summary

    return f"Unknown tool: {tool_name}"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _extract_company(title: str, body: str) -> str:
    """Try to pull company name from the result text."""
    # DuckDuckGo often puts "Company Name - Job Title" in the title
    if " - " in title:
        parts = title.split(" - ")
        if len(parts) >= 2:
            return parts[-1].strip()
    if " at " in title.lower():
        return title.lower().split(" at ")[-1].strip().title()
    return "—"


def _extract_location(body: str, query: str) -> str:
    """Try to extract city from body or fall back to query location."""
    cities = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Pune",
              "Chennai", "Gurgaon", "Noida", "Kolkata", "Ahmedabad"]
    for city in cities:
        if city.lower() in body.lower():
            return f"{city}, India"
    return "India"


def _extract_type(body: str) -> str:
    """Detect job type from body text."""
    body_lower = body.lower()
    if "remote" in body_lower:
        return "Remote"
    if "hybrid" in body_lower:
        return "Hybrid"
    return "On-site"


def _score_jobs(jobs: list, profile: dict):
    """
    Simple keyword-based scoring against the profile.
    Each job gets a score 1-10 written directly into the dict.
    """
    if not profile:
        for job in jobs:
            job["score"] = 5
        return

    role   = profile.get("role", "").lower()
    skills = [s.strip().lower() for s in profile.get("skills", "").split(",")]
    jtype  = profile.get("job_type", "").lower()

    for job in jobs:
        text  = (job.get("title", "") + " " + job.get("description", "")).lower()
        score = 0

        # Role match (up to 4 points)
        role_words = role.split()
        matches    = sum(1 for w in role_words if w in text)
        score     += min(4, int((matches / max(len(role_words), 1)) * 4))

        # Skills match (up to 4 points)
        skill_hits = sum(1 for s in skills if s in text)
        score     += min(4, int((skill_hits / max(len(skills), 1)) * 4))

        # Job type match (1 point)
        if jtype and jtype != "any":
            if jtype in job.get("type", "").lower():
                score += 1

        # Clamp between 1 and 10
        job["score"] = max(1, min(10, score + 1))