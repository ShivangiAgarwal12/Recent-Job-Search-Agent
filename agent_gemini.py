# -*- coding: utf-8 -*-
"""
Created on Mon Mar 23 15:01:41 2026

@author: shiva_xjtzfpt
AIzaSyBOjuGj97XUUJh3uKvQA3RIGZ6FCjZsMtk
"""

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime
from google import genai
from google.genai import types

# 1. YOUR CUSTOM TOOL (The "Save" function)
def save_jobs_to_file(filename: str, content: str) -> str:
    """Saves the final list of job postings to a .txt file on disk."""
    try:
        # Clean filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ','.','_')).rstrip()
        if not filename.endswith(".txt"): filename += ".txt"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"JOB SEARCH RESULTS\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 30 + "\n\n")
            f.write(content)
        return f"SUCCESS: Saved to {filename}"
    except Exception as e:
        return f"ERROR saving file: {str(e)}"

# 2. THE AGENT EXECUTION
def run_agent(role, location):
    client = genai.Client(api_key=os.environ.get("AIzaSyBOjuGj97XUUJh3uKvQA3RIGZ6FCjZsMtk"))
    
    # We use the 'GoogleSearch' tool from your specific SDK version
    tools_list = [
        save_jobs_to_file, 
        types.Tool(google_search=types.GoogleSearch()) 
    ]

    print(f"\n[Agent] Searching for {role} jobs in {location}...")
    
    # Give the API a 2-second breather to avoid the 429 Quota error
    time.sleep(2)

    # Using the exact model name from your list
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=f"Find 5 active {role} jobs in {location}. Save them to a file and summarize.",
        config=types.GenerateContentConfig(
            system_instruction="You are a helpful job assistant. Use Google Search to find real data and save_jobs_to_file to store it.",
            tools=tools_list,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,
                maximum_remote_calls=5
            ),
        )
    )
    return response.text

# 3. RUN IT
if __name__ == "__main__":
    # Ensure you've run: set GOOGLE_API_KEY=your_key
    try:
        job = input("Enter Role (e.g. Data Scientist): ") or "Data Scientist"
        loc = input("Enter City (e.g. Mumbai): ") or "Mumbai"
        
        print("\n--- Starting Agent ---")
        result = run_agent(job, loc)
        print("\n--- Agent Summary ---")
        print(result)
        print("\nCheck your folder for the .txt file!")
    except Exception as e:
        print(f"\n[Final Error] {e}")