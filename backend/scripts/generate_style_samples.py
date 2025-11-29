import json
import shutil
from pathlib import Path
from typing import List

from app.services.prompt_service import generate_prompts_from_script
from app.services.image_service import generate_images_for_scenes

SAMPLE_DIR = Path("style_samples")
SAMPLE_DIR.mkdir(exist_ok=True)

STYLE_METADATA_PATH = Path("style_metadata.json")

BASE_SCRIPT_TEMPLATE = (
    "Scene 1: A signature {style_name} scene featuring a key subject that highlights the core aesthetic.\n\n"
    "Scene 2: Another {style_name} moment in a different environment, emphasizing the mood and storytelling of the style."
)


def load_styles() -> List[dict]:
    with STYLE_METADATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    styles = []
    for display_name, info in data["styles"].items():
        normalized = info.get("normalized_name") or display_name.lower().replace(" ", "_")
        styles.append(
            {
                "display_name": display_name,
                "normalized_name": normalized,
            }
        )
    return styles


def copy_scene_images(style_slug: str, scenes):
    copied_files = []
    for scene in scenes:
        image_url = scene.get("image_url")
        if not image_url:
            continue
        if image_url.startswith("/"):
            image_url = image_url[1:]
        source_path = Path(image_url)
        if not source_path.exists():
            continue
        dest_path = SAMPLE_DIR / f"{style_slug}_scene{scene['scene_number']}.png"
        shutil.copy2(source_path, dest_path)
        copied_files.append(dest_path.as_posix())
    return copied_files


def main():
    styles = load_styles()
    summary = []

    for idx, style in enumerate(styles, 1):
        style_name = style["display_name"]
        style_slug = style["normalized_name"]
        print(f"[{idx}/{len(styles)}] Generating samples for {style_name} ({style_slug})...")

        script = BASE_SCRIPT_TEMPLATE.format(style_name=style_name)

        scenes = generate_prompts_from_script(
            script=script,
            style=style_slug,
            custom_instructions=None,
            ai_provider="groq",
            ai_model=None,
        )

        scenes = scenes[:2]
        for scene in scenes:
            scene["scene_number"] = scene.get("scene_number") or scenes.index(scene) + 1

        scenes_with_images = generate_images_for_scenes(
            scenes=scenes,
            image_service="pollination",
            image_model=None,
            resolution="720p",
            orientation="landscape",
            video_id=900000 + idx,
            progress_callback=None,
        )

        outputs = copy_scene_images(style_slug, scenes_with_images)
        summary.append(
            {
                "style": style_name,
                "normalized": style_slug,
                "generated": len(outputs),
                "files": outputs,
            }
        )

    with (SAMPLE_DIR / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Finished generating samples for {len(styles)} styles.")
    print(f"Outputs saved to {SAMPLE_DIR.resolve()}")


if __name__ == "__main__":
    main()

