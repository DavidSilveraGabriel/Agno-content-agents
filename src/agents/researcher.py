import json
import httpx # <-- Import httpx
import os
from datetime import datetime
import asyncio
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.crawl4ai import Crawl4aiTools
from agno.storage.sqlite import SqliteStorage

# Assuming settings are in src/config/settings.py
# Make sure you have:


from src.config.settings import settings


from src.utils.logging_config import logger


class MyCrawl4aiTools(Crawl4aiTools):
    """Custom wrapper for Crawl4aiTools to add basic error handling."""
    async def web_crawler(self, url: str, max_length: int | None = None) -> str | None:
        try:
            # Note: Crawl4AI might have its own timeout/error handling.
            # Consider adding specific exception catching if needed.
            content = await self._async_web_crawler(url, max_length)
            if content is None:
                logger.warning(f"MyCrawl4aiTools.web_crawler returned None for {url}")
            return content
        except Exception as e:
            # Log specific errors encountered during crawling
            logger.error(f"Error in MyCrawl4aiTools.web_crawler processing {url}: {e}", exc_info=False) # exc_info=False to avoid overly verbose logs for common crawl errors
            return None # Return None on error


class ResearcherAgent:
    def __init__(self):
        # --- Tool Configuration ---
        # Consider adding timeout configuration to Crawl4aiTools if available
        self.scraper_tool = MyCrawl4aiTools(max_length=None) # Set reasonable max_length?

        # --- Storage Configuration ---
        db_path = os.path.join("tmp", "researcher_storage.db") # Use os.path.join for cross-platform compatibility
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.storage = SqliteStorage(table_name="researcher_sessions", db_file=db_path)

        # --- Agent Configuration ---
        if not settings.GOOGLE_API_KEY:
            logger.warning("GOOGLE_API_KEY not found in settings or environment variables. ResearcherAgent might fail.")

        self.agent = Agent(
            name="ResearcherAgent",
            # Use a default model or handle missing key more gracefully?
            model=Gemini(id="gemini-1.5-flash", api_key=settings.GOOGLE_API_KEY), # Using 1.5 Flash as example
            tools=[self.scraper_tool],
            storage=self.storage,
            add_history_to_messages=True,
            num_history_responses=3,
            description="You are an expert researcher. Use provided URLs or search the web to gather information on a topic.",
            instructions=[
                "1. Analyze the provided topic.",
                "2. If specific URLs are provided, use the web_crawler tool to extract content from EACH URL.",
                "3. If NO URLs are provided, perform a web search using the Serper API (via internal logic, not a tool call) to find relevant URLs.",
                "4. After finding URLs (from search), use the web_crawler tool to extract content from the MOST PROMISING ones (e.g., top 3-5).",
                "5. Synthesize the gathered information from all processed URLs into a comprehensive summary.",
                "6. Clearly list the source URLs used for the final summary.",
                "7. If you encounter errors accessing a URL or find no relevant content, note that but try other sources.",
                "8. If the search yields no usable URLs, or crawling fails for all found URLs, state that clearly."
            ],
            add_datetime_to_instructions=False, # Usually not needed unless time-sensitivity is critical
            markdown=True, # Use Markdown for potentially better structured LLM output
            show_tool_calls=True, # Useful for debugging tool usage
            debug_mode=False, # Set to True for more verbose Agno logging if needed
        )

    async def research(self, topic: str, urls: list[str] | None = None) -> dict:
        """
        Researches a topic using provided URLs or by searching the web.

        Args:
            topic: The topic to research.
            urls: A list of specific URLs to process (optional).

        Returns:
            A dictionary containing the research results:
            {
                "topic": str,
                "content": str | None, # Synthesized summary or error message
                "timestamp": str,
                "sources": list[str] # List of URLs successfully processed
            }
        """
        logger.info(f"Starting research for topic: '{topic}' with provided URLs: {bool(urls)}")

        final_content: str | None = None
        processed_sources: list[str] = []
        error_message: str | None = None

        try:
            if urls:
                logger.info(f"Processing {len(urls)} provided URLs...")
                final_content, processed_sources = await self._process_urls(urls)
                if not final_content:
                    error_message = "Processing provided URLs yielded no usable content."
                    logger.warning(f"{error_message} for topic: {topic}")
            else:
                logger.info("No URLs provided, performing web search and analysis...")
                search_content, search_sources = await self._search_and_analyze(topic)
                if search_content:
                    final_content = search_content
                    processed_sources = search_sources
                else:
                    # Use the error message from _search_and_analyze if content is None
                    error_message = search_sources[0] if search_sources and isinstance(search_sources[0], str) else "Web search and analysis failed to yield content."
                    logger.warning(f"Search/analyze yielded no content for topic '{topic}'. Reason: {error_message}")
                    processed_sources = [] # Ensure sources list is empty if search failed

        except Exception as e:
            logger.error(f"Unexpected error during research method for topic '{topic}': {e}", exc_info=True)
            error_message = f"An unexpected error occurred during research: {e}"
            final_content = None # Ensure content is None on major error
            # Keep any sources processed before the error, if applicable
            processed_sources = processed_sources or (urls if urls else [])

        # Prepare the final result dictionary
        research_result = {
            "topic": topic,
            # Prioritize content, but include error message if content is missing
            "content": final_content if final_content else error_message,
            "timestamp": datetime.now().isoformat(),
            "sources": processed_sources, # Only list sources that contributed content
        }

        log_content_len = len(final_content) if final_content else 0
        log_status = "successfully" if final_content else f"with errors ({error_message})"
        logger.info(
            f"Research for topic: '{topic}' completed {log_status}. "
            f"Sources processed: {len(processed_sources)}. Content length: {log_content_len}."
        )

        return research_result

    async def _process_urls(self, urls_to_process: list[str]) -> tuple[str | None, list[str]]:
        """
        Processes a list of URLs using the web_crawler tool and combines the content.

        Args:
            urls_to_process: List of URLs to crawl.

        Returns:
            A tuple containing:
            - Combined content string (or None if no content found).
            - List of URLs from which content was successfully extracted.
        """
        contents = []
        successful_sources = []
        logger.info(f"Processing {len(urls_to_process)} URLs with Crawl4AI...")

        # Process URLs concurrently using asyncio.gather for efficiency
        tasks = [self.scraper_tool.web_crawler(url=url) for url in urls_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True) # Gather results, including exceptions

        for url, result in zip(urls_to_process, results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {url} with Crawl4AI task: {result}", exc_info=False)
            elif result:
                contents.append(f"--- Source: {url} ---\n\n{result}\n\n--- End Source: {url} ---")
                successful_sources.append(url)
                logger.debug(f"Successfully scraped content from {url} (Length: {len(result)})")
            else:
                logger.warning(f"Crawl4AI returned no content or failed for {url}")

        if contents:
            logger.info(f"Successfully extracted content from {len(successful_sources)} out of {len(urls_to_process)} URLs.")
            return "\n\n".join(contents), successful_sources
        else:
            logger.warning(f"Failed to extract any content from the provided {len(urls_to_process)} URLs.")
            return None, []

    async def _search_and_analyze(self, topic: str, num_results_to_scrape: int = 3) -> tuple[str | None, list[str]]:
        """
        Searches the web using Serper, then scrapes the top results using Crawl4AI.

        Args:
            topic: The topic to search for.
            num_results_to_scrape: Max number of search results to attempt scraping.

        Returns:
            A tuple containing:
            - Combined content string from scraped results (or None).
            - List of URLs successfully scraped OR a list containing an error message if search fails.
        """
        logger.info(f"Performing web search with Serper API for: {topic}")

        # --- Get API Key from Settings ---
        api_key_to_use = settings.SERPER_API_KEY

        # --- LÍNEA DE DEBUGGING TEMPORAL ---
        print(f"DEBUG: Valor recuperado de settings.SERPER_API_KEY: '{api_key_to_use}'")
        logger.info(f"DEBUG: Valor recuperado de settings.SERPER_API_KEY: '{api_key_to_use}'")

        # Check if the API key is available
        if not api_key_to_use:
             logger.error("SERPER_API_KEY not found in settings or environment variables. Cannot perform web search.")
             # Return None content and an error message in the sources list
             return None, ["Serper API key is missing."]
        # ----------------------------------

        serper_url = "https://google.serper.dev/search"
        payload = json.dumps({"q": topic, "num": 10}) # Ask for more results initially
        headers = {
            "X-API-KEY": api_key_to_use,
            "Content-Type": "application/json",
        }

        # --- DEBUGGING: Log the key being used ---
        logger.info(f"Attempting Serper API call for '{topic}' using API Key ending with: ...{api_key_to_use[-4:] if api_key_to_use and len(api_key_to_use) >= 4 else 'INVALID_OR_SHORT'}")
        # -----------------------------------------

        urls_to_scrape = []
        try:
            # --- Use httpx for async request ---
            async with httpx.AsyncClient(timeout=15.0) as client: # Set a reasonable timeout
                response = await client.post(serper_url, headers=headers, content=payload)
            # ----------------------------------

            logger.debug(f"Serper API raw response status: {response.status_code}")
            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses
            search_results = response.json()
            logger.info(f"Serper API response received successfully for topic: {topic}")

            # Extract organic result URLs safely
            organic_results = search_results.get("organic", [])
            if isinstance(organic_results, list):
                urls_to_scrape = [
                    item.get("link")
                    for item in organic_results
                    if isinstance(item, dict) and item.get("link") and isinstance(item.get("link"), str)
                ]
            else:
                logger.warning("Serper response 'organic' field is not a list or missing.")

            if not urls_to_scrape:
                logger.warning(f"Serper search for '{topic}' did not return any valid URLs in 'organic' results.")
                return None, [f"Web search for '{topic}' did not return usable URLs."] # Error message in list

            logger.info(f"Found {len(urls_to_scrape)} potential URLs from Serper. Attempting to scrape top {num_results_to_scrape}.")

            # Take only the top N results to scrape
            urls_to_try = urls_to_scrape[:num_results_to_scrape]

            # Process the found URLs using the same helper function
            scraped_content, successful_sources = await self._process_urls(urls_to_try)

            if not scraped_content:
                logger.warning(
                    f"Crawl4AI failed to extract content from any of the top {len(urls_to_try)} URLs found for '{topic}'."
                )
                # Return None, but include the list of URLs *tried* for context
                return None, [f"Crawling failed for top search results: {', '.join(urls_to_try)}"]

            # Return the content and the list of *successfully* scraped sources
            return scraped_content, successful_sources

        # --- Specific httpx exceptions ---
        except httpx.HTTPStatusError as e:
             logger.error(f"Serper API returned error status {e.response.status_code} for '{topic}': {e.response.text}", exc_info=False)
             return None, [f"Error calling Search API (Status {e.response.status_code})"]
        except httpx.RequestError as e:
            logger.error(f"Network error calling Serper API for '{topic}': {e}", exc_info=False)
            return None, [f"Network error during web search: {e}"]
        # ---------------------------------
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON response from Serper API for '{topic}': {e}", exc_info=True)
            # Log the raw response text if possible and not too large
            try:
                raw_text = response.text[:500] # Log beginning of text
                logger.error(f"Serper raw response text (start): {raw_text}")
            except NameError: # response might not be defined if httpx call failed earlier
                pass
            return None, ["Error decoding search results."]
        except Exception as e:
            logger.error(f"Unexpected error during search/analysis for '{topic}': {e}", exc_info=True)
            return None, [f"Unexpected error during search: {e}"]

# --- Agent Instantiation ---
# This creates a single instance when the module is imported.
researcher = ResearcherAgent()
