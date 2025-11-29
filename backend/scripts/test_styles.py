import asyncio
import json
from pathlib import Path

from httpx import AsyncClient, ASGITransport
from app.main import app

import os
import random

STYLE_METADATA_PATH = Path(__file__).resolve().parents[1] / "style_metadata.json"

TEST_SCRIPT = (
    "Scene 1: A calm evening in a cozy room.\n\n"
    "Scene 2: A character studying with a cup of tea."
)


def load_styles():
    with STYLE_METADATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    styles = []
    for style_name, info in data["styles"].items():
        normalized = info.get("normalized_name") or style_name.lower().replace(" ", "_")
        styles.append({"name": style_name, "normalized": normalized})
    return styles


async def run_tests():
    styles = load_styles()
    random.shuffle(styles)

    results = []
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        for index, style in enumerate(styles, 1):
            payload = {
                "title": f"Style Test - {style['name']}",
                "description": "Automated style verification test",
                "script": TEST_SCRIPT,
                "style": style["normalized"],
                "resolution": "720p",
                "orientation": "landscape",
                "tts_provider": "edge",
                "image_service": "pollination",
                "transitionType": "none",
                "transitionDuration": 0.5,
                "subtitlesEnabled": False,
            }

            try:
                response = await client.post("/api/v1/videos/generate", json=payload)
                if response.status_code != 200:
                    results.append(
                        {
                            "style": style["name"],
                            "status": "failed",
                            "error": f"HTTP {response.status_code}: {response.text}",
                        }
                    )
                    continue

                data = response.json()
                video_id = data.get("id")
                results.append(
                    {"style": style["name"], "status": "queued", "video_id": video_id}
                )
                print(f"[{index}/{len(styles)}] Queued style: {style['name']} (video {video_id})")
            except Exception as exc:
                results.append(
                    {"style": style["name"], "status": "error", "error": str(exc)}
                )

    with open("style_test_results.json", "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)
    print("Results written to style_test_results.json")


if __name__ == "__main__":
    asyncio.run(run_tests())

