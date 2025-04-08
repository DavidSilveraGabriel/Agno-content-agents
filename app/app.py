import streamlit as st
import sys
import os
import asyncio
from typing import Iterator

# Add the project root to the Python path to allow importing from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # Import necessary components from the Agno project
    from src.workflows.social_content_workflow import SocialContentWorkflow, FinalContentOutput
    from src.utils.logging_config import logger
    # Import RunEvent for progress updates
    from agno.workflow import RunEvent
except ImportError as e:
    st.error(f"Error importing project modules: {e}. Make sure the project structure is correct and dependencies are installed.")
    st.stop()

# --- Streamlit App UI ---
st.set_page_config(page_title="Agno Content Generator", layout="wide")

# --- Custom CSS for Text Wrapping ---
# Apply word wrap to preformatted text blocks used by st.markdown's code fences
st.markdown("""
<style>
    /* Target code blocks within Streamlit's markdown rendering */
    .stMarkdown pre code {
        white-space: pre-wrap !important; /* Allow wrapping */
        word-wrap: break-word !important; /* Break long words */
    }
    /* Ensure the container itself allows wrapping */
     .stMarkdown pre {
        white-space: pre-wrap !important;
        word-wrap: break-word !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 Agno Social Content Generator")
st.caption("Generate content for multiple platforms using AI agents.")

# --- Input Fields ---
st.header("1. Input Topic and URLs")
topic = st.text_input(
    "Enter the main topic:",
    placeholder="e.g., The future of AI in content creation",
    value="What are MCPs (Model Context Protocols) and why you should use them?" # Default value
)

use_urls = st.checkbox("Provide specific URLs for research?")
urls_text = st.text_area(
    "Enter URLs (one per line):",
    placeholder="https://example.com/article1\nhttps://anotherexample.com/blogpost",
    height=100,
    disabled=not use_urls
)

# --- Workflow Execution ---
st.header("2. Generate Content")
if st.button("✨ Generate Content", type="primary", disabled=not topic):
    urls_list = [url.strip() for url in urls_text.splitlines() if url.strip()] if use_urls else None

    st.info(f"Starting content generation for topic: '{topic}'" + (f" using URLs: {urls_list}" if urls_list else "..."))

    try:
        # --- Instantiate and Run Workflow ---
        # Create a unique session ID (optional but good practice)
        url_safe_topic = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in topic)[:50]
        session_id = f"streamlit-social-content-{url_safe_topic}"

        # Instantiate the workflow
        # Note: Ensure any required dependencies like Redis/Chroma are running if used by agents/workflow
        workflow_instance = SocialContentWorkflow(session_id=session_id, debug_mode=False) # Set debug_mode as needed

        st.write("Workflow started...")
        progress_bar = st.progress(0) # Add progress bar
        status_text = st.empty() # Add status text placeholder
        final_result = None
        error_message = None
        final_result = None # Initialize final_result

        # --- Helper function to consume the async generator and update progress ---
        async def run_workflow_and_collect(workflow, topic_str, urls_list_param, progress_bar_ui, status_text_ui):
            collected_result = None
            async for response in workflow.arun(topic=topic_str, urls=urls_list_param):
                # Check for run_started event AND specific progress content structure
                if response.event == RunEvent.run_started and isinstance(response.content, dict) and response.content.get("type") == "progress":
                    # Update progress bar and status text
                    progress_value = response.content.get("value", 0)
                    step_description = response.content.get("step", "Working...")
                    progress_bar_ui.progress(progress_value)
                    status_text_ui.text(f"Progress: {step_description} ({int(progress_value * 100)}%)")
                elif response.event == RunEvent.workflow_completed:
                    # Capture the final result content
                    collected_result = response.content
                # Removed check for RunEvent.error as it's not available and errors are handled via final_result.errors
                # Keep track of the last content if it's the final output type,
                # in case the workflow_completed event doesn't contain it directly (though it should)
                elif isinstance(response.content, FinalContentOutput):
                     collected_result = response.content

            # Ensure progress bar reaches 100% at the end if successful
            if collected_result and not error_message:
                 progress_bar_ui.progress(1.0)
                 status_text_ui.text("Progress: Workflow Completed (100%)")
            return collected_result

        # --- Running the Async Workflow in Streamlit ---
        try:
            # No longer need st.spinner as we have the progress bar
            # Run the helper function that consumes the async generator
            final_result = asyncio.run(run_workflow_and_collect(workflow_instance, topic, urls_list, progress_bar, status_text))

            # --- Process the collected final result ---
            if isinstance(final_result, FinalContentOutput):
                st.success("✅ Workflow completed successfully!")
                if final_result.errors:
                     st.warning(f"Workflow completed with errors: {'; '.join(final_result.errors)}")
            elif isinstance(final_result, dict) and "error" in final_result: # Check if workflow yielded an error dict
                 error_message = f"Workflow failed: {final_result['error']}"
            elif final_result is None:
                 error_message = "Workflow did not produce a final result or an error."
            else:
                 # Handle unexpected final result types
                 logger.warning(f"Workflow finished with unexpected result type: {type(final_result)}")
                 st.success("✅ Workflow finished (result format may vary).")
                 # Optionally display the raw result if it's not the expected type
                 # st.write("Raw result:", final_result)

        except Exception as e:
            logger.error(f"Error running Agno workflow via asyncio.run: {e}", exc_info=True)
            error_message = f"An error occurred during workflow execution: {e}"

        # --- Display Results or Errors ---
        st.header("3. Results")
        if error_message:
            st.error(error_message)
        elif final_result:
            if isinstance(final_result, FinalContentOutput):
                st.subheader("Generated Content:")
                st.markdown(f"**Blog Post Idea:**\n```markdown\n{final_result.blog_post_md}\n```") # Corrected attribute name
                st.markdown(f"**LinkedIn Post:**\n```markdown\n{final_result.linkedin_post}\n```")
                st.markdown(f"**X (Twitter) Post:**\n```markdown\n{final_result.twitter_post}\n```") # Corrected attribute name
                st.markdown(f"**Instagram Post:**\n```markdown\n{final_result.instagram_post_caption}\n```") # Corrected attribute name
                st.markdown(f"**Research Summary:**\n```markdown\n{final_result.research_context}\n```") # Corrected attribute name

                # Display sources if available
                if final_result.sources:
                    st.subheader("Sources Used:")
                    for source in final_result.sources:
                        st.markdown(f"- {source}")
            elif isinstance(final_result, dict): # Fallback if it's just a dict
                 st.json(final_result)
            else:
                 st.write("Received result:", final_result)

        else:
            st.warning("No results were generated.")

    except Exception as e:
        logger.error(f"Critical error setting up or running workflow: {e}", exc_info=True)
        st.error(f"A critical error occurred: {e}")

# --- Optional: Add footer or other UI elements ---
st.markdown("---")
st.caption("Powered by Agno & Streamlit")
