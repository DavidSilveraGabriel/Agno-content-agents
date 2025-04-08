# agents/twitter_writer.py
from agno.agent import Agent
from agno.models.google import Gemini
import os
from src.config.settings import settings # Import settings object

x_writer_agent = Agent(
    name="XWriterAgent", # Renamed for consistency
    model=Gemini(id="gemini-2.0-flash", api_key=settings.GOOGLE_API_KEY), # Use settings.GOOGLE_API_KEY
    description="You are a social media specialist, expert in creating content for X (formerly Twitter).",
    instructions=[
        "You will receive research context about a topic.",
        "Write a concise and catchy tweet (maximum 280 characters).",
        "Highlight the most interesting or surprising point of the topic.",
        "Include 2-3 relevant and popular hashtags.",
        "Use a conversational and direct tone.",
        "Consider adding a relevant emoji.",
        # Note: For an MVP, we won't implement complex threads.
    ],
    markdown=False,
    show_tool_calls=False,
    debug_mode=False
)
