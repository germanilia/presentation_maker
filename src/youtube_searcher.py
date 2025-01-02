import os
import requests
from datetime import datetime
from typing import List
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from pydantic import BaseModel
from models.presentation_config import PresentationConfig
from src.content_generator import ContentGenerator
from math import log
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed


class YouTubeVideo(BaseModel):
    score: float
    title: str
    channel_name: str
    views: int
    likes: int
    subscribers: int
    days_since_published: int
    video_id: str
    url: str
    description: str


def search_youtube(topic: str, max_results: int = 5) -> List[YouTubeVideo]:
    """
    Search YouTube videos using the YouTube Data API v3

    Args:
        topic: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List[YouTubeVideo]: List of YouTubeVideo objects containing video information
    """
    try:
        # Get API key from environment variable
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise Exception("Error: YouTube API key not found in environment variables")

        # Search for videos
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "maxResults": max_results,
            "q": topic,
            "type": "video",
            "key": api_key,
        }

        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()

        if "items" not in search_data:
            raise Exception(f"No results found or API error: {search_data.get('error', {}).get('message', 'Unknown error')}")

        results = []
        for item in search_data["items"]:
            video_id = item["id"]["videoId"]

            # Get video statistics
            video_url = "https://www.googleapis.com/youtube/v3/videos"
            video_params = {
                "part": "statistics,snippet",
                "id": video_id,
                "key": api_key,
            }

            video_response = requests.get(video_url, params=video_params)
            video_data = video_response.json()

            if "items" in video_data and video_data["items"]:
                video_stats = video_data["items"][0]["statistics"]
                video_snippet = video_data["items"][0]["snippet"]

                # Get channel statistics
                channel_id = item["snippet"]["channelId"]
                channel_url = "https://www.googleapis.com/youtube/v3/channels"
                channel_params = {
                    "part": "statistics",
                    "id": channel_id,
                    "key": api_key,
                }

                channel_response = requests.get(channel_url, params=channel_params)
                channel_data = channel_response.json()

                # Calculate days since published
                publish_date = datetime.strptime(
                    video_snippet["publishedAt"][:10], "%Y-%m-%d"
                )
                days_since_published = (datetime.now() - publish_date).days

                view_count = video_stats.get("viewCount", "0")
                like_count = video_stats.get("likeCount", "0")
                subscriber_count = (
                    channel_data["items"][0]["statistics"].get("subscriberCount", "0")
                    if "items" in channel_data
                    else "0"
                )

                video = YouTubeVideo(
                    score=calculate_score(
                        days_since_published,
                        int(view_count),
                        int(subscriber_count),
                        int(like_count),
                    ),
                    title=video_snippet["title"],
                    channel_name=video_snippet["channelTitle"],
                    views=int(view_count),
                    likes=int(like_count),
                    subscribers=int(subscriber_count),
                    days_since_published=days_since_published,
                    video_id=video_id,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    description=video_snippet["description"][:200],
                )
                results.append(video)

        return results

    except Exception as e:
        raise Exception(f"Error searching YouTube: {str(e)}")


def calculate_score(
    days_since_published: int, views: int, subscribers: int, likes: int
) -> float:
    """
    Calculate video score based on multiple metrics

    Args:
        days_since_published: Number of days since video was published
        views: Number of video views
        subscribers: Number of channel subscribers
        likes: Number of video likes

    Returns:
        float: Calculated score between 0 and 1
    """
    # Convert metrics to numbers, use 0 if N/A
    views = int(views) if str(views).isdigit() else 0
    subscribers = int(subscribers) if str(subscribers).isdigit() else 0
    likes = int(likes) if str(likes).isdigit() else 0

    # Normalize dates (newer = better, max age considered is 365 days)
    date_score = max(0, (365 - min(days_since_published, 365)) / 365)

    # Normalize other metrics using log scale to handle large numbers
    # Add 1 to avoid log(0)
    view_score = min(1, log(views + 1) / log(10000000))  # Assuming 10M views is max
    subscriber_score = min(
        1, log(subscribers + 1) / log(10000000)
    )  # Assuming 10M subs is max
    like_score = min(1, log(likes + 1) / log(100000))  # Assuming 100K likes is max

    # Calculate weighted score
    final_score = (
        0.4 * date_score + 0.4 * view_score + 0.1 * subscriber_score + 0.1 * like_score
    )

    return round(final_score, 3)


def get_video_transcript(video_url: str) -> str:
    """
    Get the transcript/subtitles from a YouTube video

    Args:
        video_url: Full YouTube video URL or video ID

    Returns:
        str: Formatted transcript text or error message
    """
    try:
        # Extract video ID from URL
        if "youtube.com" in video_url or "youtu.be" in video_url:
            if "youtube.com" in video_url:
                query = urlparse(video_url).query
                video_id = parse_qs(query).get("v", [None])[0]
            else:  # youtu.be
                video_id = urlparse(video_url).path[1:]
        else:
            # Assume the input is directly a video ID
            video_id = video_url

        if not video_id:
            return "Error: Could not extract video ID from URL"

        # Get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Format transcript text
        formatted_transcript = ""
        for entry in transcript_list:
            formatted_transcript += f"{entry['text']}\n"

        return formatted_transcript

    except Exception as e:
        return f"Error getting transcript: {str(e)}"


