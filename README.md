# Agno Social Content Generation Workflow

This project utilizes the Agno framework to create an automated workflow for generating social media and blog content based on a given topic. It employs multiple AI agents orchestrated by a central workflow, interacting with external APIs like Google Gemini and potentially Firecrawl for research. The user interface is provided via a Streamlit web application.

## Features

-   **Multi-Platform Content:** Generates draft content for:
    -   Blog Post (Markdown)
    -   LinkedIn Post
    -   X (Twitter) Post
    -   Instagram Post Caption (with placeholder image ideas)
-   **AI-Powered:** Leverages Google Gemini via the Agno framework for content generation.
-   **Research Capability:** Includes a researcher agent that can analyze provided URLs or (with future MCP integration) perform web searches using Firecrawl.
-   **Workflow Orchestration:** Uses an Agno `Workflow` to manage the sequence of research and content generation steps.
-   **Streamlit UI:** Provides a simple web interface (`app/app.py`) to input topics/URLs and view results.
-   **Error Handling & Retries:** Implements basic retry logic with exponential backoff for API calls to handle rate limiting.
-   **Progress Tracking:** Displays a progress bar in the Streamlit UI during content generation.
-   **Output Saving:** Saves the consolidated results in a JSON file and the blog post in a Markdown file within the `output/` directory.

## Project Structure

```
AGNO/
├── app/                  # Streamlit UI application
│   └── app.py
├── src/                  # Core Agno project source code
│   ├── agents/          # Agent definitions (Researcher, BlogWriter, etc.)
│   ├── config/          # Configuration (settings.py)
│   ├── tools/           # Custom tools 
│   ├── workflows/       # Workflow definitions (social_content_workflow.py)
│   └── utils/           # Utility functions (logging, file operations)
├── output/               # Default directory for generated content files
├── logs/                 # Log files (if logging to file is configured)
├── tests/                # Unit and integration tests (optional)
├── .env                  # Environment variables (API Keys, etc. - **DO NOT COMMIT**)
├── .env.example          # Example environment variables file
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── .gitignore            # Specifies intentionally untracked files
```

## Requirements

-   Python 3.10+
-   Agno Framework
-   Streamlit
-   Google Generative AI SDK (`google-genai`)
-   Pydantic
-   See `requirements.txt` for the full list and specific versions.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/DavidSilveraGabriel/Agno-content-agents.git
    cd AGNO
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    -   Copy the example file:
        ```bash
        cp .env.example .env
        ```
    -   Edit the `.env` file and add your API keys:
        -   `GOOGLE_API_KEY`: Your Google AI Studio (Gemini) API key.
        -   `FIRECRAWL_API_KEY`: Your Firecrawl API key (required for the researcher agent's web scraping/search functionality).
        -   *(Add any other required keys)*

## Usage

1.  Ensure your virtual environment is activated.
2.  Make sure the necessary API keys are set in your `.env` file.
3.  Run the Streamlit application from the project root directory:
    ```bash
    streamlit run app/app.py
    ```
4.  Open the provided URL (usually `http://localhost:8501`) in your web browser.
5.  Enter a topic for content generation.
6.  Optionally, provide specific URLs for the researcher agent to analyze.
7.  Click "Generate Content" and monitor the progress bar.
8.  View the generated content drafts in the UI.
9.  Check the `output/` directory for the saved JSON and Markdown files.

## Development

*(Optional: Add details about running tests, linting, etc. if applicable)*

```bash
# Example: Install development dependencies (if you have a [dev] extra in setup.py or similar)
# pip install -e ".[dev]"

# Example: Run tests (if using pytest)
# pytest

# Example: Format code (if using black/isort)
# black src app tests
# isort src app tests
```

## License

*(Specify your project's license, e.g., MIT License)*


