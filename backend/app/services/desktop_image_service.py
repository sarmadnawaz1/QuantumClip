"""
Service to generate images using Replicate, Together AI, FAL AI, or Runware.ai.
Based on the RapidClips implementation with enhanced timeout and retry mechanisms.
"""
import os
import base64
import requests
import replicate
from together import Together
import fal_client
import time
import uuid
from app.utils import load_config

# Default timeout and retry settings
DEFAULT_TIMEOUT = 60  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2  # seconds (base for exponential backoff)

class ReplicateImageService:
    """
    Service to interact with the Replicate API for image generation using the Flux model.
    """

    def __init__(self, api_token=None):
        """
        Initialize the service with the Replicate API token.

        Args:
            api_token (str): Replicate API token.
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_KEY", "")
        os.environ["REPLICATE_API_TOKEN"] = self.api_token

    def generate_image(self, prompt, width=1408, height=768, steps=4):
        """
        Generate an image based on the given prompt using the model specified in config.

        Args:
            prompt (str): The prompt describing the image to generate.
            width (int): The width of the generated image.
            height (int): The height of the generated image.
            steps (int): Number of inference steps.

        Returns:
            bytes: The generated image data.
        """
        # Load configuration
        config = load_config()
        replicate_config = config["replicate_flux_api"]

        # Add a negative prompt to prevent text in the generated images
        negative_prompt = "text, words, letters, writing, captions, labels, watermark, signature, logo, title, subtitle, timestamp"

        # Determine if this is portrait or landscape
        is_portrait = height > width

        # Set aspect ratio based on orientation from config
        orientation = "portrait" if is_portrait else "landscape"
        aspect_ratio = replicate_config["aspect_ratio"].get(orientation, "9:16")

        print(f"Replicate service using aspect ratio: {aspect_ratio}")

        input_data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "aspect_ratio": aspect_ratio,  # Use aspect_ratio parameter directly
            "num_inference_steps": steps,
            "guidance_scale": 7.5
        }
        model_id = replicate_config["model"]

        try:
            print(f"Calling Replicate API with model: {model_id}")
            print(f"Input data: {input_data}")

            output = replicate.run(
                model_id,
                input=input_data
            )

            print(f"Replicate API response type: {type(output)}")

            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
                print(f"Image URL received: {image_url[:50]}...")
                response = requests.get(image_url)
                response.raise_for_status()
                # Return raw bytes; downstream pipeline will handle final sizing
                return response.content
            else:
                print(f"Unexpected response from Replicate API: {output}")
                return None
        except Exception as e:
            print(f"Error in Replicate API call: {str(e)}")
            # Try again with different parameters if there's an issue with dimensions
            try:
                print("Retrying with alternative parameters...")

                # Try with a different aspect ratio format
                # Sometimes the model works better with one format vs another
                alt_aspect_ratio = "0.5625" if aspect_ratio == "9:16" else "1.7778"

                print(f"Trying alternative aspect ratio format: {alt_aspect_ratio}")

                # Alternative input data
                alt_input = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "aspect_ratio": alt_aspect_ratio,  # Use numeric aspect ratio
                    "num_inference_steps": steps,
                    "guidance_scale": 7.5
                }

                output = replicate.run(
                    model_id,
                    input=alt_input
                )

                if isinstance(output, list) and len(output) > 0:
                    image_url = output[0]
                    print(f"Retry successful, image URL: {image_url[:50]}...")
                    response = requests.get(image_url)
                    response.raise_for_status()
                    # Return raw bytes; downstream pipeline will handle final sizing
                    return response.content
            except Exception as retry_error:
                print(f"Retry also failed: {str(retry_error)}")

            return None


class TogetherImageService:
    """
    Service to interact with Together AI API for image generation.
    """

    def __init__(self, api_token=None):
        """
        Initialize the Together AI service with an API token.

        Args:
            api_token (str): Together AI API token.
        """
        self.api_token = api_token or os.getenv("TOGETHER_API_KEY", "")
        self.client = Together(api_key=self.api_token)

    def generate_image(self, prompt, width=1408, height=768, steps=4, model=None, timeout=DEFAULT_TIMEOUT, max_retries=DEFAULT_MAX_RETRIES):
        """
        Generate an image based on the provided prompt using Together AI's models with timeout and retry.

        Args:
            prompt (str): The prompt to guide image generation.
            width (int): Width of the generated image (between 64 and 1792, must be multiple of 16).
            height (int): Height of the generated image (between 64 and 1792, must be multiple of 16).
            steps (int): Number of steps for image generation.
            model (str, optional): The model to use for image generation. If None, uses the model from config.
            timeout (int): Timeout in seconds for the API request.
            max_retries (int): Maximum number of retry attempts.

        Returns:
            bytes: The image data in binary format.

        Raises:
            Exception: If image generation fails after all retries.
        """
        # Load configuration if model is not specified
        if model is None:
            config = load_config()
            together_config = config["together_flux_api"]
            model = together_config["model"]

        # Ensure width and height are within the allowed range (64-1792)
        width = max(64, min(width, 1792))
        height = max(64, min(height, 1792))

        # Ensure width and height are multiples of 16
        width = (width // 16) * 16
        height = (height // 16) * 16

        # Add a negative prompt to prevent text in the generated images
        negative_prompt = "text, words, letters, writing, captions, labels, watermark, signature, logo, title, subtitle, timestamp"

        print(f"🎨 [TOGETHER] Generating image with Together AI using model: {model}")
        print(f"📝 [TOGETHER] Prompt: {prompt[:100]}...")
        print(f"📐 [TOGETHER] Dimensions: {width}x{height}, Steps: {steps}")
        print(f"⏱️ [TOGETHER] Timeout: {timeout}s, Max retries: {max_retries}")

        last_error = None

        for attempt in range(max_retries):
            try:
                print(f"🔄 [TOGETHER] Attempt {attempt + 1}/{max_retries}")

                # Generate image using Together AI with timeout
                response = self.client.images.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model=model,
                    width=width,
                    height=height,
                    steps=steps,
                    n=1,
                    response_format="b64_json",
                    timeout=timeout
                )

                # Get base64 encoded image
                image_b64 = response.data[0].b64_json

                # Decode the base64 image
                image_data = base64.b64decode(image_b64)
                print(f"✅ [TOGETHER] Image generation successful on attempt {attempt + 1}")
                # Return raw bytes; downstream pipeline will handle final sizing
                return image_data

            except Exception as e:
                last_error = e
                error_message = str(e)
                print(f"❌ [TOGETHER] Error on attempt {attempt + 1}: {error_message}")

                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (DEFAULT_RETRY_DELAY ** attempt) + (time.time() % 1)
                    print(f"⏳ [TOGETHER] Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"💥 [TOGETHER] All {max_retries} attempts failed")

        raise Exception(f"Error generating image with Together AI after {max_retries} attempts: {str(last_error)}")


class FalAIImageService:
    """
    Service to interact with the FAL AI API for image generation.
    """

    def __init__(self, api_token=None):
        """
        Initialize the FAL AI service with an API token.

        Args:
            api_token (str): FAL AI API token.
        """
        # FAL client expects the key in FAL_KEY environment variable
        self.api_token = api_token or os.getenv("FAL_KEY", "")

        # If FAL_KEY is not set, try FAL_API_KEY as fallback for backward compatibility
        if not self.api_token:
            self.api_token = os.getenv("FAL_API_KEY", "")
            if self.api_token:
                print("WARNING: Using FAL_API_KEY is deprecated. Please use FAL_KEY instead.")

        # Set the API key for FAL client
        if self.api_token:
            os.environ['FAL_KEY'] = self.api_token
        else:
            print("ERROR: No FAL AI API key found. Please set the FAL_KEY environment variable.")

    def generate_image(self, prompt, width=1080, height=1920, steps=4, timeout=DEFAULT_TIMEOUT, max_retries=DEFAULT_MAX_RETRIES):
        """
        Generate an image based on the given prompt using FAL AI with timeout and retry.

        Args:
            prompt (str): The prompt describing the image to generate.
            width (int): The width of the generated image.
            height (int): The height of the generated image.
            steps (int): Number of inference steps.
            timeout (int): Timeout in seconds for the API request.
            max_retries (int): Maximum number of retry attempts.

        Returns:
            bytes: The generated image data.

        Raises:
            Exception: If image generation fails after all retries.
        """
        # Add a negative prompt to prevent text in the generated images
        negative_prompt = "text, words, letters, writing, captions, labels, watermark, signature, logo, title, subtitle, timestamp"

        # Calculate aspect ratio
        aspect_ratio = width / height

        # Determine the appropriate image_size parameter based on aspect ratio
        # FAL AI expects specific string values or a properly formatted object
        if abs(aspect_ratio - 9/16) < 0.1:  # Portrait (9:16)
            image_size = "portrait_16_9"
        elif abs(aspect_ratio - 16/9) < 0.1:  # Landscape (16:9)
            image_size = "landscape_16_9"
        elif abs(aspect_ratio - 4/3) < 0.1:  # 4:3 aspect ratio
            if width > height:
                image_size = "landscape_4_3"
            else:
                image_size = "portrait_4_3"
        elif abs(aspect_ratio - 1) < 0.1:  # Square
            image_size = "square_hd"
        else:
            # For custom aspect ratios, use the width/height object format
            # Ensure dimensions are within FAL AI's limits
            max_dimension = 1024  # FAL AI typically has limits on dimensions

            # Scale dimensions to fit within limits while maintaining aspect ratio
            if width > height:
                if width > max_dimension:
                    scale = max_dimension / width
                    width = max_dimension
                    height = int(height * scale)
            else:
                if height > max_dimension:
                    scale = max_dimension / height
                    height = max_dimension
                    width = int(width * scale)

            # Use custom dimensions
            image_size = {
                "width": width,
                "height": height
            }

        print(f"🎨 [FAL] Generating image with FAL AI")
        print(f"📝 [FAL] Prompt: {prompt[:100]}...")
        print(f"📐 [FAL] Dimensions: {width}x{height}, Image size: {image_size}")
        print(f"⏱️ [FAL] Timeout: {timeout}s, Max retries: {max_retries}")

        # Load configuration
        config = load_config()
        fal_config = config["fal_flux_api"]

        last_error = None

        for attempt in range(max_retries):
            try:
                print(f"🔄 [FAL] Attempt {attempt + 1}/{max_retries}")

                # Submit request to FAL AI
                handler = fal_client.submit(
                    fal_config["model"],
                    arguments={
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "image_size": image_size,
                        "num_images": fal_config["num_images"],
                        "num_inference_steps": steps,
                        "enable_safety_checker": fal_config["enable_safety_checker"],
                    },
                )

                # Get the result with timeout consideration
                result = handler.get()

                if result and isinstance(result, dict) and "images" in result:
                    images = result["images"]
                    if isinstance(images, list) and images:
                        image_url = images[0].get("url")
                        if image_url:
                            print(f"✅ [FAL] Image generation successful on attempt {attempt + 1}")
                            response = requests.get(image_url, timeout=timeout)
                            response.raise_for_status()
                            # Return raw bytes; downstream pipeline will handle final sizing
                            return response.content

                print(f"❌ [FAL] No valid image data found in response on attempt {attempt + 1}")
                last_error = Exception("No valid image data found in FAL AI response")

            except Exception as e:
                last_error = e
                error_message = str(e)
                print(f"❌ [FAL] Error on attempt {attempt + 1}: {error_message}")

                # Special handling for 422/400 errors - try with fallback image size
                if ("422" in error_message or "400" in error_message) and attempt == 0:
                    print(f"🔄 [FAL] Trying with fallback image size...")
                    try:
                        fallback_image_size = "landscape_16_9" if width > height else "portrait_16_9"

                        handler = fal_client.submit(
                            fal_config["model"],
                            arguments={
                                "prompt": prompt,
                                "negative_prompt": negative_prompt,
                                "image_size": fallback_image_size,
                                "num_images": fal_config["num_images"],
                                "num_inference_steps": steps,
                                "enable_safety_checker": fal_config["enable_safety_checker"],
                            },
                        )

                        result = handler.get()
                        if result and isinstance(result, dict) and "images" in result:
                            images = result["images"]
                            if isinstance(images, list) and images:
                                image_url = images[0].get("url")
                                if image_url:
                                    print(f"✅ [FAL] Fallback successful with {fallback_image_size}")
                                    response = requests.get(image_url, timeout=timeout)
                                    response.raise_for_status()
                                    # Return raw bytes; downstream pipeline will handle final sizing
                                    return response.content
                    except Exception as fallback_error:
                        print(f"❌ [FAL] Fallback also failed: {fallback_error}")

                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = (DEFAULT_RETRY_DELAY ** attempt) + (time.time() % 1)
                    print(f"⏳ [FAL] Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"💥 [FAL] All {max_retries} attempts failed")

        raise Exception(f"Error generating image with FAL AI after {max_retries} attempts: {str(last_error)}")


class RunwareImageService:
    """
    Service to interact with the Runware.ai API for image generation.
    Uses the official Runware SDK when available, with fallback to direct API calls.
    """

    def __init__(self, api_token=None, model_type="flux_dev"):
        """
        Initialize the Runware.ai service with an API token.

        Args:
            api_token (str): Runware.ai API token.
            model_type (str): The model type to use (flux_dev, flex_schenele, or juggernaut_lightning).
        """
        self.api_token = api_token or os.getenv("RUNWARE_API_KEY", "")
        self.model_type = model_type

        # Load configuration
        config = load_config()
        self.runware_config = config["runware_flux_api"]

        # Get model ID from config
        self.model_id = self.runware_config["models"][self.model_type]["model_id"]

        # Always use direct API calls
        self.use_sdk = False
        print("Using direct API calls for Runware.ai")

    def generate_image(self, prompt, width=1344, height=768, steps=None, model_type=None, max_retries=DEFAULT_MAX_RETRIES, timeout=DEFAULT_TIMEOUT):
        """
        Generate an image based on the given prompt using Runware.ai with enhanced timeout and retry.

        Args:
            prompt (str): The prompt describing the image to generate.
            width (int): The width of the generated image.
            height (int): The height of the generated image.
            steps (int, optional): Number of inference steps. If None, uses the value from config.
            model_type (str, optional): The model type to use. If None, uses the model from initialization.
            max_retries (int): Maximum number of retry attempts.
            timeout (int): Timeout in seconds for the API request.

        Returns:
            bytes: The generated image data.

        Raises:
            Exception: If image generation fails after all retries.
        """
        import time
        import traceback

        print(f"🎨 [RUNWARE] Starting image generation...")
        print(f"📝 [RUNWARE] Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print(f"📐 [RUNWARE] Dimensions: {width}x{height}")
        print(f"🔧 [RUNWARE] Model: {model_type or self.model_type}")
        print(f"⏱️ [RUNWARE] Timeout: {timeout}s, Max retries: {max_retries}")

        for attempt in range(max_retries):
            try:
                print(f"🔄 [RUNWARE] Attempt {attempt+1}/{max_retries}")

                # Use provided model_type if specified, otherwise use the one from initialization
                if model_type:
                    self.model_type = model_type
                    self.model_id = self.runware_config["models"][self.model_type]["model_id"]
                    print(f"🔧 [RUNWARE] Updated model_type to {self.model_type}, model_id to {self.model_id}")

                # ALWAYS use dimensions from Runware config, overriding any provided dimensions
                # Get orientation based on aspect ratio
                orientation = "portrait"  # Default to portrait
                if width is not None and height is not None and width > height:
                    orientation = "landscape"

                # Get dimensions from config
                dimensions = self.runware_config["dimensions"].get(orientation, {})
                # Store original dimensions for logging
                original_width, original_height = width, height
                # Always override with dimensions from config
                width = dimensions.get("width", 1344)
                height = dimensions.get("height", 768)

                # Log if we're overriding provided dimensions
                if original_width is not None and original_height is not None and (original_width != width or original_height != height):
                    print(f"Overriding provided dimensions ({original_width}x{original_height}) with Runware.ai config dimensions: {width}x{height}")
                else:
                    print(f"Using dimensions from Runware.ai config: {width}x{height}")

                # Use model-specific steps if not provided
                if steps is None:
                    # Check if model has specific steps in config first
                    model_config = self.runware_config["models"].get(self.model_type, {})
                    if "steps" in model_config:
                        steps = model_config["steps"]
                        print(f"Using {steps} steps for {self.model_type} model (from config)")
                    else:
                        # Fallback to hardcoded values for backward compatibility
                        if self.model_type == "flux_dev":
                            steps = 28  # Use 28 steps for Flux Dev model
                            print(f"Using 28 steps for Flux Dev model (fallback)")
                        elif self.model_type == "flex_schenele":
                            steps = 4  # Use 4 steps for Flex Schenele model
                            print(f"Using 4 steps for Flex Schenele model (fallback)")
                        elif self.model_type == "juggernaut_lightning":
                            steps = 5  # Use 5 steps for Juggernaut Lightning
                            print(f"Using 5 steps for Juggernaut Lightning Flux model (fallback)")
                        else:
                            steps = self.runware_config.get("steps", 20)  # Default from config
                            print(f"Using default {steps} steps for {self.model_type} model")

                # Get negative prompt from config
                negative_prompt = self.runware_config.get("negative_prompt",
                    "text, words, letters, writing, captions, labels, watermark, signature, logo, title, subtitle, timestamp")

                print(f"🚀 [RUNWARE] Generating image with model_id={self.model_id}, model_type={self.model_type}")
                print(f"📐 [RUNWARE] Final dimensions: {width}x{height}, Steps: {steps}")

                # Always use direct API calls
                result = self._generate_with_direct_api(prompt, width, height, steps, negative_prompt)
                if result:
                    print(f"✅ [RUNWARE] Image generation successful on attempt {attempt+1}")
                    # Return raw bytes; downstream pipeline will handle final sizing
                    return result
                else:
                    raise Exception("No image data returned from Runware.ai API")

            except Exception as e:
                error_message = str(e)
                print(f"❌ [RUNWARE] Error on attempt {attempt+1}/{max_retries}: {error_message}")

                # Print detailed error information for debugging
                if "timeout" in error_message.lower():
                    print(f"⏰ [RUNWARE] Timeout detected - API may be overloaded")
                elif "rate limit" in error_message.lower():
                    print(f"🚫 [RUNWARE] Rate limit detected - need to wait longer")
                elif "authentication" in error_message.lower():
                    print(f"🔑 [RUNWARE] Authentication error - check API key")
                elif "model" in error_message.lower():
                    print(f"🤖 [RUNWARE] Model error - check model availability")
                else:
                    print(f"🔍 [RUNWARE] Unknown error type: {type(e).__name__}")

                if attempt < max_retries - 1:
                    # Implement exponential backoff with jitter: wait longer with each retry
                    base_wait = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
                    jitter = time.time() % 1  # Add some randomness to avoid thundering herd
                    wait_time = base_wait + jitter
                    print(f"⏳ [RUNWARE] Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"💥 [RUNWARE] All {max_retries} attempts failed. Final error: {error_message}")
                    # Re-raise the exception to be consistent with other services
                    raise Exception(f"Error generating image with Runware.ai after {max_retries} attempts: {error_message}")



    def _generate_with_direct_api(self, prompt, width, height, steps, negative_prompt):
        """
        Generate an image using direct API calls to Runware.ai with retry logic.
        """
        import requests
        import base64
        import time
        import uuid

        max_retries = 3
        base_timeout = 60  # Start with 60 seconds timeout

        print(f"🚀 [RUNWARE API] Starting image generation with retry mechanism")
        print(f"📋 [RUNWARE API] Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print(f"📐 [RUNWARE API] Dimensions: {width}x{height}, Steps: {steps}")
        print(f"🎯 [RUNWARE API] Model: {self.model_id}")

        for attempt in range(max_retries):
            try:
                # Increase timeout with each retry
                current_timeout = base_timeout * (attempt + 1)  # 60s, 120s, 180s
                print(f"🔄 [RUNWARE API] Attempt {attempt + 1}/{max_retries} (timeout: {current_timeout}s)")
                if attempt > 0:
                    print(f"🔧 [RUNWARE API] Previous attempt failed, trying with longer timeout")

                result = self._make_single_api_request(prompt, width, height, steps, negative_prompt, current_timeout)
                if result:
                    print(f"✅ [RUNWARE API] Successfully generated image on attempt {attempt + 1}")
                    return result

            except requests.exceptions.Timeout:
                print(f"⏰ [RUNWARE API] Attempt {attempt + 1} timed out after {current_timeout}s")
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s
                    print(f"⏳ [RUNWARE API] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Runware API timed out after {max_retries} attempts")

            except Exception as e:
                print(f"💥 [RUNWARE API] Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 3 * (attempt + 1)  # 3s, 6s, 9s
                    print(f"⏳ [RUNWARE API] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"💀 [RUNWARE API] All retry attempts exhausted")
                    raise Exception(f"Runware API failed after {max_retries} attempts: {e}")

        print(f"💀 [RUNWARE API] Failed to generate image after all retry attempts")
        raise Exception("Failed to generate image after all retry attempts")

    def _make_single_api_request(self, prompt, width, height, steps, negative_prompt, timeout):
        """
        Make a single API request to Runware.ai with specified timeout.
        """
        import requests
        import base64
        import time
        import uuid

        try:
            # API endpoint - Updated to match official documentation
            api_endpoint = "https://api.runware.ai/v1"

            # Generate a random UUID for the task
            task_uuid = str(uuid.uuid4())

            # Prepare the request payload according to Runware.ai API format
            # Based on the official docs, the payload should be an array of task objects
            task_payload = {
                "taskType": "imageInference",
                "taskUUID": task_uuid,
                "positivePrompt": prompt,
                "model": self.model_id,
                "width": width,
                "height": height,
                "steps": steps,
                "CFGScale": self.runware_config.get("guidance_scale", 7.5),
                "numberResults": self.runware_config.get("num_images", 1),
                "outputType": "base64Data",
                "outputFormat": self.runware_config.get("output_format", "PNG")
            }

            # Only add negative prompt if it's provided and not empty
            if negative_prompt and negative_prompt.strip():
                task_payload["negativePrompt"] = negative_prompt

            payload = [task_payload]

            print(f"🌐 [RUNWARE API] Calling Runware.ai API with model: {self.model_id}")
            print(f"📦 [RUNWARE API] Task UUID: {task_uuid}")
            print(f"🔗 [RUNWARE API] Endpoint: {api_endpoint}")
            print(f"🔑 [RUNWARE API] Token: {self.api_token[:5]}...{self.api_token[-5:] if len(self.api_token) > 10 else ''}")
            print(f"⚙️ [RUNWARE API] Payload summary: {width}x{height}, {steps} steps, CFG: {self.runware_config.get('guidance_scale', 7.5)}")

            # Set up headers with API key
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_token}"
            }

            # Make the API request with dynamic timeout
            print(f"📡 [RUNWARE API] Sending request with {timeout}s timeout...")
            if timeout > 60:
                print(f"⚠️ [RUNWARE API] Using extended timeout due to previous failures")
            start_time = time.time()

            # Show progress indicator for longer timeouts
            if timeout > 60:
                print(f"⏳ [RUNWARE API] This may take a while... (up to {timeout}s)")
                print(f"💡 [RUNWARE API] If this gets stuck, the retry mechanism will handle it")

            # Add connection timeout and read timeout separately for better control
            response = requests.post(
                api_endpoint,
                headers=headers,
                json=payload,
                timeout=(30, timeout),  # (connection_timeout, read_timeout)
                stream=False  # Don't stream to get full response at once
            )

            request_time = time.time() - start_time
            print(f"⏱️ [RUNWARE API] Request completed in {request_time:.2f} seconds")

            # Check if the request was successful
            response.raise_for_status()
            print(f"✅ [RUNWARE API] HTTP Status: {response.status_code}")

            # Parse the response
            try:
                result = response.json()
                print(f"📄 [RUNWARE API] Response received, parsing...")
            except ValueError as e:
                # If we can't parse JSON, the response might be corrupted or binary
                print(f"❌ [RUNWARE API] Failed to parse JSON response: {e}")
                print(f"🔍 [RUNWARE API] Response content type: {response.headers.get('content-type', 'unknown')}")
                print(f"🔍 [RUNWARE API] Response length: {len(response.content)} bytes")
                if len(response.content) > 1000:
                    print(f"🔍 [RUNWARE API] Response preview: {response.content[:100]}...")
                else:
                    print(f"🔍 [RUNWARE API] Response content: {response.content}")
                raise Exception("Invalid JSON response from Runware API - possible API issue")

            # Debug: Print response structure (truncated for readability)
            if isinstance(result, dict):
                keys = list(result.keys())
                print(f"🔍 [RUNWARE API] Response keys: {keys}")
            else:
                print(f"🔍 [RUNWARE API] Response type: {type(result)}")

            # Parse response according to official Runware API documentation
            # Expected format: { "data": [ { "taskType": "imageInference", "taskUUID": "...", "imageURL": "..." } ] }
            # Or for base64: { "data": [ { "taskType": "imageInference", "taskUUID": "...", "imageBase64Data": "..." } ] }

            # Check for errors first
            if "errors" in result:
                error_info = result["errors"][0] if result["errors"] else {"message": "Unknown error"}
                error_msg = error_info.get("message", "Unknown error")
                print(f"🚨 [RUNWARE API] API Error: {error_msg}")
                raise Exception(f"Runware API Error: {error_msg}")

            if "data" in result and len(result["data"]) > 0:
                # Get the task data
                task_data = result["data"][0]
                print(f"📊 [RUNWARE API] Task data keys: {list(task_data.keys()) if isinstance(task_data, dict) else 'Not a dict'}")

                # Check if we have base64 image data first
                if "imageBase64Data" in task_data:
                    # Get the base64 encoded image
                    image_b64 = task_data["imageBase64Data"]

                    if image_b64:
                        print(f"🖼️ [RUNWARE API] Base64 image data received (length: {len(image_b64)})")
                        # Decode the base64 image
                        image_data = base64.b64decode(image_b64)
                        print(f"✅ [RUNWARE API] Image decoded successfully ({len(image_data)} bytes)")
                        # Return raw bytes; downstream pipeline will handle final sizing
                        return image_data
                    else:
                        print("❌ [RUNWARE API] Empty base64 image data in response")
                        raise Exception("Empty base64 image data received")

                # If no base64 data, check for image URL and download it
                elif "imageURL" in task_data:
                    image_url = task_data["imageURL"]
                    print(f"🔗 [RUNWARE API] Image URL received: {image_url}")

                    # Download the image from the URL
                    import requests
                    response = requests.get(image_url, timeout=60)
                    response.raise_for_status()

                    image_data = response.content
                    print(f"✅ [RUNWARE API] Image downloaded successfully ({len(image_data)} bytes)")
                    # Return raw bytes; downstream pipeline will handle final sizing
                    return image_data

                else:
                    print(f"❌ [RUNWARE API] No image data found in task data: {list(task_data.keys())}")
                    raise Exception(f"Missing image data in response. Available keys: {list(task_data.keys())}")
            else:
                print(f"❌ [RUNWARE API] Unexpected response format - no data array or empty data")
                if "error" in result:
                    error_msg = result.get("error", "Unknown error")
                    print(f"🚨 [RUNWARE API] API Error: {error_msg}")
                    raise Exception(f"Runware API Error: {error_msg}")
                else:
                    raise Exception(f"Unexpected response format: {result}")

        except requests.exceptions.Timeout:
            print(f"⏰ [RUNWARE API] Request timed out after {timeout} seconds")
            raise requests.exceptions.Timeout(f"Runware API request timed out after {timeout}s")
        except requests.exceptions.ConnectionError:
            print(f"🌐 [RUNWARE API] Connection error - check internet connection")
            raise Exception("Connection error to Runware API")
        except requests.exceptions.HTTPError as e:
            print(f"🚨 [RUNWARE API] HTTP Error: {e}")
            print(f"📄 [RUNWARE API] Response content: {response.text if 'response' in locals() else 'No response'}")
            raise Exception(f"HTTP Error: {e}")
        except Exception as e:
            print(f"💥 [RUNWARE API] Unexpected error: {type(e).__name__}: {e}")
            import traceback
            print(f"🔍 [RUNWARE API] Traceback: {traceback.format_exc()}")
            raise Exception(f"Runware API error: {e}")


class PollinationImageService:
    """
    Image service for Pollination AI with Flux model support.
    """

    def __init__(self, api_token=None):
        """
        Initialize Pollination AI service.

        Args:
            api_token: Not required for Pollination AI (free service)
        """
        self.base_url = "https://pollinations.ai/p/"
        print("✅ [POLLINATION] Service initialized")

    def generate_image(self, prompt, width=1024, height=1024, steps=4, negative_prompt="", seed=None, timeout=DEFAULT_TIMEOUT, max_retries=DEFAULT_MAX_RETRIES):
        """
        Generate an image using Pollination AI.

        Args:
            prompt (str): Text prompt for image generation
            width (int): Image width (will be adjusted to be divisible by 8)
            height (int): Image height (will be adjusted to be divisible by 8)
            steps (int): Number of inference steps (ignored for Pollination AI)
            negative_prompt (str): Negative prompt (ignored for Pollination AI)
            seed (int): Random seed for reproducible results
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retry attempts

        Returns:
            bytes: Generated image data or None if failed
        """
        import requests
        import urllib.parse
        import random
        import json
        import time

        # Ensure dimensions are divisible by 8 (required by Flux model)
        width = (width // 8) * 8
        height = (height // 8) * 8

        if seed is None:
            seed = random.randint(1, 1000000)

        print(f"🎨 [POLLINATION] Generating image...")
        print(f"📐 [POLLINATION] Dimensions: {width}x{height}")
        print(f"🎯 [POLLINATION] Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print(f"🎲 [POLLINATION] Seed: {seed}")

        for attempt in range(max_retries):
            try:
                print(f"🔄 [POLLINATION] Attempt {attempt + 1}/{max_retries}")

                # URL-encode prompt and add cache busting on retries
                encoded_prompt = urllib.parse.quote(prompt)
                cache_param = "&nocache=true" if attempt > 0 else ""
                api_url = f"{self.base_url}{encoded_prompt}?width={width}&height={height}&seed={seed}&model=flux&nologo=true&nofeed=true&private=true&enhance=true{cache_param}"

                # Make request with proper headers
                response = requests.get(
                    api_url,
                    timeout=timeout,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                )

                print(f"🔍 [POLLINATION] Response status: {response.status_code}")
                print(f"🔍 [POLLINATION] Content-Type: {response.headers.get('content-type', 'Unknown')}")
                print(f"🔍 [POLLINATION] Content-Length: {len(response.content)} bytes")

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    content_length = len(response.content)

                    # Check if we got a valid image
                    if content_length > 1000 and ('image' in content_type or content_type.startswith('image/')):
                        print(f"✅ [POLLINATION] Image generation successful on attempt {attempt + 1}")
                        # Return raw bytes; downstream pipeline will handle final sizing
                        return response.content
                    else:
                        print(f"❌ [POLLINATION] Invalid response: {content_length} bytes, type: {content_type}")
                        # Try to parse error message
                        try:
                            error_text = response.content.decode('utf-8')[:500]
                            print(f"🔍 [POLLINATION] Response content: {error_text}")

                            # Try to parse as JSON error
                            try:
                                error_json = json.loads(error_text)
                                if "error" in error_json:
                                    print(f"🔍 [POLLINATION] API Error: {error_json.get('error', 'Unknown error')}")
                            except json.JSONDecodeError:
                                pass
                        except:
                            pass
                else:
                    print(f"❌ [POLLINATION] HTTP error: {response.status_code}")
                    # Try to parse error response
                    try:
                        error_text = response.content.decode('utf-8')[:500]
                        print(f"🔍 [POLLINATION] Error response: {error_text}")
                    except:
                        pass

                # Wait before retry with exponential backoff
                if attempt < max_retries - 1:
                    wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                    print(f"⏳ [POLLINATION] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

            except Exception as e:
                print(f"❌ [POLLINATION] Error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = DEFAULT_RETRY_DELAY * (2 ** attempt)
                    print(f"⏳ [POLLINATION] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Pollination API error: {e}")

        return None


def get_image_service(service_name="replicate", api_token=None, model_type=None):
    """
    Factory function to get the appropriate image service.

    Args:
        service_name (str): The name of the service to use ('replicate', 'together', 'fal', 'runware', or 'pollination').
        api_token (str): Optional API token to use.
        model_type (str): Optional model type for services that support multiple models (like Runware.ai).

    Returns:
        An instance of the requested image service.
    """
    print(f"get_image_service called with service_name={service_name}, model_type={model_type}")

    if service_name.lower() == "together":
        print(f"Creating TogetherImageService")
        return TogetherImageService(api_token)
    elif service_name.lower() == "fal":
        print(f"Creating FalAIImageService")
        return FalAIImageService(api_token)
    elif service_name.lower() == "runware":
        # Always ensure we have a model_type for Runware.ai
        if model_type is None:
            model_type = "flux_dev"
            print(f"No model_type specified for Runware.ai, defaulting to {model_type}")
        print(f"Creating RunwareImageService with model_type={model_type}")
        return RunwareImageService(api_token, model_type)
    elif service_name.lower() == "pollination":
        print(f"Creating PollinationImageService")
        return PollinationImageService(api_token)
    else:  # Default to replicate
        print(f"Creating ReplicateImageService (default fallback)")
        return ReplicateImageService(api_token)
