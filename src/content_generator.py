import base64
import io
import json
import logging
import os
import re
from typing import List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

from models.presentation_config import PresentationConfig, Slide
from models.slide import PowerPointSlide, PowerPointSlides

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ImageError(Exception):
    """Custom exception for errors returned by Amazon Nova Canvas"""

    def __init__(self, message):
        self.message = message


class ContentGenerator:
    def __init__(self, session=None):
        logger.info("Initializing ContentGenerator")
        # Use provided session or create default
        if session:
            self.bedrock = session.client(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                config=Config(read_timeout=300),
            )
        else:
            # Fallback to default client creation
            self.bedrock = boto3.client(
                service_name="bedrock-runtime",
                region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                config=Config(read_timeout=300),
            )
        self.canvas_model = os.getenv("CANVAS_MODEL", "amazon.nova-canvas-v1:0")
        self.anthropic_model = os.getenv(
            "ANTHROPIC_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.nova_model = os.getenv("NOVA_MODEL", "amazon.nova-lite-v1:0")
        logger.info(
            f"Using models - Canvas: {self.canvas_model}, Anthropic: {self.anthropic_model}, Nova: {self.nova_model}"
        )

    def generate_image_from_text(
        self,
        text,
        output_path,
        height=1024,
        width=1024,
        cfg_scale=8.0,
        seed=0,
        max_retries=3,
    ):
        logger.info(
            f"Starting image generation for text: {text[:100]}..."
        )  # Log truncated text
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                error_context = ""
                if last_error:
                    error_context = f" Previous attempt failed with error: {last_error}. Please adjust the description to avoid this error."

                # Generate detailed image description first
                image_description = self.generate_image_description(
                    text + error_context
                )
                if not image_description:
                    logger.error("Failed to generate image description")
                    retry_count += 1
                    continue

                # Create output directory if it doesn't exist
                output_dir = os.path.dirname(output_path)
                if output_dir:
                    # Ensure the path is properly normalized and absolute
                    output_dir = os.path.normpath(os.path.abspath(output_dir))
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                    except OSError as e:
                        logger.error(
                            f"Failed to create directory {output_dir}: {str(e)}"
                        )
                        return None

                # Validate input parameters
                if not text or not text.strip():
                    logger.error("Empty or invalid prompt text provided")
                    return None

                if not output_path:
                    logger.error("No output path provided")
                    return None

                # Log the request parameters for debugging
                logger.info(
                    f"Generating image with parameters: height={height}, width={width}, cfg_scale={cfg_scale}, seed={seed}"
                )
                logger.info(f"Prompt text: {text}")

                # Simplified request body matching the example
                body = json.dumps(
                    {
                        "taskType": "TEXT_IMAGE",
                        "textToImageParams": {"text": image_description},
                        "imageGenerationConfig": {
                            "numberOfImages": 1,
                            "height": height,
                            "width": width,
                            "cfgScale": cfg_scale,
                            "seed": seed,
                        },
                    }
                )

                # Log the API request body
                logger.info(f"Request body: {body}")

                response = self.bedrock.invoke_model(
                    body=body,
                    modelId=self.canvas_model,
                    accept="application/json",
                    contentType="application/json",
                )

                response_body = json.loads(response.get("body").read())

                # Check for errors first
                if response_body.get("error"):
                    raise ImageError(
                        f"Image generation error. Error is {response_body.get('error')}"
                    )

                # Get the base64 image directly
                base64_image = response_body.get("images")[0]
                if not base64_image:
                    raise ImageError("No images returned in the response")

                # Convert and save the image
                base64_bytes = base64_image.encode("ascii")
                image_bytes = base64.b64decode(base64_bytes)
                image = Image.open(io.BytesIO(image_bytes))
                image.save(output_path)

                logger.info(f"Successfully generated and saved image to {output_path}")
                return output_path

            except ClientError as err:
                last_error = err.response["Error"]["Message"]
                logger.warning(f"Attempt {retry_count + 1} failed: {last_error}")
            except ImageError as err:
                last_error = err.message
                logger.warning(f"Attempt {retry_count + 1} failed: {last_error}")
            except Exception as err:
                last_error = str(err)
                logger.warning(f"Attempt {retry_count + 1} failed: {last_error}")

            retry_count += 1

        logger.error(
            f"Failed to generate image after {max_retries} attempts. Last error: {last_error}"
        )
        return None

    def generate_slides(
        self, presentation: PresentationConfig, extra_content: dict[str, str]
    ) -> List[PowerPointSlide]:
        logger.info(f"Generating slides for presentation: {presentation.topic}")
        logger.info(f"Number of content sections to process: {len(extra_content)}")
        slides = []
        cover_slide = Slide(title=presentation.topic, style="cover")
        slides.append(cover_slide)
        for title, content in extra_content.items():
            logger.info(f"Processing slide for title: {title}")
            max_retries = 3
            retry_count = 0
            last_error = ""  # Initialize last_error variable

            while retry_count < max_retries:
                error_context = ""
                if retry_count > 0:
                    error_context = f"\nPrevious attempt failed with error: {last_error}\nPlease fix the error and ensure the JSON is valid."

                prompt = f"""
                Based on the following title and content, create a single detailed slide for a presentation about {title}.
                Raw Content: {content}
                {error_context}
                
                The slide should capture the content essence and create interesting and engaging content
                based on the title and content. Need to make sure the slide content will be readable and make sense.
                The structure should be according to the content type, use bullets for several topics in one slide
                use table to compare topics, if there is no comparison use paragraph style or bullets.
                
                Important: When using bullets style each bullet point should have a header, and a content
                they will be separated by a dash.
                
                The Slide's content must be directly related to the title and based on the content.
                Don't add any additional content to the slide, just the content from the raw content.
                
                * Header - Content (a single string)
                There should not be more than 5 bullets per slide.
                
                The output should be in JSON format.
                The first char of the output should be curly bracket.
                
                The slide should follow this schema:
                class PowerPointSlide(BaseModel):
                    title: str
                    subtitle: str
                    style: One of ["cover", "bullets", "table", "paragraph"]
                    content: Union[str, List[Union[str, BulletPoint]], TableContent]
                    image_path: str = ""
                    layout: dict = {{"image_position": "right", "image_width": 0.5}}
                    
                Output must be valid JSON for a single slide.
                """

                # Generate and validate single slide
                response = self.generate_text(prompt, True)
                if response:
                    try:
                        slide = PowerPointSlide.model_validate_json(response)
                        slide.comments = content
                        slides.append(slide)
                        break  # Success, exit retry loop
                    except Exception as e:
                        last_error = str(e)
                        logger.warning(
                            f"Attempt {retry_count + 1} failed for title '{title}': {last_error}"
                        )
                        retry_count += 1
                        continue

                retry_count += 1

            if retry_count == max_retries:
                logger.error(
                    f"Failed to generate valid slide for title '{title}' after {max_retries} attempts"
                )

        return slides

    def save_base64_image(self, base64_string, output_path) -> str | None:
        """
        Save a base64 encoded image string to a file

        Args:
            base64_string (str): The base64 encoded image string
            output_path (str): Path where the image will be saved

        Returns:
            str: Path to the saved image if successful, None otherwise
        """
        try:
            # Validate base64 string
            if not base64_string or not isinstance(base64_string, str):
                logger.error("Invalid base64 string provided")
                return None

            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if output_dir:
                output_dir = os.path.normpath(os.path.abspath(output_dir))
                os.makedirs(output_dir, exist_ok=True)

            try:
                # Decode and save the image
                base64_bytes = base64_string.encode("ascii")
                image_bytes = base64.b64decode(base64_bytes)

                # Remove any potential padding or extra data before JPEG header
                jpeg_header = b"\xff\xd8"
                if jpeg_header in image_bytes:
                    start_idx = image_bytes.index(jpeg_header)
                    image_bytes = image_bytes[start_idx:]

                # Create BytesIO object with cleaned data
                image_stream = io.BytesIO(image_bytes)
                image_stream.seek(0)

                # Try to open and save the image with explicit format
                image = Image.open(image_stream)
                image.save(output_path, format=image.format if image.format else "JPEG")

                logger.info(f"Successfully saved image to {output_path}")
                return output_path

            except Image.UnidentifiedImageError as e:
                logger.error(f"Could not identify image format: {str(e)}")
                logger.debug(f"First 100 bytes: {image_bytes[:100].hex()}")
                return None

        except Exception as err:
            logger.error(f"Failed to save base64 image: {str(err)}")
            logger.debug(f"Error type: {type(err).__name__}")
            return None

    def generate_text(
        self,
        prompt,
        return_json: bool = False,
        model_id: str | None = None,
        max_tokens: int = 4096,
    ):
        """
        Generate text using Amazon Nova Pro model

        Args:
            prompt (str): The input text prompt
            response_start_with (str | None): Optional starting text for the response
            return_json (bool): If True, attempts to extract and validate JSON from response
            model_id (str | None): Optional model ID to use. Defaults to self.text_model_id

        Returns:
            str: Generated text or JSON string if return_json=True, None if error occurs
        """
        model_id = model_id if model_id is not None else self.anthropic_model
        logger.info(f"Generating text with model: {model_id or self.anthropic_model}")
        logger.debug(f"Prompt (truncated): {prompt[:200]}...")
        try:
            if model_id == self.nova_model:
                body = json.dumps(
                    {
                        "inferenceConfig": {"max_new_tokens": 1000},
                        "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    }
                )
            else:
                body = json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": max_tokens,
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"type": "text", "text": prompt}],
                            }
                        ],
                    }
                )

            response = self.bedrock.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json",
            )

            response_body = json.loads(response.get("body").read())

            # Handle different response formats based on model
            if model_id == self.nova_model:
                response_text = (
                    response_body.get("output").get("message").get("content")[0]["text"]
                )
            else:
                response_text = response_body["content"][0]["text"]

            if return_json:
                logger.debug("Attempting to extract JSON from response")
                # Extract JSON using regex
                json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    json_str = json_str.replace("\n", "").replace("'", "")
                    # Validate that it's valid JSON
                    try:
                        json.loads(json_str)
                        return json_str
                    except json.JSONDecodeError:
                        logger.error("Extracted text is not valid JSON")
                        return None
                else:
                    logger.error("No JSON found in response")
                    return None

            return response_text

        except ClientError as err:
            logger.error(
                "A client error occurred: %s", err.response["Error"]["Message"]
            )
            return None
        except Exception as err:
            logger.error("An unexpected error occurred: %s", str(err))
            return None

    def generate_image_description(self, text: str) -> str | None:
        """
        Generate a detailed image description from text using the fast text model

        Args:
            text (str): The base text to generate an image description from

        Returns:
            str: Enhanced image description if successful, None otherwise
        """
        logger.info("Generating image description")
        logger.debug(f"Input text: {text[:100]}...")  # Log truncated text
        try:
            description_prompt = f"""Create an image description for: {text}
            Focus on visual elements, style, composition, and mood. Make it specific and descriptive 
            for an AI image generator. Include details about:
            - Main subject and positioning
            - Lighting and atmosphere
            - Color palette
            - Style (photorealistic, artistic, etc.)
            - Perspective and composition
            Keep it under 100 words and make it cohesive.
            The output need to be a short paragraph, not title, bullets etc. example
            Examples:
            A realistic image of a person looking on a ball 35 mm lense camera
            An abstract image machine thinking about the future
            A futuristic image of a person looking on a ball 35 mm lense camera
            
            Try to capture the essence of the text and create a detailed description of the image.
            It must be relevant to the discussed topic
            
            NEVER USE PEOPLE NAMES IN THE DESCRIPTION
            NEVER ADD TEXT TO IMAGES
            NEVER ADD SPECIAL CHARS ONLY LETTERS AND NUMBERS
            Based on the examples, create a description for the above text
            
            """

            description = self.generate_text(
                description_prompt, model_id=self.nova_model
            )

            logger.info(f"Generated image description: {description}")
            return description

        except Exception as err:
            logger.error("An unexpected error occurred: %s", str(err))
            return None