def create_summary(text: str, presentation: PresentationConfig, content_generator: ContentGenerator, extra_instructions: str = "") -> str:
    prompt = f"""
    <transcript>
    {text}
    </transcript>
    You are a helpful assistant that summarizes YouTube videos. The audience is people looking
    to learn about a {presentation.topic}. 
    Keep in mind the subtopics are {presentation.sub_topics}.
    You are required to create a comprehensive summary of the video. Mind the details they are important.
    The summary should be in a way that is easy to understand and follow.
    The summary should capture the essence of the video and create a detailed summary of the video.
    Do not mentioned the video or what was transcribed, just create a summary of the video.
    {extra_instructions}
    """
    summary = content_generator.generate_text(prompt=prompt, model_id="amazon.nova-lite-v1:0")
    return summary if summary else "Error: Could not generate summary"


def generate_video_summary(video: YouTubeVideo, presentation: PresentationConfig, content_generator: ContentGenerator) -> str:
    transcript = get_video_transcript(video.url)
    summary = create_summary(transcript, presentation, content_generator)
    return summary


def summarize_videos(videos: List[YouTubeVideo], presentation: PresentationConfig, content_generator: ContentGenerator) -> str:
    summaries = []
    for video in videos:
        summary = generate_video_summary(video, presentation, content_generator)
        summaries.append(summary)
    return create_summary(
        str(summaries),
        presentation,
        content_generator,
        extra_instructions="The summaries are from different videos. Combine them into a single summary.",
    )


def generate_search_query(topic: str, subtopic: str , content_generator: ContentGenerator) -> str:
    """
    Generate a search query combining topic, subtopic, and instructions using LLM
    
    Args:
        topic: Main topic
        subtopic: Optional subtopic to combine with main topic
        instructions: Optional additional search instructions/keywords
        content_generator: ContentGenerator instance for text generation
        
    Returns:
        str: Generated search query
    """

    prompt = f"""
    You are required to capture the essence of the topic and subtopic. and generate
    a search query which will be used to search for videos on YouTube.
    
    Topic: {topic}
    {f'Subtopic: {subtopic}' if subtopic else ''}

    The query should be as similar as possible to the topic and subtopic combination.
    
    Return only the search query, nothing else dont add any additional subjects just create a clear query.
    """

    query = content_generator.generate_text(prompt=prompt, model_id="amazon.nova-lite-v1:0")
    return query.strip() if query else f"{topic} {subtopic}".strip()


class YouTubeAgent:
    def __init__(self, content_generator: ContentGenerator, max_results: int = 1):
        """Initialize YouTubeAgent"""
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is not set")
            
        self.content_generator = content_generator
        self.max_results = max_results

        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def process_topic(self, presentation: PresentationConfig) -> dict:
        """
        Process a topic to generate video summaries
        
        Args:
            topic: The topic to search for on YouTube
            
        Returns:
            dict: Dictionary containing summaries for main topic and subtopics
        """
        self.presentation = presentation
        return self.execute()

    def execute(self) -> dict:
        """Main method to execute the YouTube search and summarization process in parallel"""
        summaries = {}
        
        with ThreadPoolExecutor() as executor:
            # Create future tasks for each subtopic
            future_to_subtopic = {
                executor.submit(self._process_subtopic, subtopic): subtopic 
                for subtopic in self.presentation.sub_topics
            }
            
            # Wait for all tasks to complete and collect results
            for future in as_completed(future_to_subtopic):
                subtopic = future_to_subtopic[future]
                try:
                    summary = future.result()
                    summaries[subtopic] = summary
                except Exception as e:
                    self.logger.error(f"Error processing subtopic {subtopic}: {str(e)}")
                    summaries[subtopic] = f"Error: {str(e)}"
        
        return summaries

    def _process_subtopic(self, subtopic: str) -> str:
        """Process a single subtopic in a separate thread"""
        search_query = generate_search_query(
            self.presentation.topic,
            subtopic,
            content_generator=self.content_generator
        )
        videos = self._search_youtube(search_query)
        return self._summarize_videos(videos, subtopic)

    def _search_youtube(self, search_query: str) -> List[YouTubeVideo]:
        """Internal method to search YouTube videos"""
        return search_youtube(search_query, self.max_results)

    def _summarize_videos(self, videos: List[YouTubeVideo], current_topic: str) -> str:
        """Internal method to generate summaries for videos"""
        # If there's only one video, process it directly
        if len(videos) == 1:
            video = videos[0]
            self.logger.info(f"Processing video for topic '{current_topic}': {video.title}")
            self.logger.info(f"Video URL: {video.url}")
            
            transcript = self._get_video_transcript(video.url)
            return self._create_summary(
                transcript,
                extra_instructions=f"Focus specifically on aspects related to {current_topic}."
            )
        
        # For multiple videos
        summaries = []
        for i, video in enumerate(videos, 1):
            self.logger.info(f"Processing video {i}/{len(videos)} for topic '{current_topic}': {video.title}")
            self.logger.info(f"Video URL: {video.url}")
            
            transcript = self._get_video_transcript(video.url)
            summary = self._create_summary(
                transcript,
                extra_instructions=f"Focus specifically on aspects related to {current_topic}."
            )
            summaries.append(summary)
        
        # Create and return combined summary
        return self._create_summary(
            str(summaries),
            extra_instructions=f"The summaries are from different videos about {current_topic}. Combine them into a single cohesive summary focusing on this specific aspect."
        )

    def _get_video_transcript(self, video_url: str) -> str:
        """Internal method to get video transcript"""
        return get_video_transcript(video_url)

    def _create_summary(self, text: str, extra_instructions: str = "") -> str:
        """Internal method to create summary"""
        return create_summary(text, self.presentation, self.content_generator, extra_instructions)
