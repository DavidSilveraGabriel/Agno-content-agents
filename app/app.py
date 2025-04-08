import streamlit as st
import sys
import os
import asyncio
from typing import Iterator

# --- WINDOWS ASYNCIO FIX (MUST BE AT THE VERY BEGINNING) ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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
    logger.exception("Import Error in Streamlit app") # Log the full traceback
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

# --- Initialize the workflow as a singleton ---
@st.cache_resource
def get_workflow(session_id):
    # Consider if debug_mode should be configurable, e.g., via secrets or env var
    return SocialContentWorkflow(session_id=session_id, debug_mode=False)

# --- Workflow Execution ---
st.header("2. Generate Content")

# Define a function to handle the workflow execution as a callback
def on_generate_content():
    if not topic:
        st.warning("Please enter a topic.")
        return

    if use_urls:
        urls_list = [url.strip() for url in urls_text.splitlines() if url.strip()]
        if not urls_list:
            st.warning("Please enter at least one URL when the checkbox is selected, or uncheck it.")
            return
    else:
        urls_list = None

    st.info(f"Starting content generation for topic: '{topic}'" + (f" using {len(urls_list)} URL(s)." if urls_list else "..."))
    logger.info(f"Triggering workflow for topic: '{topic}' with URLs: {urls_list}")

    # Create a unique session ID (optional but good practice)
    # Using a simple counter or timestamp might be better than topic if topic changes slightly
    # For now, keeping topic-based ID
    url_safe_topic = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in topic)[:50]
    session_id = f"streamlit-social-content-{url_safe_topic}"

    # Get the singleton workflow instance
    try:
        workflow_instance = get_workflow(session_id)
    except Exception as e:
        st.error(f"Failed to initialize the workflow: {e}")
        logger.exception("Failed to get workflow instance")
        return

    progress_bar_placeholder = st.empty() # Placeholder for progress bar
    status_text_placeholder = st.empty() # Placeholder for status text
    st.session_state["final_result"] = None  # Clear previous result
    st.session_state["error_message"] = None
    st.session_state["workflow_running"] = True

    # --- Helper function to consume the async generator and update progress ---
    async def run_workflow_and_collect(workflow, topic_str, urls_list_param, progress_bar_ph, status_text_ph):
        collected_result = None
        progress_bar = None # Initialize progress bar variable
        try:
            async for response in workflow.arun(topic=topic_str, urls=urls_list_param):
                # Ensure UI elements are created only once
                if progress_bar is None:
                     progress_bar = progress_bar_ph.progress(0) # Create progress bar here
                     status_text = status_text_ph.empty() # Create status text here

                # Check for run_started event AND specific progress content structure
                if response.event == RunEvent.run_started and isinstance(response.content, dict) and response.content.get("type") == "progress":
                    # Update progress bar and status text
                    progress_value = response.content.get("value", 0)
                    step_description = response.content.get("step", "Working...")
                    progress_bar.progress(progress_value)
                    status_text.text(f"Progress: {step_description} ({int(progress_value * 100)}%)")
                    logger.debug(f"Workflow progress: {step_description} ({progress_value*100:.0f}%)")
                elif response.event == RunEvent.workflow_completed:
                    # Capture the final result content
                    collected_result = response.content
                    logger.info("Workflow completed event received.")
                # Keep track of the last content if it's the final output type,
                # in case the workflow_completed event doesn't contain it directly
                elif isinstance(response.content, FinalContentOutput):
                     collected_result = response.content

            # Ensure progress bar reaches 100% at the end if successful and exists
            if collected_result and not st.session_state.get("error_message"):
                 if progress_bar:
                     progress_bar.progress(1.0)
                 if 'status_text' in locals():
                     status_text.text("Progress: Workflow Completed (100%)")
                 logger.info("Workflow finished successfully.")

        except Exception as e:
            logger.error(f"Error running workflow async loop: {e}", exc_info=True)
            st.session_state["error_message"] = f"An error occurred during workflow execution: {e}" # Store the error
            collected_result = None # Ensure we don't display partial results
            # Optionally clear progress bar/text on error
            progress_bar_ph.empty()
            status_text_ph.empty()


        st.session_state["workflow_running"] = False # The workflow is not running
        return collected_result

    # --- Run the workflow using asyncio.run ---
    async def run_workflow():
        # Pass the placeholders to the async function
        result = await run_workflow_and_collect(workflow_instance, topic, urls_list, progress_bar_placeholder, status_text_placeholder)
        st.session_state["final_result"] = result

        # Check for errors again after completion (although usually caught inside)
        if st.session_state.get("error_message"):
             logger.error(f"Workflow errored: {st.session_state.get('error_message')}")
             # Consider if st.rerun() is needed to force UI update after async completion
             # st.rerun() # Uncomment if UI doesn't update reliably after error

    try:
        # --- FIX: Use asyncio.run() to execute the async function ---
        # This will create an event loop, run the coroutine, and close the loop.
        # It blocks the Streamlit callback until the async function completes.
        logger.info("Starting asyncio.run(run_workflow)...")
        asyncio.run(run_workflow())
        logger.info("asyncio.run(run_workflow) finished.")
        # ------------------------------------------------------------

    except Exception as e:
        # This catches errors during the setup/call of asyncio.run itself
        logger.error(f"Error initiating or running the Agno workflow via asyncio.run: {e}", exc_info=True)
        st.session_state["error_message"] = f"An error occurred starting or running the workflow: {e}"
        st.session_state["workflow_running"] = False # Ensure state is correct
        # Clear placeholders if error happened before run_workflow_and_collect handled it
        progress_bar_placeholder.empty()
        status_text_placeholder.empty()

    # Force a rerun AFTER the async operation completes/errors
    # to ensure the UI below reflects the final state correctly.
    st.rerun()


