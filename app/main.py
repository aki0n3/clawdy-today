import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import asyncio
import json
import random
import uuid

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"


# Load tasks from JSON on startup
def load_tasks():
    tasks_file = os.path.join(os.path.dirname(__file__), "tasks.json")
    with open(tasks_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tasks", [])

# Load stream events from JSON on startup
def load_stream_events():
    events_file = os.path.join(os.path.dirname(__file__), "stream_events.json")
    with open(events_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("events", [])

TASKS = load_tasks()
STREAM_EVENTS = load_stream_events()

if not ANTHROPIC_API_KEY:
    raise RuntimeError("Set ANTHROPIC_API_KEY env variable")

# ====== Mock responses ======
MOCK_RESPONSES = [
    "Отличный вопрос! Вот краткое объяснение:",
    "Это сложная тема, но я помогу тебе разобраться.",
    "Позволь мне дать развернутый ответ на это.",
    "Согласно лучшим практикам индустрии:",
    "Вот пошаговое решение:",
    "Это можно реализовать несколькими способами.",
    "Давай разберемся в деталях этого вопроса.",
    "Вот оптимальный подход к этой проблеме:",
    "Основываясь на опыте, рекомендую:",
    "Здесь важно обратить внимание на следующее:",
]

def generate_mock_response(task: str) -> dict:
    """Generates mock response in Anthropic API format"""
    response_text = random.choice(MOCK_RESPONSES)
    
    # Generate realistic token counts
    input_tokens = len(task.split()) + random.randint(10, 50)
    output_tokens = random.randint(50, 300)
    
    return {
        "model": "claude-3-opus-20240229",
        "content": [
            {
                "type": "text",
                "text": f"{response_text}\n\n{task[:100]}...\n\n[AKIONE]"
            }
        ],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    }

app = FastAPI(title="OpenClaw-like Agent")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ====== HTTP schema (client -> agent) ======

class TaskRequest(BaseModel):
    task: str
    system_prompt: str | None = "You are a senior software engineer"
    max_tokens: int = 1024

class TaskResponse(BaseModel):
    model: str
    output_text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


# ====== Main page ======

@app.get("/")
async def get_index():
    """Returns main HTML page"""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "index.html not found"}


# ====== Agent endpoint ======

@app.post("/task", response_model=TaskResponse)
async def run_task(req: TaskRequest):
    """
    Client -> Agent (HTTP)
    Agent -> Claude (HTTPS 443 + TLS)
    """

    # --- Build payload for Claude ---
    anthropic_payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": req.max_tokens,
        "system": req.system_prompt,
        "messages": [
            {
                "role": "user",
                "content": req.task
            }
        ]
    }

    # --- Try to get real response from Claude ---
    try:
        async with httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            timeout=60.0,
            http2=True,
            verify=True
        ) as client:

            response = await client.post(
                "/v1/messages",
                headers={
                    "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
                    "Content-Type": "application/json",
                    "Anthropic-Version": "2023-06-01"
                },
                json=anthropic_payload
            )

        if response.status_code != 200:
            # Если ошибка аутентификации или сети - используем mock
            if response.status_code in [401, 403, 500, 503] or USE_MOCK:
                data = generate_mock_response(req.task)
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
        else:
            data = response.json()

    except (httpx.RequestError, httpx.ConnectError, asyncio.TimeoutError):
        # On network error - use mock
        data = generate_mock_response(req.task)

    # --- Extract text ---
    text_blocks = [
        block["text"]
        for block in data.get("content", [])
        if block.get("type") == "text"
    ]

    return TaskResponse(
        model=data["model"],
        output_text="\n".join(text_blocks),
        input_tokens=data.get("usage", {}).get("input_tokens"),
        output_tokens=data.get("usage", {}).get("output_tokens")
    )


@app.post("/task/send", response_model=TaskResponse)
async def run_random_task():
    """
    Selects random task and system prompt from tasks.json
    and sends them to Claude
    """
    if not TASKS:
        raise HTTPException(
            status_code=500,
            detail="No tasks loaded from tasks.json"
        )
    
    # Choose random task
    random_task_data = random.choice(TASKS)
    
    # Create TaskRequest from selected task
    req = TaskRequest(
        task=random_task_data["task"],
        system_prompt=random_task_data.get("system_prompt", "You are a senior software engineer"),
        max_tokens=1024
    )
    
    # --- Build payload for Claude ---
    anthropic_payload = {
        "model": "claude-3-opus-20240229",
        "max_tokens": req.max_tokens,
        "system": req.system_prompt,
        "messages": [
            {
                "role": "user",
                "content": req.task
            }
        ]
    }

    # --- Try to get real response from Claude ---
    try:
        async with httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            timeout=60.0,
            http2=True,
            verify=True
        ) as client:

            response = await client.post(
                "/v1/messages",
                headers={
                    "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
                    "Content-Type": "application/json",
                    "Anthropic-Version": "2023-06-01"
                },
                json=anthropic_payload
            )

        if response.status_code != 200:
            # On auth or network error - use mock
            if response.status_code in [401, 403, 500, 503] or USE_MOCK:
                data = generate_mock_response(req.task)
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
        else:
            data = response.json()

    except (httpx.RequestError, httpx.ConnectError, asyncio.TimeoutError):
        # On network error - use mock
        data = generate_mock_response(req.task)

    # --- Extract text ---
    text_blocks = [
        block["text"]
        for block in data.get("content", [])
        if block.get("type") == "text"
    ]

    return TaskResponse(
        model=data["model"],
        output_text="\n".join(text_blocks),
        input_tokens=data.get("usage", {}).get("input_tokens"),
        output_tokens=data.get("usage", {}).get("output_tokens")
    )


async def event_generator():
    if not STREAM_EVENTS:
        yield "event: error\ndata: No events loaded\n\n"
        return
    
    # Choose random events sequence
    events_sequence = random.choice(STREAM_EVENTS)
    
    # Generate stream events with small delay
    for event in events_sequence:
        yield f"data: {event}\n\n"
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    yield "event: done\ndata: Sequence completed\n\n"

@app.get("/stream")
def stream():
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
