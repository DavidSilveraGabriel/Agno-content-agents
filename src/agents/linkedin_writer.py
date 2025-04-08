# agents/linkedin_writer.py
from agno.agent import Agent
from agno.models.google import Gemini
import os
from src.config.settings import settings # Import settings object

linkedin_writer_agent = Agent(
    name="LinkedInWriterAgent",
    model=Gemini(id="gemini-2.0-flash", api_key=settings.GOOGLE_API_KEY), # Use settings.GOOGLE_API_KEY
    description="You are an expert in content marketing for LinkedIn.",
    instructions=[
        "You will receive research context about a topic.",
        "Write a concise and professional post for LinkedIn (maximum 2-3 paragraphs).",
        "Focus on the impact or relevance for professionals and businesses.",
        "Include 3-5 relevant hashtags.",
        "Use a professional yet accessible tone.",
        "End with a question or call to action to encourage interaction.",
    ],
    markdown=False, # LinkedIn no usa Markdown complejo
    show_tool_calls=False,
    debug_mode=False
)
