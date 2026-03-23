# -*- coding: utf-8 -*-
"""
Created on Mon Mar 23 10:29:35 2026

@author: shiva_xjtzfpt
"""

"""
Job Search Agent — 100% Free Stack
====================================
LLM    : Google Gemini 1.5 Flash  (1500 free requests/day — no credit card)
Search : DuckDuckGo               (completely free — no API key needed)
Save   : Local .txt file

Install:
  pip install google-generativeai duckduckgo-search

Free Gemini key (no credit card): https://aistudio.google.com

Set your key — either paste it directly below, or set as env variable:
  Linux/Mac:  export GEMINI_API_KEY=your_key_here
  Windows:    set GEMINI_API_KEY=your_key_here

Run:
  python job_search_agent_free.py
"""

import os
from datetime import datetime

import google.generativeai as genai
import google.ai.generativelanguage as glm
# from duckduckgo_search import DDGS
from ddgs import DDGS
os.environ["GEMINI_API_KEY"] = "Update your key here"




def web_search(query: str, max_results: int = 8) -> str:
    """Search the web for job postings on LinkedIn, Naukri, Indeed, Glassdoor.
    Call this multiple times with different queries to find diverse results.

    Args:
        query: Search query e.g. 'React developer jobs Bengaluru India 2025'
        max_results: Number of results to fetch. Default is 8.
    """
    pass


def save_jobs_to_file(filename: str, content: str) -> str:
    """Save the final formatted list of job postings to a txt file on disk.
    Call this ONCE at the end after collecting all results.

    Args:
        filename: Name of the output file e.g. react_jobs_bengaluru.txt
        content: All job listings formatted as clear readable text.
    """
    pass


# Pass the function OBJECTS (not dicts) — Gemini parses them automatically
TOOLS = [web_search, save_jobs_to_file]


# ─────────────────────────────────────────────
# STEP 2: Tool executor
#
# When Gemini calls a tool, it returns the name
# + arguments. This function runs the real logic
# and returns a result string back to the LLM.
# ─────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> str:

    # ── web_search: call DuckDuckGo ────────────
    if tool_name == "web_search":
        query       = tool_input.get("query", "")
        max_results = int(tool_input.get("max_results", 8))

        print(f"    Searching: {query}")

        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url":   r.get("href", ""),
                        "body":  r.get("body", "")[:300]
                    })

            if not results:
                return "No results found. Try a different search query."

            formatted = f"Results for '{query}':\n\n"
            for i, r in enumerate(results, 1):
                formatted += f"{i}. {r['title']}\n"
                formatted += f"   URL: {r['url']}\n"
                formatted += f"   {r['body']}\n\n"

            return formatted

        except Exception as e:
            return f"Search error: {str(e)}. Try a simpler query."

    # ── save_jobs_to_file: write to disk ────────
    if tool_name == "save_jobs_to_file":
        filename = tool_input.get("filename", "jobs.txt")
        content  = tool_input.get("content", "")

        filename = filename.replace("/", "_").replace("\\", "_")
        if not filename.endswith(".txt"):
            filename += ".txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write("Job Search Results\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(content)
            print(f"\n  ✓ File saved: {os.path.abspath(filename)}")

        return f"Saved {len(content)} characters to '{filename}'"

    return f"Unknown tool: {tool_name}"


# ─────────────────────────────────────────────
# STEP 3: Agent loop
#
# Identical logic to the Claude version:
#   1. Send message to LLM
#   2. Tool call? → execute → send result back → repeat
#   3. No tool call? → LLM is done, return text
#
# Only the API syntax is different:
#   Claude → response.stop_reason == "tool_use"
#   Gemini → part.function_call in response.parts
# ─────────────────────────────────────────────

