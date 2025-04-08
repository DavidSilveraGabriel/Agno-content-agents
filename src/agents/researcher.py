# agents/researcher.py
import json
import requests # Import requests for Serper API calls
from agno.agent import Agent
from agno.models.google import Gemini
# Removed MCP import attempt
# from agno.tools.exa import ExaTools # No longer used
# from agno.tools.firecrawl import FirecrawlTools # Commented out
# from agno.tools.googlesearch import GoogleSearchTools # Commented out
from agno.tools.crawl4ai import Crawl4aiTools # Import Crawl4aiTools
# Removed RedisMemory and ChromaKnowledge imports
from agno.storage.sqlite import SqliteStorage # Added SqliteStorage import
import os
# Use the MCP client - assuming it's available globally or passed in
# For now, we'll structure the code assuming an MCP client is accessible.
# If not, we'll need to adjust how the MCP tool is called.
# from mcp_client import mcp # Placeholder for how MCP client might be accessed
from src.config.settings import settings # Import settings object
from src.utils.logging_config import logger # Corrected utils import path
from datetime import datetime

class ResearcherAgent:
    # Assuming mcp_client is passed or accessible globally
    # def __init__(self, mcp_client):
    def __init__(self):
        # self.mcp_client = mcp_client # Store MCP client if passed

        # --- Tool Configuration ---
        # Commented out previous tools
        # self.search_tool = GoogleSearchTools()
        # self.scraper_tool = FirecrawlTools(
        #     api_key=settings.FIRECRAWL_API_KEY,
        #     scrape=True,
        #     crawl=False
        # )

        # New scraper tool using Crawl4AI
        self.scraper_tool = Crawl4aiTools(max_length=None) # Use None for potentially unlimited length, or set a value like 5000

        # --- Storage Configuration ---
        # Ensure 'tmp' directory exists or adjust path as needed
        db_path = "tmp/researcher_storage.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.storage = SqliteStorage(
            table_name="researcher_sessions",
            db_file=db_path
        )

        # Configuración del agente
        # --- Agent Configuration ---
        self.agent = Agent(
            name="ResearcherAgent",
            model=Gemini(id="gemini-2.0-flash", api_key=settings.GOOGLE_API_KEY), # Use settings.GOOGLE_API_KEY
            # Note: We are calling Serper API directly, so it's not an 'agno tool' here.
            # Crawl4aiTools is used for scraping.
            tools=[self.scraper_tool],
            storage=self.storage, # Use SQLite storage
            add_history_to_messages=True, # Add history capability
            num_history_responses=3, # Number of history messages to include
            # Removed memory and knowledge parameters
            description="You are an expert researcher. You use the Serper API to find relevant URLs and Crawl4AI to scrape content from specific URLs.",
            instructions=[
                "1. Analyze the provided topic.",
                "2. If specific URLs are provided, use the Crawl4AI tool to extract and analyze their content.",
                "3. If no URLs are provided, perform a web search using the Serper API to find relevant URLs for the topic.",
                "4. Once URLs are found (either provided or via search), use Crawl4AI to extract their content.",
                # Removed instructions related to Redis memory and Chroma knowledge
                "5. Generate a structured and well-documented summary based on the found content.",
            ],
            add_datetime_to_instructions=False, # Datetime less relevant without specific memory/knowledge steps
            markdown=True,
            show_tool_calls=True,
            debug_mode=False
        )

    async def research(self, topic: str, urls: list[str] | None = None) -> dict:
        """
        Performs research on a specific topic using provided URLs or web search.

        Args:
            topic (str): The topic to research.
            urls (list[str] | None): Specific URLs to analyze. If None, performs web search.

        Returns:
            dict: Research result including topic, content (or error), timestamp, and sources.
        """
        logger.info(f"Starting research for topic: '{topic}'")

        content = None
        sources_used = [] # Initialize list for sources

        try:
            if urls:
                # If URLs are provided, use them directly
                logger.info(f"Processing {len(urls)} provided URLs...")
                content = await self._process_urls(urls)
                sources_used = urls
                if not content:
                     logger.warning(f"Processing provided URLs yielded no content for topic: {topic}")
                     content = "Failed to process provided URLs." # Provide feedback if scraping fails
            else:
                # If no URLs, perform search and then process
                logger.info("No URLs provided, performing web search and analysis...")
                search_result = await self._search_and_analyze(topic)
                if isinstance(search_result, tuple):
                    content, sources_used = search_result
                    if not content:
                         logger.warning(f"Search successful, but scraping yielded no content for topic: {topic}")
                         # Keep sources, content might be the error message from _search_and_analyze
                else: # Handle potential error string return from search
                    content = search_result # Store the error message
                    sources_used = []
                    logger.error(f"Search and analyze phase failed for topic '{topic}': {content}")

        except Exception as e:
            logger.error(f"Unexpected error during research method for topic '{topic}': {e}", exc_info=True)
            content = f"Unexpected error during research: {e}"
            # Preserve sources if they were provided or found before the error
            sources_used = urls if urls else (sources_used if sources_used else [])


        # --- Result Formatting ---
        research_result = {
            "topic": topic,
            "content": content, # This might be scraped content or an error message
            "timestamp": datetime.now().isoformat(),
            "sources": sources_used # Store the list of URLs used (provided or found)
        }

        logger.info(f"Research completed for topic: '{topic}'. Sources count: {len(sources_used)}. Content length: {len(content) if content else 0}")
        # logger.debug(f"Research result: {research_result}") # Optional debug

        return research_result

    async def _process_urls(self, urls: list[str]) -> str | None:
        """Processes a list of specific URLs using Crawl4AI."""
        contents = []
        logger.info(f"Processing {len(urls)} URLs with Crawl4AI...")
        for url in urls:
            try:
                # Use Crawl4aiTools' web_crawler function
                # It might return a string directly or need parsing depending on crawl4ai version/output
                scraped_data = await self.scraper_tool.web_crawler(url=url) # Pass url as named argument
                if scraped_data: # Assuming it returns the text content directly
                    contents.append(f"--- Source: {url} ---\n\n{scraped_data}")
                else:
                    logger.warning(f"Crawl4AI returned no content for {url}")
            except Exception as e:
                logger.error(f"Error processing {url} with Crawl4AI: {e}", exc_info=True)

        return "\n\n".join(contents) if contents else None

    async def _search_and_analyze(self, topic: str) -> tuple[str | None, list[str]]:
        """Performs web search using Serper API, scrapes results with Crawl4AI, and returns content and sources."""
        logger.info(f"Performing web search with Serper API for: {topic}")
        found_sources = []
        scraped_content = None

        # --- 1. Perform Web Search using Serper API ---
        serper_url = "https://google.serper.dev/search"
        payload = json.dumps({"q": topic, "num": 5}) # Request 5 results
        headers = {
            'X-API-KEY': settings.SERPER_API_KEY, # Get key from settings
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", serper_url, headers=headers, data=payload, timeout=10) # Added timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            search_results = response.json()
            logger.info(f"Serper API response received.")
            # logger.debug(f"Serper API full response: {json.dumps(search_results, indent=2)}") # Optional: log full response if needed

            # --- 2. Extract URLs from Serper results ---
            # Structure depends on Serper response, common is {'organic': [{'link': '...'}]}
            urls_to_scrape = []
            if 'organic' in search_results and isinstance(search_results['organic'], list):
                urls_to_scrape = [item.get('link') for item in search_results['organic'] if isinstance(item, dict) and item.get('link')]
            else:
                logger.warning(f"Serper response missing 'organic' results list or format unexpected.")

            if not urls_to_scrape:
                 logger.warning(f"Serper search for '{topic}' did not return valid URLs in 'organic' results.")
                 return f"Serper search for '{topic}' did not return valid URLs.", []

            found_sources = urls_to_scrape
            logger.info(f"Found {len(found_sources)} URLs from Serper.")

            # --- 3. Scrape content from found URLs using Crawl4AI ---
            scraped_content = await self._process_urls(found_sources) # Reuse URL processing logic

            if not scraped_content:
                logger.warning(f"Crawl4AI failed to extract content from any of the URLs found for '{topic}'.")
                # Return sources even if scraping failed
                return f"Crawl4AI failed to extract content from the found URLs for '{topic}'.", found_sources

            return scraped_content, found_sources

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Serper API for '{topic}': {e}", exc_info=True)
            return f"Error calling Serper API: {e}", []
        except json.JSONDecodeError as e:
             logger.error(f"Error decoding JSON response from Serper API for '{topic}': {e}", exc_info=True)
             return f"Error decoding Serper API response: {e}", []
        except Exception as e:
            # Catch-all for other potential errors during search or scraping phase
            logger.error(f"Unexpected error during search/analysis for '{topic}': {e}", exc_info=True)
            # Return partial sources if available
            return scraped_content or f"Unexpected error during search/analysis: {e}", found_sources


# Instancia global del agente (considerar si necesita el mcp_client)
# researcher = ResearcherAgent(mcp_client=mcp) # Example if MCP client is passed
researcher = ResearcherAgent() # Current instantiation

# Función auxiliar run_research eliminada ya que la lógica principal está en research()
