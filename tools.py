# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 15:05:35 2026

@author: shiva_xjtzfpt
"""

#%%
"""
All tool definitions and the execute_tool() dispatcher.

Two kinds of things live here:
1. Tool STUBS — empty Python functions that Gemini reads to understand
   what tools exist and what arguments they take. The docstrings and
   type hints are what Gemini uses to build the schema automatically.

2. execute_tool() — the real logic dispatcher. When Gemini calls a tool,
   this function runs the actual code and returns the result.
"""
#%%
import json
import time

from ddgs import DDGS

from logger import logger
from memory import is_new_job
from retry import safe_call


# ─────────────────────────────────────────────
# TOOL STUBS (Gemini reads these)
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


def score_and_rank_jobs(jobs_json: str) -> str:
    """Score each job listing 1-10 based on how well it matches the candidate profile.
    Sort results highest score first. Call this once after all searches are done.

    Args:
        jobs_json: A JSON string containing a list of job dicts with keys:
                   title, company, location, type, description, url
    """
    pass


def save_jobs_to_file(jobs_json: str, filename: str) -> str:
    """Save the final scored and ranked list of jobs. Call this ONCE at the end.

    Args:
        jobs_json: JSON string of the final ranked job list.
        filename: Base filename e.g. react_jobs_bengaluru
    """
    pass


# Export stubs for Gemini
TOOL_DEFINITIONS = [web_search, score_and_rank_jobs, save_jobs_to_file]


# ─────────────────────────────────────────────
# TOOL EXECUTOR
# Real logic runs here. Returns a string result
# which Gemini reads to decide what to do next.
# ─────────────────────────────────────────────

# Shared state for this run — populated by execute_tool calls
_collected_jobs = []
_seen_urls      = set()
_delay          = 4     # seconds between searches, set by agent.py


def set_seen_urls(seen: set):
    """Called by agent.py to inject memory before the run starts."""
    global _seen_urls
    _seen_urls = seen


def set_delay(delay: int):
    """Called by agent.py to inject search delay from config."""
    global _delay
    _delay = delay


def get_collected_jobs() -> list:
    """Called by agent.py to retrieve results after the run."""
    return _collected_jobs


def execute_tool(tool_name: str, tool_input: dict) -> str:
    global _collected_jobs

    # ── web_search ──────────────────────────────
    if tool_name == "web_search":
        query       = tool_input.get("query", "")
        max_results = int(tool_input.get("max_results", 8))

        logger.info(f"web_search: {query}")

        def _search():
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)
            return results

        try:
            raw = safe_call(_search, retries=3, delay=5)
        except Exception as e:
            return f"Search failed after retries: {e}"

        if not raw:
            return "No results found. Try a different query."

        formatted = f"Results for '{query}':\n\n"
        for i, r in enumerate(raw, 1):
            url = r.get("href", "")
            # Skip if already seen
            if not is_new_job(url, _seen_urls):
                continue
            formatted += f"{i}. {r.get('title', '')}\n"
            formatted += f"   URL : {url}\n"
            formatted += f"   Info: {r.get('body', '')[:300]}\n\n"

        # Delay to respect free tier rate limits
        time.sleep(_delay)
        return formatted if formatted.strip() else "All results already seen. Try a different query."

    # ── score_and_rank_jobs ─────────────────────
    if tool_name == "score_and_rank_jobs":
        try:
            jobs = json.loads(tool_input.get("jobs_json", "[]"))
        except json.JSONDecodeError:
            return "Error: jobs_json was not valid JSON."

        if not jobs:
            return "No jobs to score."

        # Store scored jobs for later retrieval
        _collected_jobs = sorted(jobs, key=lambda j: j.get("score", 0), reverse=True)

        summary = f"Scored and ranked {len(_collected_jobs)} jobs.\n"
        for j in _collected_jobs[:3]:
            summary += f"  [{j.get('score','?')}/10] {j.get('title','?')} at {j.get('company','?')}\n"

        return summary

    # ── save_jobs_to_file ───────────────────────
    if tool_name == "save_jobs_to_file":
        # Signal to agent.py that saving should happen
        # Actual file writing is done by output.py after the loop
        # This tool just confirms to Gemini that the task is done
        jobs_json = tool_input.get("jobs_json", "[]")
        try:
            jobs = json.loads(jobs_json)
            if jobs:
                _collected_jobs = jobs
        except json.JSONDecodeError:
            pass

        return f"Ready to save {len(_collected_jobs)} jobs. Files will be written now."

    return f"Unknown tool: {tool_name}"