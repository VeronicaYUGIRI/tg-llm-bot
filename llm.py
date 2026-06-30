import os
import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def call_llm(messages, model, api_key):
    """
    messages: list of {"role": "user"/"assistant"/"system", "content": "..."}
    Returns dict: {"reply": str, "prompt_tokens": int, "completion_tokens": int, "cost": float}
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "usage": {"include": True},
    }

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    reply = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    return {
        "reply": reply,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "cost": usage.get("cost", 0.0),
    }
