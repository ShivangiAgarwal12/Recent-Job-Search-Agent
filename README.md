# Recent-Job-Search-Agent
Scraps internet to find most recent jobs posted
# Job Search Agent 🔍

An AI-powered job search agent that searches the web for job postings matching your profile and saves results to a file — **completely free to run**.

## Stack

| Component | Tool | Cost |
|---|---|---|
| LLM | Google Gemini 2.5 Flash Lite | Free (1000 req/day) |
| Web Search | DDGS (DuckDuckGo) | Free, no API key |
| Output | Local `.txt` file | — |

## How It Works

This is a classic **agent loop**:
```
User profile
     ↓
 [LLM thinks]
     ↓
 Tool call? → web_search (DuckDuckGo) → result back to LLM → repeat
     ↓
 No more tools → save_jobs_to_file → done
```

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/your-username/job-search-agent
cd job-search-agent
```

**2. Install dependencies**
```bash
pip install google-generativeai ddgs
```

**3. Get a free Gemini API key**

Go to [aistudio.google.com](https://aistudio.google.com) → click **Get API key** → no credit card needed.

**4. Set your API key**
```bash
# Mac/Linux
export GEMINI_API_KEY=your_key_here

# Windows
set GEMINI_API_KEY=your_key_here
```

**5. Run**
```bash
python agent.py
```

## Usage

When you run the script it will ask for your profile:
```
Job Role       [React Developer]      : Data Scientist
Key Skills     [React, Node.js]       : Python, Machine Learning, SQL
Experience     [3-5 years]            : 2-4 years
City in India  [Bengaluru]            : Bengaluru
Job Type       [Remote/Hybrid/Any]    : Remote
```

Results are saved to a `.txt` file in the same folder:
```
data_scientist_jobs_bengaluru.txt
```

## Project Structure
```
job-search-agent/
├── agent.py          # main agent script
├── README.md         # this file
└── .gitignore        # keeps your API key off GitHub
```




## Key Concepts

- **System prompt** — defines the agent's role and rules, passed on every API call
- **User message** — the specific task, changes each run
- **Tool definitions** — Python functions the LLM can choose to call
- **Agent loop** — keeps running until the LLM stops requesting tools
- **Tool executor** — your code that actually runs each tool and returns results

Once you understand this loop, you can swap in any LLM and any set of tools to build agents for any task.

## License

MIT