import asyncio
import shutil
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.video import Video
from app.api.v1.endpoints.videos import cleanup_existing_videos, UPLOAD_DIR


async def cleanup_all_videos() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Video.user_id).distinct())
        user_ids = [row[0] for row in result.all()]

        if not user_ids:
            print("No videos found. Nothing to clean.")
            return

        for user_id in user_ids:
            print(f"🧹 Cleaning videos for user_id={user_id}")
            await cleanup_existing_videos(user_id, session)

    # Remove any leftover generated assets under uploads/video_*
    if UPLOAD_DIR.exists():
        removed = 0
        for item in UPLOAD_DIR.iterdir():
            if item.name.startswith("video_"):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
                removed += 1
        print(f"🧾 Removed {removed} leftover generated files from {UPLOAD_DIR}")
    else:
        print(f"Warning: uploads directory {UPLOAD_DIR} does not exist.")

    print("✅ Cleanup completed.")


def main():
    asyncio.run(cleanup_all_videos())


if __name__ == "__main__":
    main()

