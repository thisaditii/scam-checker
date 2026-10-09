from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_groq import ChatGroq

import tools as t

load_dotenv()

MODEL_NAME = "openai/gpt-oss-120b"

@tool
def extract_entities_tool(text: str) -> dict:
    """Extract emails, URLs and phone numbers from a job or internship message."""
    return t.extract_entities(text)


@tool
def domain_age_tool(domain: str) -> dict:
    """Return the age in days of a website domain, like 'example.com'.
    Domains younger than 180 days are suspicious for a company offering jobs."""
    return t.check_domain_age(domain)


@tool
def email_check_tool(email: str, company_site: str = "") -> dict:
    """Check whether the sender email uses a free provider like gmail,
    and whether it matches the company website domain."""
    return t.check_email_domain(email, company_site)


@tool
def red_flag_tool(text: str) -> dict:
    """Scan the full message for scam phrases: fees, deposits,
    WhatsApp-only contact, urgency, and 'no interview' promises."""
    return t.scan_red_flags(text)


@tool
def website_tool(url: str) -> dict:
    """Check whether a company website loads and has a careers or contact page."""
    return t.check_website(url)


TOOLS = [extract_entities_tool, domain_age_tool, email_check_tool,
         red_flag_tool, website_tool]

SYSTEM_PROMPT = """You are a job-scam investigator helping students in India.
Follow these steps:
1. Extract emails, URLs and phone numbers from the message.
2. Scan the message for red-flag phrases.
3. Check every sender email you found.
4. If a company website or a non-free email domain exists, check its domain age and website.
Base every conclusion ONLY on tool results. If a tool returns unknown or fails,
say 'unknown'. Never guess. Finish with a short summary of the evidence found."""

llm = ChatGroq(model=MODEL_NAME, temperature=0)

try:
    from langchain.agents import create_agent
    agent = create_agent(llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
except ImportError:
    # Older LangChain
    from langgraph.prebuilt import create_react_agent
    agent = create_react_agent(llm, tools=TOOLS, prompt=SYSTEM_PROMPT)


def investigate(message: str):
    """Run the agent. Returns (final_text, list_of_tool_calls)."""
    result = agent.invoke({"messages": [("user", message)]})
    msgs = result["messages"]

    tool_log = []
    for m in msgs:
        if m.type == "tool":
            tool_log.append({"tool": m.name, "output": str(m.content)[:300]})

    return msgs[-1].content, tool_log