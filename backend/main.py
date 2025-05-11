import os
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from bson import ObjectId
import time
from typing import Callable
import requests
import httpx

from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions
from history_chatbot import router as history_chatbot_router # Ensure you import the router
from rag_story import router as rag_story_router



# --- Constants ---
VIDEO_STATIC_API = "http://d59d-34-143-176-229.ngrok-free.app"
STORY_GEN_API = "http://94ad-34-168-181-25.ngrok-free.app"
VIDEO_FLUID_API = "http://f828-34-87-156-40.ngrok-free.app"  # or your actual API


# --- Load .env ---
load_dotenv()

# --- Clerk Setup ---
clerk_client = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

# --- FastAPI App ---
app = FastAPI()
app.include_router(history_chatbot_router, prefix="/history_chatbot") # Example prefix, adjust if needed
app.include_router(rag_story_router, prefix="/rag_story")



API_BASE_URL = "http://localhost:3000" # Adjust if your app runs on a different host/port

@app.on_event("startup")
async def startup_event():
    global http_client
    http_client = httpx.AsyncClient(base_url=API_BASE_URL)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CLIENT_URL", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- MongoDB Setup ---
MONGO_URL = os.environ.get("MONGO", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client["ASH_AI_Testing"]



# --- Pydantic Models ---
class ChatCreate(BaseModel):
    text: str
    type: str

class ChatUpdate(BaseModel):
    question: str | None = None
    answer: str

# --- Clerk Auth Middleware ---
def get_current_user(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    try:
        dummy_request = httpx.Request(
            method="GET",
            url=str(request.url),
            headers={"authorization": auth_header}
        )
        request_state = clerk_client.authenticate_request(
            dummy_request,
            AuthenticateRequestOptions(
                authorized_parties=[os.environ.get("CLIENT_URL", "http://localhost:5173")]
            )
        )
        if not request_state.is_signed_in:
            raise HTTPException(status_code=401, detail="Token is invalid")
        return request_state.payload.get("sub")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

# --- Video Generation Helper ---
async def generate_static_video(payload: dict, chat_id: str, user_id: str) -> str:
    try:
        # 1. Trigger video job
        print(payload)
        resp = requests.post(f"{VIDEO_STATIC_API}/make_video", json={"story": payload["story"]})
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        print(job_id)

        # 2. Poll until complete
        while True:
            status_resp = requests.get(f"{VIDEO_STATIC_API}/job_status/{job_id}")
            status_resp.raise_for_status()
            status = status_resp.json()["status"]
            print("Status:", status)
            if status == "done":
                break
            elif status == "error":
                raise RuntimeError("Video job failed")
            await asyncio.sleep(10)

        # 3. Download the video
        print("After While True")
        download_url = f"{VIDEO_STATIC_API}/get_video/{job_id}"
        print("Download URL:", download_url)
        video_resp = requests.get(download_url)
        print(video_resp)
        video_resp.raise_for_status()
        video_bytes = video_resp.content

        # 4. Save locally
        out_dir = Path("videos") / "Video Generation (Static)" / chat_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "output.mp4"
        path.write_bytes(video_bytes)

        # 5. Store in DB
        video_path = str(path)
        print("Video path:", video_path)
        html = (
            "<div style='display:flex; justify-content:center; margin: 20px 0;'>"
            f"<video width='720' height='405' controls style='border-radius:12px;'>"
            f"<source src='http://localhost:3000/{video_path}' type='video/mp4'>"
            "Your browser does not support the video tag."
            "</video></div>"
        )

        await db.chats.update_one(
            {"_id": ObjectId(chat_id), "userId": user_id},
            {"$push": {"history": {"role": "model", "parts": [{"text": html}]}}}
        )

        await db.videometadata.insert_one({
            "chatId": chat_id,
            "userId": user_id,
            "prompt": payload["prompt"],   # Save original user prompt here
            "videoPath": video_path,
            "createdAt": datetime.utcnow()
        })

        return html
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


async def generate_fluid_video(payload: dict, chat_id: str, user_id: str) -> str:
    try:
        # 1. Enqueue the job
        enqueue_resp = requests.post(
            f"{VIDEO_FLUID_API}/enqueue_story",
            json={"story": payload["story"], "num_frames": 16},  # You can change frames as needed
            timeout=10
        )
        enqueue_resp.raise_for_status()
        job_id = enqueue_resp.json()["job_id"]
        print("Fluid video job enqueued:", job_id)

        # 2. Poll for completion
        while True:
            poll_resp = requests.get(f"{VIDEO_FLUID_API}/result/{job_id}", stream=True, timeout=30)
            content_type = poll_resp.headers.get("Content-Type", "")

            if content_type.startswith("application/json"):
                status = poll_resp.json().get("status")
                if status == "processing":
                    print(f"[{job_id}] still processing…")
                    await asyncio.sleep(5)
                    continue
                elif status == "error":
                    raise RuntimeError(f"Job failed: {poll_resp.json().get('error')}")

            elif content_type == "video/mp4":
                # Save the video
                out_dir = Path("videos") / "Video Generation (Fluid)" / chat_id
                print("video saved")
                out_dir.mkdir(parents=True, exist_ok=True)
                path = out_dir / "output.mp4"

                with open(path, "wb") as f:
                    for chunk in poll_resp.iter_content(8192):
                        f.write(chunk)

                video_path = str(path)
                print(f"[{job_id}] video saved → {video_path}")

                # 3. Store in DB
                html = (
                    "<div style='display:flex; justify-content:center; margin: 20px 0;'>"
                    f"<video width='720' height='405' controls style='border-radius:12px;'>"
                    f"<source src='http://localhost:3000/{video_path}' type='video/mp4'>"
                    "Your browser does not support the video tag."
                    "</video></div>"
                )

                await db.chats.update_one(
                    {"_id": ObjectId(chat_id), "userId": user_id},
                    {"$push": {"history": {"role": "model", "parts": [{"text": html}]}}}
                )

                await db.videometadata.insert_one({
                    "chatId": chat_id,
                    "userId": user_id,
                    "prompt": payload["story"],
                    "videoPath": video_path,
                    "createdAt": datetime.utcnow()
                })

                return html

            else:
                raise RuntimeError(f"Unexpected response type: {content_type}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fluid video generation failed: {str(e)}")



# --- Function to call the History Chatbot API (Simplified) ---
async def chat_with_history_chatbot_api(prompt: str) -> str: # chat_history parameter is still here but not sent to API
    """
    Calls the stateful History Chatbot API endpoint.
    Only sends the question, as the API manages history internally.
    The 'chat_history' parameter from main.py is ignored when calling the API.
    """

    api_endpoint = "/history_chatbot/chat" # Adjust the endpoint based on how the router is mounted

    # Construct the payload, ONLY including the question
    payload = {
        "question": prompt,
    }

    try:
        response = await http_client.post(api_endpoint, json=payload)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as e:
        print(f"HTTP error calling history chatbot API: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"API error: {e.response.text}")
    except httpx.RequestError as e:
        print(f"Request error calling history chatbot API: {e}")
        raise HTTPException(status_code=500, detail=f"API request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred calling history chatbot API: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error calling API: {e}")

async def generate_rag_story(prompt: str) -> str: # chat_history parameter is still here but not sent to API
    """
    Calls the stateful History Chatbot API endpoint.
    Only sends the question, as the API manages history internally.
    The 'chat_history' parameter from main.py is ignored when calling the API.
    """

    api_endpoint = "/rag_story/chat" # Adjust the endpoint based on how the router is mounted

    # Construct the payload, ONLY including the question
    payload = {
        "query": prompt,
    }

    try:
        response = await http_client.post(api_endpoint, json=payload)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as e:
        print(f"HTTP error calling history chatbot API: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"API error: {e.response.text}")
    except httpx.RequestError as e:
        print(f"Request error calling history chatbot API: {e}")
        raise HTTPException(status_code=500, detail=f"API request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred calling history chatbot API: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error calling API: {e}")


import requests


async def generate_story(prompt: str) -> str:
    """
    Calls the Full Story Generation API using requests (sync).
    """


    payload = {
        "concept": prompt,
        "initial_story": "",
        "max_steps": 9
    }

    try:
        resp = requests.post(f"{STORY_GEN_API}/generate_story/", json=payload)
        resp.raise_for_status()
        result = resp.json()
        return result.get("story", "⚠️ No story returned.")

    except requests.exceptions.RequestException as e:
        print(f"Story generation API request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate story.")

    except Exception as e:
        print(f"Unexpected error in story generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during story generation.")


# --- Model Selector ---
# --- Modified get_model_for_type (No change needed here) ---
def get_model_for_type(chat_type: str) -> Callable:
    async def passthrough_model(question: str, history: list):
        yield "🚧 Model not yet implemented for this type."

    if chat_type == "History ChatBot":
        async def history_wrapper(prompt: str):
            answer = await chat_with_history_chatbot_api(prompt)
            yield answer
        return history_wrapper

    if chat_type == "RAG Story Generation":
        async def rag_wrapper(prompt: str):
            answer = await generate_rag_story(prompt)
            yield answer
        return rag_wrapper

    if chat_type == "Story Generation":
        async def story_wrapper(prompt: str):
            story = await generate_story(prompt)
            yield story
        return story_wrapper

    else:
        return passthrough_model


# --- Helpers ---
def obj_id_to_str(document: dict) -> dict:
    document["_id"] = str(document["_id"])
    return document

# --- Routes ---
@app.post("/api/chats", status_code=201)
async def create_chat(chat_data: ChatCreate, user_id: str = Depends(get_current_user)):
    new_chat = {
        "userId": user_id,
        "type": chat_data.type,
        "history": [{"role": "user", "parts": [{"text": chat_data.text}]}],
        "createdAt": datetime.utcnow(),
    }

    result = await db.chats.insert_one(new_chat)
    chat_id = str(result.inserted_id)

    if chat_data.type == "Video Generation (Static)":
        # 1. First, call the RAG Story model with user prompt
        model_fn = get_model_for_type("RAG Story Generation")
        generated_story = ""
        async for chunk in model_fn(chat_data.text):
            generated_story += chunk

        # 2. Then, pass the generated story to the video generator
        await generate_static_video(
            {
                "story": generated_story,    # Generated story used for making video
                "prompt": chat_data.text      # Original user input to RAG, saved in DB
            },
            chat_id,
            user_id
        )

    elif chat_data.type == "Video Generation (Fluid)":

        await generate_fluid_video(
            {
                "story": chat_data.text,
            },
            chat_id,
            user_id
        )

    else:
        model_fn = get_model_for_type(chat_data.type)
        accumulated_text = ""
        async for chunk in model_fn(chat_data.text):
            accumulated_text += chunk
        await db.chats.update_one(
            {"_id": result.inserted_id},
            {"$push": {"history": {"role": "model", "parts": [{"text": accumulated_text}]}}}
        )

    chat_entry = {
        "_id": chat_id,
        "title": chat_data.text[:40],
        "createdAt": datetime.utcnow(),
        "type": chat_data.type,
    }

    existing = await db.userchats.find_one({"userId": user_id})
    if not existing:
        await db.userchats.insert_one({"userId": user_id, "chats": [chat_entry]})
    else:
        await db.userchats.update_one({"userId": user_id}, {"$push": {"chats": chat_entry}})

    return chat_id


@app.get("/api/userchats")
async def get_user_chats(request: Request, user_id: str = Depends(get_current_user)):
    chat_type = request.query_params.get("type")
    userchats = await db.userchats.find_one({"userId": user_id})
    if not userchats:
        return []
    chats = userchats["chats"]
    if chat_type:
        chats = [c for c in chats if c.get("type") == chat_type]
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    return chats

@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str, user_id: str = Depends(get_current_user)):
    try:
        chat = await db.chats.find_one({"_id": ObjectId(chat_id), "userId": user_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid chat ID")
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return obj_id_to_str(chat)

import io
from pathlib import Path
from fastapi import HTTPException, Depends
from fastapi.responses import StreamingResponse
from bson import ObjectId

import os
from weasyprint import HTML

# 1️⃣ Paths
FONT_PATH = "PDF Generation/fonts/Jameel Noori Nastaleeq Regular.ttf"
LOGO_PATH = "PDF Generation/logo.png"  # Optional: Set None if no logo


def create_urdu_pdf_weasyprint(text_content: str,
                               watermark_text="Generated By ASH AI",
                               logo_path=None) -> bytes:
    abs_font_path = os.path.abspath(FONT_PATH)
    abs_logo_path = os.path.abspath(logo_path) if logo_path else None

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ur">
    <head>
      <meta charset="utf-8">
      <title>Urdu Document</title>
      <style>
        @font-face {{
          font-family: 'UrduFont';
          src: url('file://{abs_font_path}') format('truetype');
        }}

        /* BODY & TYPOGRAPHY */
        body {{
          background-color: #202229;
          color: white;
          font-family: 'UrduFont', sans-serif;
          direction: rtl;
          text-align: justify;
          margin: 0.3in 0.4in;
          font-size: 16pt;
          line-height: 1.6;
          letter-spacing: 0.5px;
        }}
        p {{
          text-indent: 2em;
          margin-bottom: 1.2em;
          font-size: 18pt;
        }}

        /* FIRST-PAGE HEADER */
        header.docHeader {{
          position: running(docHeader);
          margin-top: 15px;         /* push the logo down */
          /* border-bottom removed */
        }}
        .headerLogo {{
          height: 60px;
        }}

        @page:first {{
          background-color: #202229;
          @top-left {{
            content: element(docHeader);
          }}
          @bottom-left {{
            content: element(docFooter);
          }}
        }}

        /* FOOTER ON ALL PAGES */
        footer.docFooter {{
          position: running(docFooter);
        }}
        @page {{
          background-color: #202229;
          @bottom-left {{
            content: element(docFooter);
          }}
        }}
        .watermark {{
          display: flex;
          direction: ltr;
          align-items: center;
          gap: 0px;
          color: white;
          font-size: 10pt;
          font-weight: bold;
        }}
        .watermark img {{
          height: 28px;
          filter: brightness(0) invert(1);
        }}
      </style>
    </head>
    <body>

      <!-- Header (only on page 1) -->
      {f'''
      <header class="docHeader">
        <img src="file://{abs_logo_path}" class="headerLogo" alt="Logo">
      </header>
      ''' if abs_logo_path else ''}

      <!-- Main content -->
      <div class="content">
        <p>{text_content.replace('\n', '</p><p>')}</p>
      </div>

      <!-- Footer on every page -->
      <footer class="docFooter watermark">
        {f'<img src="file://{abs_logo_path}" alt="Logo">' if abs_logo_path else ''}
        {watermark_text}
      </footer>
    </body>
    </html>
    """
    return HTML(string=html_content).write_pdf()






# 3️⃣ FastAPI Endpoint
@app.get("/api/chats/{chat_id}/pdf")
async def download_story_pdf(chat_id: str, user_id: str = Depends(get_current_user)):
    # 1) Fetch and authorize
    chat = await db.chats.find_one({"_id": ObjectId(chat_id), "userId": user_id})
    if not chat:
        raise HTTPException(404, "Chat not found")

    # 2) Extract last model reply
    history = chat.get("history", [])
    story = ""
    for item in reversed(history):
        if item.get("role") == "model":
            story = "".join(p["text"] for p in item.get("parts", []))
            break
    if not story:
        raise HTTPException(400, "No story to generate PDF")

    # 3) Generate Urdu PDF with watermark at the end
    pdf_bytes = create_urdu_pdf_weasyprint(story, watermark_text="Generated By ASH AI", logo_path=LOGO_PATH)

    # 4) Stream back
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Story.pdf"},
    )



@app.post("/api/chats/{chat_id}/message")
async def generate_message(chat_id: str, payload: dict, user_id: str = Depends(get_current_user)):
    question = payload.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    chat = await db.chats.find_one({"_id": ObjectId(chat_id), "userId": user_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat_type = chat.get("type", "Story Generation")  # Default is Story Generation if not set

    model_fn = get_model_for_type(chat_type)
    accumulated_text = ""
    async for chunk in model_fn(question):
        accumulated_text += chunk

    new_items = [
        {"role": "user", "parts": [{"text": question}]},
        {"role": "model", "parts": [{"text": accumulated_text}]}
    ]
    await db.chats.update_one(
        {"_id": ObjectId(chat_id), "userId": user_id},
        {"$push": {"history": {"$each": new_items}}}
    )

    return {"answer": accumulated_text}




# --- Serve Static & Video Files ---
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/", StaticFiles(directory="../client/dist", html=True), name="static")

# --- Local Dev ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
