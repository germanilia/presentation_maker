import http.client
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from models.presentation_config import PresentationConfig
from src.content_generator import ContentGenerator


class WebResult(BaseModel):
    """Similar to YouTubeVideo but for web results"""

    score: float
    title: str
    domain: str
    url: str
    description: str
    published_date: str = ""


def search_serper(query: str, max_results: int = 5) -> List[WebResult]:
    """Search using Serper API"""
    logging.info(f"Searching Serper API for query: {query}")
    try:
        api_key = os.getenv("SERPER_API_KEY")
        if not api_key:
            raise Exception("Error: Serper API key not found in environment variables")

        conn = http.client.HTTPSConnection("google.serper.dev")
        payload = json.dumps({"q": query})
        headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
        conn.request("POST", "/search", payload, headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        results = []
        logging.info(f"Found {len(data.get('organic', []))} organic results")
        for item in data.get("organic", []):
            result = WebResult(
                score=calculate_result_score(item),
                title=item.get("title", ""),
                domain=item.get("domain", ""),
                url=item.get("link", ""),
                description=item.get("snippet", ""),
                published_date=item.get("date", ""),
            )
            results.append(result)

        logging.info(f"Returning {len(results[:max_results])} results")
        return results[:max_results]

    except Exception as e:
        logging.error(f"Error searching Serper: {str(e)}")
        raise Exception(f"Error searching Serper: {str(e)}")


def calculate_result_score(result: dict) -> float:
    """Calculate relevance score for web results"""
    # Simplified scoring example - can be enhanced based on needs
    score = 0.5  # Base score

    # Boost score if result has a date
    if result.get("date"):
        score += 0.2

    # Boost score if result has rich snippets
    if result.get("richSnippet"):
        score += 0.3

    return round(score, 3)


def scrape_webpage(url: str) -> str:
    """Scrape main content from webpage"""
    logging.info(f"Starting to scrape webpage: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()

        # Get text content
        text = soup.get_text(separator="\n", strip=True)
        logging.info(f"Successfully scraped {len(text)} characters from {url}")
        return text
    except Exception as e:
        logging.error(f"Error scraping webpage {url}: {str(e)}")
        return f"Error scraping webpage: {str(e)}"


class SerperAgent:
    def __init__(self, content_generator: ContentGenerator, max_results: int = 5):
        """Initialize SerperAgent"""
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY environment variable is not set")

        self.content_generator = content_generator
        self.max_results = max_results

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def process_topic(self, presentation: PresentationConfig) -> dict:
        """Process a topic to generate web content summaries"""
        self.logger.info(f"Starting to process topic: {presentation.topic}")
        self.presentation = presentation
        return self.execute()

    def execute(self) -> dict:
        """Execute the web search and summarization process sequentially"""
        self.logger.info(f"Processing {len(self.presentation.sub_topics)} subtopics")
        summaries = {}

        for subtopic in self.presentation.sub_topics:
            self.logger.info(f"Processing subtopic: {subtopic}")
            try:
                summary = self._process_subtopic(subtopic)
                summaries[subtopic] = summary
                self.logger.info(f"Successfully processed subtopic: {subtopic}")
            except Exception as e:
                self.logger.error(f"Error processing subtopic {subtopic}: {str(e)}")
                summaries[subtopic] = f"Error: {str(e)}"

        self.logger.info("Finished processing all subtopics")
        return summaries

    def _process_subtopic(self, subtopic: str) -> str:
        """Process a single subtopic"""
        search_query = self._generate_search_query(subtopic)
        results = search_serper(search_query, self.max_results)
        return self._summarize_results(results, subtopic)

    def _generate_search_query(self, subtopic: str) -> str:
        return f"{self.presentation.topic} {subtopic}"

    def _summarize_results(self, results: List[WebResult], current_topic: str) -> str:
        """Summarize web results"""
        all_content = []

        for result in results:
            # Skip YouTube URLs
            if "youtube.com" in result.url.lower():
                self.logger.info(f"Skipping YouTube URL: {result.url}")
                continue

            self.logger.info(f"Processing webpage: {result.title}")
            self.logger.info(f"URL: {result.url}")

            content = scrape_webpage(result.url)
            all_content.append(content)

        # Combine and summarize all content
        combined_content = "\n\n".join(all_content)
        return self._create_summary(
            combined_content,
            extra_instructions=f"Focus specifically on aspects related to {current_topic}.",
        )

    def _create_summary(self, text: str, extra_instructions: str = "") -> str:
        """Create summary from text content"""
        self.logger.info("Generating summary with content generator")
        prompt = f"""
        <content>
        {text}
        </content>
        You are a helpful assistant that summarizes web content. The audience is people looking
        to learn about {self.presentation.topic}. 
        Keep in mind the subtopics are {self.presentation.sub_topics}.
        Create a comprehensive summary of the content. Mind the details as they are important.
        The summary should be easy to understand and follow.
        {extra_instructions}
        """
        summary = self.content_generator.generate_text(
            prompt=prompt, model_id="amazon.nova-lite-v1:0"
        )
        if summary:
            self.logger.info(
                f"Successfully generated summary of {len(summary)} characters"
            )
        else:
            self.logger.error("Failed to generate summary")
        return summary if summary else "Error: Could not generate summary"
