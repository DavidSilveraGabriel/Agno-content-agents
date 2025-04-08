# agents/instagram_writer.py
from agno.agent import Agent
from agno.models.google import Gemini
import os
from src.config.settings import settings # Import settings object

instagram_writer_agent = Agent(
    name="InstagramWriterAgent",
    model=Gemini(id="gemini-2.0-flash", api_key=settings.GOOGLE_API_KEY), # Use settings.GOOGLE_API_KEY
    description="You are a visual content creator and Instagram expert.",
    instructions=[
        "You will receive research context about a topic.",
        "Write an engaging caption for an Instagram post.",
        "The caption should be visually descriptive and emotionally resonant.",
        "Include 3-5 relevant and popular hashtags, including some more niche ones.",
        "Use emojis to add visual appeal.",
        "End with a question or call to action for the community.",
        "IMPORTANT: Also suggest 2-3 concrete ideas for the image or video that would accompany this caption.",
    ],
    markdown=False, # Instagram no usa Markdown
    show_tool_calls=False,
    debug_mode=False
    # Podríamos añadir un response_model si quisiéramos separar caption e ideas de imagen
)
