# agents/blog_writer.py
from agno.agent import Agent
from agno.models.google import Gemini
from textwrap import dedent
import os
from src.config.settings import settings # Import settings object

blog_writer_agent = Agent(
    name="BlogWriterAgent",
    model=Gemini(id="gemini-2.0-flash", api_key=settings.GOOGLE_API_KEY), # Use settings.GOOGLE_API_KEY
    description="You are an expert blog writer, capable of transforming researched information into engaging and well-structured articles.",
    instructions=[
        "You will receive context based on web research.",
        "Your task is to write a detailed and well-researched blog post about the main topic.",
        "The post must have an engaging introduction, several development paragraphs with clear subheadings, and a strong conclusion.",
        "Use Markdown format for titles, subtitles, lists, and bold text.",
        "Ensure the content is informative, accurate, and easy to read.",
        "The length should be appropriate for a blog post (at least 500 words).",
        "Cite sources implicitly based on the provided context; do not invent information.",
    ],
    expected_output=dedent("""\
        A well-structured blog post in Markdown format. Example:
        # Engaging Blog Title

        Brief and catchy introduction...

        ## Subheading 1: Exploring the Concept

        Development of the first key point...

        ## Subheading 2: Implications and Examples

        More details, examples, or analysis...

        ## Conclusion

        Final summary and closing thoughts...
        """),
    markdown=True, # Importante para que la salida sea Markdown
    show_tool_calls=False, # Este agente no necesita herramientas
    debug_mode=False
)
