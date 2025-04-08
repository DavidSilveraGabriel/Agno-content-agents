# workflows/social_content_workflow.py
import json
import asyncio # Needed for potential parallel execution and sleep
import time # For potential synchronous sleep if needed, though asyncio.sleep is preferred
from typing import AsyncIterator, Optional, Dict, List # Use AsyncIterator
from agno.workflow import Workflow, RunResponse, RunEvent
from agno.agent import Agent
from agno.exceptions import ModelProviderError # Import exception for retry logic (ToolError removed)
from src.agents.researcher import researcher, ResearcherAgent # Import the instance and the class
from src.agents.blog_writer import blog_writer_agent
from src.agents.linkedin_writer import linkedin_writer_agent
from src.agents.x_writer import x_writer_agent
from src.agents.instagram_writer import instagram_writer_agent
from src.utils.logging_config import logger # Corrected import
from src.utils.file_utils import save_json, save_markdown # Corrected import
from pydantic import BaseModel

# Definimos un modelo Pydantic para la salida JSON final
class FinalContentOutput(BaseModel):
    topic: str
    research_context: Optional[str] = None # Explicit default
    blog_post_md: Optional[str] = None # Explicit default
    linkedin_post: Optional[str] = None # Explicit default
    twitter_post: Optional[str] = None # Explicit default
    instagram_post_caption: Optional[str] = None # Explicit default
    instagram_image_ideas: Optional[List[str]] = None # Explicit default
    sources: Optional[List[str]] = None # Add field for sources
    errors: List[str] = [] # Para rastrear errores