# --- Display Button (Consider moving above results header for flow) ---
st.button(
    "✨ Generate Content",
    type="primary",
    disabled=st.session_state.get("workflow_running", False), # Disable while running
    on_click=on_generate_content,
    key="generate_button" # Add a key for stability
)

# --- Display Results or Errors ---
st.header("3. Results")

# Check for "workflow_running" state in session state
if st.session_state.get("workflow_running", False):
    st.info("⏳ Workflow is running... Please wait.") # Show message if workflow is running
    # Progress bar/text are handled within the on_generate_content callback's async part

elif st.session_state.get("error_message"):
    st.error(f"❌ Workflow failed: {st.session_state['error_message']}") # Display stored error

elif "final_result" in st.session_state and st.session_state["final_result"]:
    final_result = st.session_state["final_result"]

    if isinstance(final_result, FinalContentOutput):
        st.success("✅ Workflow completed successfully!")

        # Check for non-fatal errors reported by the workflow itself
        if hasattr(final_result, "errors") and final_result.errors:
            st.warning(f"Workflow completed with non-fatal issues: {'; '.join(final_result.errors)}")

        st.subheader("Generated Content:")
        # Use columns for better layout if content is long
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Blog Post Idea:**\n```markdown\n{final_result.blog_post_md}\n```")
            st.markdown(f"**LinkedIn Post:**\n```markdown\n{final_result.linkedin_post}\n```")
        with col2:
            st.markdown(f"**X (Twitter) Post:**\n```markdown\n{final_result.twitter_post}\n```")
            st.markdown(f"**Instagram Post:**\n```markdown\n{final_result.instagram_post_caption}\n```")

        st.markdown("---") # Separator
        st.markdown(f"**Research Summary:**\n```markdown\n{final_result.research_context}\n```")

        if hasattr(final_result, "sources") and final_result.sources:
            st.subheader("Sources Used:")
            # Use columns for sources too if list is long
            num_sources = len(final_result.sources)
            if num_sources > 5:
                cols = st.columns(2)
                midpoint = (num_sources + 1) // 2
                for i, source in enumerate(final_result.sources):
                     with cols[0 if i < midpoint else 1]:
                         st.markdown(f"- {source}")
            else:
                for source in final_result.sources:
                    st.markdown(f"- {source}")
        else:
            st.caption("No specific external sources were cited in the final output.")

    elif isinstance(final_result, dict): # Handle unexpected dictionary results
        st.warning("Workflow returned a dictionary instead of the expected format.")
        st.json(final_result)
    else: # Handle other unexpected results
        st.warning("Workflow returned an unexpected result type.")
        st.write("Received result:", final_result)

elif not st.session_state.get("generate_button"): # Check if button was ever clicked
     st.info("Enter a topic and click 'Generate Content' to start.")
# else: # Implicitly means button was clicked but no result/error/running state set (shouldn't happen often)
#     st.info("Workflow finished, awaiting results display...")


# --- Optional: Add footer or other UI elements ---
st.markdown("---")
st.caption("Powered by Agno & Streamlit")