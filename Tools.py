from dotenv import load_dotenv
load_dotenv()
import os
import time 
import requests
from langchain_core.tools import tool

api_key = os.getenv("MINIMAX_API_KEY")
BASE_URL = "https://minimax.io/v2/video_generation"
HEADERS ={
    "Authorization": f"Bearer {api_key}", 
    "Content-Type": "application/json"
}
thread_id = 0
@tool
def minimax_AI (prompt_text: str) -> str:
    """Submits a text prompt to the MiniMax H3 API and returns the unique Task ID."""
    print("->Submitting the request to the cloud...")

    payload ={
        "model": "MiniMax-H3",
        "content":[
            {
                "type": "text",
                "text": prompt_text
            }
        ],
        "duration":5,
        "resolution": "720p",
        "ratio":"16:9"
    }
    try:
        response = requests.post(BASE_URL, headers=HEADERS, json=payload)

        if response.status_code != 200:
            return f"Error occurred during connection to the server: {response.text}"
        resp_data = response.json()
        task_id = resp_data.get("id") or resp_data.get("task_id") or resp_data.get("data", {}).get("task_id")
        if not task_id:
            return f"---<<<No response from the server>>>---"
        print("task created Successfully.")
        query_payload = {"task_id": task_id}
        while True:
            status_response = requests.post(BASE_URL, headers=HEADERS, json=query_payload)
            if status_response.status_code != 200:
                time.sleep(10)
                continue
            
            data = status_response.json()
            status = data.get("status")

            if status == "SUCCESS":
                video_url = data.get("video_url")
                print("Video ready! Downloading file...")

                video_data = requests.get(video_url).content
                with open(f"/Users/moldybead/GenerativeChatbot/output_video_{thread_id}.mp4", "wb") as file:
                    file.write(video_data)

                return f"The video is generated successfully and saved in your computer."
            
            elif status == "FAIL":
                error_msg = data.get("error_msg", "Unkown remote API error")
                return f"Failed to generate video. Server error: {error_msg}"
            
            else:
                print("Loading...")
                time.sleep(15)

    except Exception as e:
        print(e)

thread_id += 2