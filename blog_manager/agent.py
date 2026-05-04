import os
from dotenv import load_dotenv
from google.adk import Agent
from notion_to_jekyll_tool import convert_notion_to_jekyll

# Load environment variables (.env)
load_dotenv()

system_instructions = """You are an expert Blog Management Agent for a Jekyll blog.
Your primary task is to help the user manage their blog by converting Notion pages into Jekyll markdown posts.
When a user provides a Notion Page ID or URL, you MUST use the `convert_notion_to_jekyll` tool to process it.
Do not attempt to parse or write the markdown yourself; rely entirely on the tool.
Once the tool finishes, inform the user about the result (success or error) based on the tool's output.
"""

# Define the Google ADK Agent
root_agent = Agent(
    name="blog_manager",
    instruction=system_instructions,
    tools=[convert_notion_to_jekyll],
    model="gemini-2.5-flash", # You can adjust the model if needed
)

if __name__ == "__main__":
    print("🤖 Blog Management Agent Orchestrator Loaded.")
    print("Run this agent using the ADK CLI, for example:")
    print("  adk run orchestrator.py")
