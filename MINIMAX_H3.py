import os
import time
import requests
from langchain_core.tools import tool

from dotenv import load_dotenv
load_dotenv()


API_KEY = os.getenv("MINIMAX_API_KEY")

if not API_KEY:
    raise ValueError(
        "MINIMAX_API_KEY was not found. "
        "Check your .env file."
    )


# MiniMax Open Platform API
BASE_URL = "https://api.minimax.io/v2/video_generation"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def create_video_task(
    prompt: str,
    duration: int = 5,
    resolution: str = "768P",
    aspect_ratio: str = "16:9",
):
    """
    Create a MiniMax H3 video-generation task.

    Returns:
        task_id returned by MiniMax.
    """

    payload = {
        "model": "MiniMax-H3",
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
    }

    print("[MiniMax] Creating video-generation task...")

    response = requests.post(
        f"{BASE_URL}/v1/video_generation",
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    print("[MiniMax] Create-task response:")
    print(data)

    task_id = (
        data.get("task_id")
        or data.get("id")
        or data.get("data", {}).get("task_id")
    )

    if not task_id:
        raise RuntimeError(
            f"MiniMax did not return a task ID.\n"
            f"Response: {data}"
        )

    print(f"[MiniMax] Task created: {task_id}")

    return task_id


def poll_video_task(
    task_id: str,
    interval: int = 10,
    timeout: int = 600,
):
    """
    Poll MiniMax until the video-generation task finishes.

    Returns:
        file_id of the generated video.
    """

    start_time = time.time()

    print(f"[MiniMax] Polling task: {task_id}")

    while time.time() - start_time < timeout:

        response = requests.get(
            f"{BASE_URL}/v1/query/video_generation",
            headers=HEADERS,
            params={
                "task_id": task_id
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        print(f"[MiniMax] Status response: {data}")

        status = (
            data.get("status")
            or data.get("data", {}).get("status")
        )

        if status in ("Success", "SUCCESS", "success"):
            file_id = (
                data.get("file_id")
                or data.get("data", {}).get("file_id")
            )

            if not file_id:
                raise RuntimeError(
                    "MiniMax reported success, "
                    "but no file_id was returned.\n"
                    f"Response: {data}"
                )

            print(
                f"[MiniMax] Generation completed. "
                f"File ID: {file_id}"
            )

            return file_id

        if status in ("Fail", "FAIL", "failed", "Failed"):
            raise RuntimeError(
                f"MiniMax video generation failed.\n"
                f"Response: {data}"
            )

        print("[MiniMax] Still generating...")

        time.sleep(interval)

    raise TimeoutError(
        f"MiniMax task {task_id} did not finish "
        f"within {timeout} seconds."
    )


def retrieve_file(
    file_id: str,
    output_path: str,
):
    """
    Retrieve a generated MiniMax file and save it locally.

    Returns:
        Local path of the downloaded file.
    """

    print(f"[MiniMax] Retrieving file: {file_id}")

    response = requests.get(
        f"{BASE_URL}/v1/files/retrieve",
        headers=HEADERS,
        params={
            "file_id": file_id
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    print("[MiniMax] File response:")
    print(data)

    file_url = (
        data.get("file", {}).get("download_url")
        or data.get("download_url")
        or data.get("url")
    )

    if not file_url:
        raise RuntimeError(
            "MiniMax file retrieval succeeded, "
            "but no download URL was found.\n"
            f"Response: {data}"
        )

    print("[MiniMax] Downloading generated video...")

    video_response = requests.get(
        file_url,
        timeout=120,
    )

    video_response.raise_for_status()

    os.makedirs(
        os.path.dirname(output_path),
        exist_ok=True,
    )

    with open(output_path, "wb") as file:
        file.write(video_response.content)

    print(
        f"[MiniMax] Video saved to: {output_path}"
    )

    return output_path


@tool
def minimax_video_generation(prompt: str) -> str:
    """
    Generate a video using MiniMax H3.

    Use this tool when the user explicitly asks to generate
    a video.

    MiniMax H3 can generate video with native stereo audio.
    The prompt should describe the scene, subjects, actions,
    camera movement, environment, lighting, and desired style.

    This tool submits the generation request, waits for the
    asynchronous task to finish, retrieves the generated file,
    and saves the resulting MP4 locally.

    Args:
        prompt:
            Detailed natural-language description of the desired
            video.

    Returns:
        Local filesystem path to the generated MP4 file.
    """

    output_path = os.path.join(
        os.getcwd(),
        "output",
        "minimax_generated.mp4",
    )

    task_id = create_video_task(
        prompt=prompt,
        duration=5,
        resolution="768P",
        aspect_ratio="16:9",
    )

    file_id = poll_video_task(task_id)

    video_path = retrieve_file(
        file_id=file_id,
        output_path=output_path,
    )

    return video_path


if __name__ == "__main__":

    prompt = """
    A cinematic continuous aerial shot approaching a gigantic abandoned
    astronomical observatory built into the edge of a black volcanic island
    at blue hour, surrounded by a calm dark ocean.

    The camera slowly flies forward through a large broken glass dome
    without cutting. Inside the observatory is an enormous mechanical
    celestial model suspended above an ancient circular stone floor.

    Hundreds of intricate brass planets, moons, rings, and constellation
    mechanisms rotate slowly around a small glowing artificial sun.

    Thin beams of cool moonlight pass through the broken glass roof.
    Faint ocean mist drifts through the structure while small particles
    of dust float through the light.

    The camera movement remains smooth and continuous throughout the shot.
    Maintain consistent geometry, scale, lighting, materials, and
    environment from beginning to end.

    Photorealistic weathered black stone, aged brass, realistic glass,
    physically plausible reflections, subtle atmospheric fog, detailed
    mechanical components, cinematic depth of field, realistic exposure,
    mysterious quiet atmosphere.

    Generate natural synchronized environmental audio matching the scene,
    including distant ocean ambience, wind, subtle mechanical movement,
    metallic resonance, and atmospheric room tone.

    No people, no faces, no text, no logos, no subtitles,
    no sudden camera movement, no rapid cuts, no scene transitions,
    no object transformations, no duplicated objects,
    no surreal deformation.
    """

    try:

        result = minimax_video_generation.invoke({
            "prompt": prompt
        })

        print("\n========================================")
        print("MINIMAX GENERATION SUCCESSFUL")
        print("========================================")
        print(f"Output: {result}")
        print("========================================")

    except Exception as e:

        print("\n========================================")
        print("MINIMAX GENERATION FAILED")
        print("========================================")
        print(f"{type(e).__name__}: {e}")
        print("========================================")

        raise