def run_agent(system_prompt: str, user_message: str, verbose: bool = True) -> str:

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=system_prompt,   # <- system prompt (agent identity)
        tools=TOOLS,
    )

    # enable_automatic_function_calling=False → WE control the loop
    chat = model.start_chat(enable_automatic_function_calling=False)

    step = 0
    message_to_send = user_message

    while True:
        step += 1
        if verbose:
            print(f"\n[Step {step}] Calling Gemini...")

        response = chat.send_message(message_to_send)

        # Each response has "parts" — text parts or function_call parts
        function_calls_found = []

        for part in response.parts:
            if part.text and verbose:
                print(f"  Gemini: {part.text[:200]}")
            if part.function_call:
                function_calls_found.append(part.function_call)
                if verbose:
                    print(f"  -> Tool: {part.function_call.name}({dict(part.function_call.args)})")

        # No tool calls → LLM is done
        if not function_calls_found:
            if verbose:
                print("\n[Done]")
            return "".join(p.text for p in response.parts if p.text)

        # Tool calls found → execute each one, collect results
        response_parts = []

        for fc in function_calls_found:
            result = execute_tool(fc.name, dict(fc.args))
            if verbose:
                print(f"  Result: {result[:120]}...")

            # Gemini's equivalent of Claude's "tool_result" block
            response_parts.append(
                glm.Part(
                    function_response=glm.FunctionResponse(
                        name=fc.name,
                        response={"result": result}   # must be a dict
                    )
                )
            )

        # Send all results back — LLM reads them and continues
        message_to_send = glm.Content(parts=response_parts)

        if step > 20:
            print("[Warning] Step limit reached.")
            break

    return "Agent stopped."


# ─────────────────────────────────────────────
# STEP 4: Prompts
# ─────────────────────────────────────────────

def build_system_prompt() -> str:
    # WHO the agent is — permanent rules, never changes during a run
    return """You are a professional job search agent for the Indian job market.

ROLE:
- Use web_search to find real, active job postings
- Search LinkedIn, Naukri, Indeed India, Glassdoor, Wellfound, Internshala
- Never fabricate listings — only report what you find

SEARCH STRATEGY:
- Run 3-5 different searches with varied queries
- Mix: role + city, role + skills, role + job board

OUTPUT:
- Collect 8-12 listings total
- For each: title, company, location, type, description, URL
- Call save_jobs_to_file once at the end with everything
- Finish with a short summary"""


def build_user_message(role, skills, experience, location, job_type) -> str:
    # WHAT to do this run — changes every time
    return f"""Find job postings for:
- Role: {role}
- Skills: {skills}
- Experience: {experience}
- Location: {location}, India
- Job Type: {job_type}

Save results to: {role.lower().replace(' ', '_')}_jobs_{location.lower().replace(' ', '_')}.txt

Then summarise what you found."""


# ─────────────────────────────────────────────
# STEP 5: Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Job Search Agent  [Gemini 1.5 Flash + DuckDuckGo — Free]")
    print("=" * 60)

    if not os.environ.get("GEMINI_API_KEY"):
        print("\n  GEMINI_API_KEY not set.")
        print("  Get free key: https://aistudio.google.com")
        print("  Then: export GEMINI_API_KEY=your_key\n")
        exit(1)

    print("\nEnter your profile (Enter = use default):\n")
    role       = input("Job Role       [React Developer]      : ").strip() or "React Developer"
    skills     = input("Key Skills     [React, Node.js]       : ").strip() or "React, Node.js, TypeScript"
    experience = input("Experience     [3-5 years]            : ").strip() or "3-5 years"
    location   = input("City in India  [Bengaluru]            : ").strip() or "Bengaluru"
    job_type   = input("Job Type       [Remote/Hybrid/Any]    : ").strip() or "Any"

    print("\n" + "-" * 60)
    print("Starting agent...\n")

    final = run_agent(
        build_system_prompt(),
        build_user_message(role, skills, experience, location, job_type),
        verbose=True
    )

    print("\n" + "=" * 60)
    print("FINAL RESPONSE:")
    print("=" * 60)
    print(final)
    print("\nCheck your folder for the .txt file!")