class SocialContentWorkflow(Workflow):
    description: str = "Genera contenido para blog y redes sociales sobre un tema."

    # Los agentes se definen como atributos para que el workflow los gestione
    # Note: researcher is the ResearcherAgent class instance, not an Agno Agent directly,
    # but we'll call its methods. Adjust type hint if needed, or wrap it.
    # For simplicity, we keep the structure but call the instance method.
    researcher_instance: ResearcherAgent = researcher # Store the instance
    blog_writer: Agent = blog_writer_agent
    linkedin_writer: Agent = linkedin_writer_agent
    twitter_writer: Agent = x_writer_agent
    instagram_writer: Agent = instagram_writer_agent

    async def arun(self, topic: str, urls: Optional[List[str]] = None) -> AsyncIterator[RunResponse]: # Changed to async def arun
        """
        Orquesta la generación de contenido para redes sociales y blog.
        1. Investiga el tema (o URLs dadas).
        2. Genera contenido para Blog, LinkedIn, Twitter, Instagram.
        3. Consolida y guarda los resultados.
        """
        logger.info(f"Iniciando workflow para el tema: '{topic}'")
        # Use workflow_started for the initial event
        yield RunResponse(content=f"Iniciando investigación para: {topic}", event=RunEvent.workflow_started)

        final_output = FinalContentOutput(topic=topic)
        research_context = None
        research_sources = urls or [] # Initialize sources with user URLs if provided

        # --- 1. Investigación ---
        yield RunResponse(content=f"Iniciando investigación para: {topic}", event=RunEvent.run_started) # Use run_started

        try:
            if urls:
                # Option 1: Use researcher agent to scrape provided URLs
                logger.info(f"Procesando URLs proporcionadas: {urls}")
                # Assuming researcher.research handles URL scraping and returns content + sources
                # We might need to adjust researcher.research if its role changes
                research_data = await self.researcher_instance.research(topic=topic, urls=urls)
                research_context = research_data.get("content")
                # research_sources are already set to urls from initialization
                if not research_context:
                    logger.error("No se pudo extraer contenido de las URLs proporcionadas.")
                    final_output.errors.append("No se pudo extraer contenido de las URLs proporcionadas.")
                    # Stop the workflow here if scraping fails critically
                    return

            else:
                # Option 2: Delegate web search and scraping to ResearcherAgent
                logger.info(f"No se proporcionaron URLs. Delegando investigación a ResearcherAgent para: {topic}")
                yield RunResponse(content=f"Delegando investigación a ResearcherAgent para: {topic}...", event=RunEvent.run_started)

                # Call the researcher agent's method. It will handle search/scrape internally.
                research_data = await self.researcher_instance.research(topic=topic, urls=None)
                research_context = research_data.get("content")
                research_sources = research_data.get("sources", []) # Get sources found by the agent

                if not research_context:
                    logger.error("ResearcherAgent no devolvió contenido después de la búsqueda web.")
                    final_output.errors.append("ResearcherAgent no devolvió contenido después de la búsqueda web.")
                    # Stop the workflow here if research fails critically
                    return

            # --- Post-Research Processing ---
            if not research_context:
                logger.error("La investigación no produjo resultados después de intentar el método apropiado.")
                final_output.errors.append("La investigación inicial no produjo contenido.")
                # Stop the workflow here if research fails critically
                return

            final_output.research_context = research_context # Store the gathered context
            final_output.sources = research_sources # Store the final list of sources (user-provided or found)
            logger.info("Investigación completada.")
            # Yield progress update
            yield RunResponse(content={"type": "progress", "value": 0.2, "step": "Investigación completada"}, event=RunEvent.run_started)
            # Removed step_completed event as it seems unavailable
            # yield RunResponse(content="Investigación completada. Generando contenido...", event=RunEvent.step_completed) # Removed
        except Exception as e:
            # Catch any exception during research phase (including potential tool errors)
            logger.error(f"Error durante la fase de investigación (incluyendo llamadas a herramientas): {e}", exc_info=True)
            final_output.errors.append(f"Error en investigación/herramienta: {e}")
            # Stop the workflow here if research fails critically
            return

        # --- 2. Generación de Contenido (paralelizable si usamos asyncio) ---
        # Example of running sequentially (easier for MVP)
        # If parallel needed: tasks = [asyncio.create_task(agent.arun(research_context)) for agent, _ in ...]
        # results = await asyncio.gather(*tasks)
        content_generation_tasks = {
            "blog": (self.blog_writer, "blog_post_md"),
            "linkedin": (self.linkedin_writer, "linkedin_post"),
            "twitter": (self.twitter_writer, "twitter_post"),
            "instagram": (self.instagram_writer, "instagram_post_caption") # El de instagram devuelve caption + ideas
        }

        total_steps = 1 + len(content_generation_tasks) # 1 for research + N platforms
        current_step = 1 # Start after research

        for platform, (agent, output_key) in content_generation_tasks.items():
            logger.info(f"Generando contenido para {platform.capitalize()}...")
            # Use run_started when beginning a sub-step (based on error suggestion)
            yield RunResponse(content=f"Generando post para {platform.capitalize()}...", event=RunEvent.run_started) # Changed to run_started

            response = None # Initialize response for the platform
            max_retries = 3
            initial_delay = 5 # seconds

            for attempt in range(max_retries):
                try:
                    # Use arun for async agents if available, otherwise run
                    if hasattr(agent, 'arun'):
                         # Await the arun coroutine directly as it likely returns a single response
                         response = await agent.arun(final_output.research_context)
                         # Removed the async for loop as arun doesn't seem to be an async iterator
                         break # Success, exit retry loop
                    else:
                         # Fallback for potentially synchronous agents (though Agno agents are typically async)
                         # This part might need review if all agents are truly async
                         response = agent.run(final_output.research_context) # This might block
                         break # Success, exit retry loop

                except ModelProviderError as e:
                    # Check if it's a rate limit error (e.g., 429)
                    # The specific check might depend on how ModelProviderError exposes status code
                    # Assuming e.status_code exists or checking the message string
                    is_rate_limit = False
                    if hasattr(e, 'status_code') and e.status_code == 429:
                        is_rate_limit = True
                    elif "429" in str(e): # Fallback check in message
                        is_rate_limit = True

                    if is_rate_limit and attempt < max_retries - 1:
                        delay = 20 # Fixed 20-second delay for rate limit retries
                        logger.warning(f"Rate limit hit for {platform.capitalize()}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                    else:
                        # Log error if it's the last attempt or not a rate limit error
                        logger.error(f"Error generating content for {platform.capitalize()} after {attempt + 1} attempts: {e}", exc_info=True)
                        final_output.errors.append(f"Error en {platform.capitalize()} (attempt {attempt + 1}): {e}")
                        response = None # Ensure response is None on final failure
                        break # Exit retry loop after final failure or non-retryable error
                except Exception as e: # Catch other unexpected errors
                    logger.error(f"Unexpected error generating content for {platform.capitalize()}: {e}", exc_info=True)
                    final_output.errors.append(f"Error inesperado en {platform.capitalize()}: {e}")
                    response = None # Ensure response is None
                    break # Exit retry loop

            # --- Process the response after retry loop ---
            if response and response.content:
                content = response.content
                # Manejo especial para Instagram que devuelve caption + ideas
                if platform == "instagram":
                     # Asumimos que el agente devuelve un string, necesitamos parsearlo o pedirle formato JSON
                     # Para MVP, podríamos intentar extraer ideas basadas en palabras clave
                     # O mejor, ajustar el prompt del agente de Instagram para que devuelva JSON
                     # Supongamos por ahora que devuelve texto y extraemos ideas heurísticamente o lo dejamos vacío
                     setattr(final_output, output_key, content)
                     final_output.instagram_image_ideas = ["Idea 1: Placeholder", "Idea 2: Placeholder"] # Placeholder
                     logger.warning("Extracción de ideas de imagen de Instagram no implementada completamente.")
                else:
                    setattr(final_output, output_key, content)
                logger.info(f"Contenido para {platform.capitalize()} generado.")
            elif not final_output.errors or not any(f"Error en {platform.capitalize()}" in err for err in final_output.errors):
                 # Only log warning if no specific error was already logged for this platform during retries
                 logger.warning(f"No se generó contenido para {platform.capitalize()} después de los reintentos.")
                 final_output.errors.append(f"No se generó contenido para {platform.capitalize()} después de los reintentos.")
            # Removed the outer try...except block as errors are handled within the retry loop now

            # Yield progress update after attempting platform generation (using run_started as a workaround for info)
            current_step += 1
            progress_value = current_step / total_steps
            yield RunResponse(content={"type": "progress", "value": progress_value, "step": f"{platform.capitalize()} completado"}, event=RunEvent.run_started)


        # --- 3. Consolidación y Salida ---
        logger.info("Consolidando resultados...")
        # Use run_started for the final consolidation step (based on error suggestion)
        yield RunResponse(content="Consolidando resultados...", event=RunEvent.run_started) # Changed to run_started

        # Crear nombre de archivo seguro
        safe_filename = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in topic)[:50]

        # Guardar JSON
        json_data = final_output.model_dump(exclude_none=True)
        save_json(json_data, f"social_content_{safe_filename}")

        # Guardar Markdown del Blog (si existe)
        if final_output.blog_post_md:
            save_markdown(final_output.blog_post_md, f"blog_post_{safe_filename}")

        logger.info("Workflow completado.")
        yield RunResponse(
            content=final_output, # Return the Pydantic model instance directly
            event=RunEvent.workflow_completed
        )
