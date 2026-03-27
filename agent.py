# -*- coding: utf-8 -*-



"""
agent.py
---------
Main entry point for the Job Search Agent.

Modular structure:
  config.json       — all settings (profile, boards, output, email)
  config_loader.py  — reads config.json
  logger.py         — centralised logging to terminal + agent.log
  memory.py         — tracks seen jobs across runs (jobs_seen.json)
  retry.py          — safe wrapper with automatic retry on failure
  tools.py          — tool definitions + execute_tool() dispatcher
  system_prompt.py  — identity and rules for agents
  output.py         — saves results as .txt, .csv, .json + email

Run:
  python agent.py
"""
#%%
import os
import google.generativeai as genai
import google.ai.generativelanguage as glm

from config_loader import load_config, get_profile, get_search_settings, get_output_settings, get_email_settings
from logger        import logger
from memory        import load_seen_jobs, save_seen_jobs, mark_as_seen
from output        import save_all, send_email
from retry         import safe_call
from tools         import TOOL_DEFINITIONS, execute_tool, set_seen_urls, set_delay, set_profile, get_collected_jobs
from system_prompt import build_system_prompt, build_user_message
#%%
os.environ["GEMINI_API_KEY"] = "Your Key Here"

#%%
def run_agent(system_prompt: str, user_message: str) -> str:
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
 
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=system_prompt,
        tools=TOOL_DEFINITIONS,
    )
 
    chat = model.start_chat(enable_automatic_function_calling=False)
 
    step            = 0
    message_to_send = user_message
 
    while True:
        step += 1
        logger.info(f"[Step {step}] Calling Gemini...")
 
        def _call():
            return chat.send_message(message_to_send)
 
        response = safe_call(_call, retries=3, delay=10)
 
        function_calls_found = []
 
        for part in response.parts:
            if part.text:
                logger.info(f"Gemini: {part.text[:200]}")
            if part.function_call:
                function_calls_found.append(part.function_call)
                logger.info(f"Tool: {part.function_call.name}({dict(part.function_call.args)})")
 
        # No tool calls → agent is done
        if not function_calls_found:
            logger.info("[Done] Agent finished.")
            return "".join(p.text for p in response.parts if p.text)
 
        # Execute tools and collect results
        response_parts = []
 
        for fc in function_calls_found:
            result = execute_tool(fc.name, dict(fc.args))
            logger.info(f"Result: {result[:150]}")
 
            response_parts.append(
                glm.Part(
                    function_response=glm.FunctionResponse(
                        name=fc.name,
                        response={"result": result}
                    )
                )
            )
 
        message_to_send = glm.Content(parts=response_parts)
 
        if step > 25:
            logger.warning("Step limit reached.")
            break
 
    return "Agent stopped."
 
 
# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
 
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Job Search Agent  [Gemini 2.5 Flash Lite + DuckDuckGo]")
    logger.info("=" * 60)
 
    if not os.environ.get("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not set.")
        exit(1)
 
    # Load config
    config  = load_config("config.json")
    profile = get_profile(config)
    search  = get_search_settings(config)
    output  = get_output_settings(config)
    email   = get_email_settings(config)
 
    logger.info(f"Role: {profile['role']} | Location: {profile['location']}")
    logger.info(f"Boards: {search['job_boards']}")
 
    # Load memory and inject into tools
    seen_urls = load_seen_jobs()
    set_seen_urls(seen_urls)
    set_delay(search.get("delay_between_searches", 4))
    set_profile(profile)   # ← injected so tools.py can score jobs
 
    # Run agent
    final_answer = run_agent(
        build_system_prompt(profile, search),
        build_user_message(profile)
    )
 
    # Retrieve what was collected
    jobs = get_collected_jobs()
    logger.info(f"Jobs collected: {len(jobs)}")
 
    if jobs:
        # Save in all configured formats
        saved_files = save_all(jobs, profile, output["formats"], output["folder"])
 
        # Print where files landed
        for fmt, path in saved_files.items():
            print(f"  Saved {fmt.upper()}: {path}")
 
        # Update memory
        for job in jobs:
            seen_urls.add(job.get("url", ""))
        save_seen_jobs(seen_urls)
 
        # Email if enabled
        send_email(jobs, profile, email, saved_files)
 
    else:
        logger.warning("No jobs collected. Check agent.log for details.")
 
    print(f"\n{final_answer}")
    logger.info("Done.")