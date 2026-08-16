import os
import time
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
load_dotenv()

API_KEY = os.getenv("SEEDANCE_API_KEY")

if not API_KEY:
    raise ValueError(
        "API key not found. Please check your .env file."
    )

BASE_URL = "https://api.piapi.ai"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

def poll_task(task_id, interval=5, timeout=300):
    """
    Poll a Seedance task until it completes or fails.

    Args:
        task_id: Task ID returned when the video generation
                 request is created.
        interval: Seconds between status checks.
        timeout: Maximum total polling time in seconds.

    Returns:
        Generated video URL.

    Raises:
        RuntimeError: If the API request fails or generation fails.
        TimeoutError: If the task does not finish in time.
    """

    start_time = time.time()

    while time.time() - start_time < timeout:

        response = requests.get(
            f"{BASE_URL}/api/v1/task/{task_id}",
            headers=HEADERS,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to check task {task_id}. "
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        data = response.json()
        task_data = data.get("data", {})
        status = task_data.get("status")

        print(
            f"[Seedance] Task {task_id} status: {status}"
        )

        if status == "completed":
            output = task_data.get("output") or {}
            video_url = output.get("video")

            if not video_url:
                raise RuntimeError(
                    f"Task {task_id} completed, "
                    f"but no video URL was returned.\n"
                    f"Response: {data}"
                )

            print("[Seedance] Video generation completed.")

            return video_url

        if status == "failed":
            raise RuntimeError(
                f"Task {task_id} failed.\n"
                f"Response: {data}"
            )

        time.sleep(interval)

    raise TimeoutError(
        f"Task {task_id} did not complete within "
        f"{timeout} seconds."
    )

@tool
def generate_video(
    prompt: str,
    duration: int = 4,
    aspect_ratio: str = "16:9",
) -> str:
    """
    Generate a short video from a text description using Seedance.

    Use this tool ONLY when the user explicitly asks to create or generate
    a video from a text prompt.

    The prompt should describe the desired visual scene, subjects, actions,
    camera movement, environment, lighting, and visual style when relevant.

    This tool generates VIDEO ONLY. It does not generate, modify, or synchronize
    audio.

    The tool submits the generation request to Seedance, waits for the
    asynchronous generation task to complete, and returns the URL of the
    generated video.

    Do not call this tool for requests that only ask for an image, text,
    audio, explanation, or information about video generation.

    Args:
        prompt: A detailed description of the video to generate.
        duration: Video duration in seconds. Use 4 seconds unless the user
                  explicitly requests another supported duration.
        aspect_ratio: Output aspect ratio. Defaults to 16:9.
    """

    payload = {
        "model": "seedance",
        "task_type": "seedance-2-fast",
        "input": {
            "prompt": prompt,
            "mode": "text_to_video",
            "duration": duration,

            "aspect_ratio": aspect_ratio,
        },
    }

    print("[Seedance] Creating video task...")

    response = requests.post(
        f"{BASE_URL}/api/v1/task",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    task_data = data.get("data", {})
    task_id = task_data.get("task_id")

    if not task_id:
        raise RuntimeError(
            "API response did not contain a task_id.\n"
            f"Response: {data}"
        )

    print(
        f"[Seedance] Task created successfully: {task_id}"
    )

    video_url = poll_task(task_id)

    return video_url

@tool
def generate_video_using_reference(
    prompt: str,
    asset_id: str,
    duration: int = 4,
    aspect_ratio: str = "16:9",
) -> str:
    """
    Generate a video using an uploaded Seedance asset
    as a reference.

    Args:
        prompt:
            Instruction describing the desired video.

        asset_id:
            ID of the uploaded PiAPI asset.

        duration:
            Video duration in seconds.

        aspect_ratio:
            Output aspect ratio.

    Returns:
        URL of the generated video.
    """

    asset_uri = f"asset://{asset_id}"

    payload = {
        "model": "seedance",
        "task_type": "seedance-2-fast-less-restriction",
        "input": {
            "prompt": prompt,
            "mode": "omni_reference",

            "image_urls": [
                asset_uri
            ],

            "duration": duration,
            "aspect_ratio": aspect_ratio,
        },
    }

    print(
        "[Seedance] Creating reference-video task..."
    )

    response = requests.post(
        f"{BASE_URL}/api/v1/task",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    task_data = data.get("data", {})
    task_id = task_data.get("task_id")

    if not task_id:
        raise RuntimeError(
            "API response did not contain a task_id.\n"
            f"Response: {data}"
        )

    print(
        f"[Seedance] Reference task created: {task_id}"
    )

    video_url = poll_task(task_id)

    return video_url