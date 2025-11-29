"""Service for generating image prompts from scripts - using desktop app's actual service."""

import re
import json
from typing import List, Dict, Optional, Sequence

from app.services.desktop_prompt_service import PromptService
from app.utils import load_config
from app import ai_client


def _split_script_into_scenes(
    script: str,
    max_scenes: Optional[int],
    target_words_per_scene: Optional[int] = None,
    min_words_per_scene: Optional[int] = None,
    max_sentences_per_scene: Optional[int] = None,
    manual_marker: Optional[str] = None,
) -> List[str]:
    """
    Split the raw script into scene-sized chunks.

    Prefer paragraph breaks first; if the script has no blank lines, fall back
    to sentence-based chunking so that long scripts still generate multiple scenes.
    """
    cleaned_script = script.strip()
    if not cleaned_script:
        return []

    target_words = max(int(target_words_per_scene or 90), 10)
    min_words = int(min_words_per_scene or max(20, target_words // 2))
    min_words = min(min_words, target_words)
    max_sentences = int(max_sentences_per_scene) if max_sentences_per_scene else None
    marker = (manual_marker or "").strip() or None

    def has_capacity(chunks: Sequence[str]) -> bool:
        return not max_scenes or len(chunks) < max_scenes

    def add_chunk(chunks: List[str], sentences: List[str]) -> None:
        if not sentences:
            return
        chunk_text = " ".join(sentences).strip()
        if chunk_text and has_capacity(chunks):
            chunks.append(chunk_text)

    def chunk_sentences(chunks: List[str], sentences: List[str]) -> None:
        current: List[str] = []
        current_words = 0
        current_sentence_count = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_words = len(sentence.split())
            if not current:
                current = [sentence]
                current_words = sentence_words
                current_sentence_count = 1
                continue

            should_break = False
            exceeds_word_target = current_words + sentence_words > target_words
            exceeds_sentence_limit = (
                max_sentences is not None and current_sentence_count >= max_sentences
            )

            if exceeds_sentence_limit:
                should_break = True
            elif exceeds_word_target and (
                current_words >= min_words or max_sentences == 1
            ):
                should_break = True

            if should_break and has_capacity(chunks):
                add_chunk(chunks, current)
                if not has_capacity(chunks):
                    return
                current = [sentence]
                current_words = sentence_words
                current_sentence_count = 1
            else:
                current.append(sentence)
                current_words += sentence_words
                current_sentence_count += 1

        if current and has_capacity(chunks):
            add_chunk(chunks, current)

    # Manual markers take precedence if provided.
    if marker and marker in cleaned_script:
        manual_segments = [
            segment.strip() for segment in cleaned_script.split(marker) if segment.strip()
        ]
        if manual_segments:
            return manual_segments[:max_scenes] if max_scenes else manual_segments

    # First try paragraph-based splitting
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", cleaned_script)
        if paragraph.strip()
    ]
    chunks: List[str] = []
    if len(paragraphs) > 1:
        for paragraph in paragraphs:
            if not has_capacity(chunks):
                break
            paragraph_sentences = [
                sentence.strip()
                for sentence in re.split(r"(?<=[.!?])\s+", paragraph)
                if sentence.strip()
            ]
            chunk_sentences(chunks, paragraph_sentences)

        if chunks:
            return chunks[:max_scenes] if max_scenes else chunks

    # Fallback: sentence-based chunking with target words per scene
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned_script)
        if sentence.strip()
    ]
    if not sentences:
        return [cleaned_script]

    chunk_sentences(chunks, sentences)

    if not chunks:
        return [cleaned_script]

    return chunks[:max_scenes] if max_scenes else chunks


def _generate_scenes_with_ai(
    script: str,
    ai_provider: str = "groq",
    ai_model: Optional[str] = None,
    max_scenes: Optional[int] = None,
    target_scene_count: Optional[int] = None,
) -> List[str]:
    """
    Use AI (Groq, OpenAI, or Gemini) to intelligently analyze the script and create logical scenes.
    
    Args:
        script: The full video script text
        ai_provider: AI provider to use (groq, openai, gemini)
        ai_model: Specific model to use (optional)
        max_scenes: Maximum number of scenes to create (optional, deprecated - use target_scene_count)
        target_scene_count: User-specified target number of scenes (takes precedence over max_scenes)
        
    Returns:
        List of scene texts
    """
    cleaned_script = script.strip()
    if not cleaned_script:
        return []
    
    # Use target_scene_count if provided, otherwise use max_scenes
    scene_count = target_scene_count if target_scene_count is not None else max_scenes
    
    # Build the prompt for AI to analyze and create scenes
    scene_prompt = f"""You are an expert video script analyzer. Your task is to read the following script and intelligently divide it into logical scenes.

A scene should represent:
- A complete thought, idea, or narrative segment
- A natural break in the story or content flow
- A distinct visual moment that would benefit from its own image
- A coherent unit of content (typically 50-150 words, but can vary based on content)

Guidelines:
- Each scene should be self-contained and meaningful
- Scenes should flow naturally from one to the next
- Don't split mid-sentence or mid-thought
- Consider narrative structure, topic changes, and visual transitions
- Aim for scenes that are roughly similar in length, but prioritize logical breaks over strict length matching

Script to analyze:
---
{cleaned_script}
---

Please analyze this script and divide it into logical scenes. Return your response as a JSON array of strings, where each string is one scene. 

Example format:
["Scene 1 text here...", "Scene 2 text here...", "Scene 3 text here..."]

IMPORTANT: Return ONLY the JSON array, no additional text, explanations, or markdown formatting. Just the array."""

    if scene_count and scene_count > 0:
        scene_prompt += f"\n\nIMPORTANT: You MUST create exactly {scene_count} scenes. Divide the script into exactly {scene_count} logical scenes. Adjust scene lengths to fit this number while maintaining logical breaks."

    # Check if the selected provider has an API key
    provider_lower = ai_provider.lower() if ai_provider else "groq"
    has_key = ai_client.has_api_key(provider_lower)
    
    if not has_key:
        print(f"⚠️ [SCENE GENERATION] {provider_lower.upper()} API key not configured")
        print(f"⚠️ [SCENE GENERATION] Falling back to rule-based scene splitting...")
        return _split_script_into_scenes(
            script,
            scene_count,
            target_words_per_scene=90,
            min_words_per_scene=20,
            max_sentences_per_scene=None,
            manual_marker=None,
        )
    
    try:
        print(f"🤖 [SCENE GENERATION] Using {provider_lower.upper()} to analyze script and create scenes...")
        if scene_count:
            print(f"🎯 [SCENE GENERATION] Target: {scene_count} scenes")
        
        # Use ai_client with the selected provider - it will check API keys internally
        completion = ai_client.chat_completion(
            messages=[{"role": "user", "content": scene_prompt}],
            model=ai_model,
            temperature=0.2,  # Lower temperature for more consistent scene splitting
            provider=provider_lower,
        )
        
        response_text = completion.choices[0].message.content.strip()
        print(f"✅ [SCENE GENERATION] AI response received: {len(response_text)} characters")
        
        # Try to extract JSON array from the response
        # Remove markdown code blocks if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        response_text = response_text.strip()
        
        # Try to parse as JSON
        try:
            scenes = json.loads(response_text)
            if isinstance(scenes, list) and all(isinstance(s, str) for s in scenes):
                # Filter out empty scenes
                scenes = [s.strip() for s in scenes if s.strip()]
                print(f"✅ [SCENE GENERATION] Successfully created {len(scenes)} scenes using AI")
                return scenes
            else:
                raise ValueError("Response is not a list of strings")
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract scenes from text
            print(f"⚠️ [SCENE GENERATION] JSON parsing failed, attempting text extraction...")
            # Look for array-like patterns
            match = re.search(r'\[(.*?)\]', response_text, re.DOTALL)
            if match:
                array_content = match.group(1)
                # Try to split by quotes
                scenes = re.findall(r'"([^"]+)"', array_content)
                if scenes:
                    scenes = [s.strip() for s in scenes if s.strip()]
                    print(f"✅ [SCENE GENERATION] Extracted {len(scenes)} scenes from text")
                    return scenes
            
            # Last resort: split by numbered items or newlines
            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            scenes = []
            for line in lines:
                # Remove numbering (1., 2., etc.)
                line = re.sub(r'^\d+[\.\)]\s*', '', line)
                # Remove quotes
                line = line.strip('"\'')
                if line and len(line) > 10:  # Minimum scene length
                    scenes.append(line)
            
            if scenes:
                print(f"✅ [SCENE GENERATION] Extracted {len(scenes)} scenes using fallback method")
                return scenes
            else:
                raise ValueError("Could not extract scenes from AI response")
                
    except Exception as e:
        print(f"❌ [SCENE GENERATION] Error using AI to create scenes: {e}")
        print(f"⚠️ [SCENE GENERATION] Falling back to rule-based scene splitting...")
        # Fallback to the original rule-based splitting
        return _split_script_into_scenes(
            script,
            scene_count,  # Use scene_count (which includes target_scene_count)
            target_words_per_scene=90,
            min_words_per_scene=20,
            max_sentences_per_scene=None,
            manual_marker=None,
        )


def generate_prompts_from_script(
    script: str,
    style: str = "cinematic",
    custom_instructions: Optional[str] = None,
    ai_provider: str = "groq",
    ai_model: Optional[str] = None,
    target_scene_count: Optional[int] = None,
) -> List[Dict]:
    """
    Generate image prompts for each scene in the script using desktop app's PromptService.
    
    First uses AI (Groq/Gemini) to intelligently analyze the script and create logical scenes,
    then generates image prompts for each scene.
    
    Args:
        script: The video script text
        style: Visual style to use
        custom_instructions: Custom context instructions
        ai_provider: AI provider (groq, openai, gemini) - used for both scene generation and prompt generation
        ai_model: Specific model to use
        target_scene_count: User-specified target number of scenes (overrides config)
        
    Returns:
        List of scenes with prompts
    """
    config = load_config()
    
    # Use target_scene_count if provided, otherwise use config
    if target_scene_count and target_scene_count > 0:
        max_scenes = target_scene_count
        print(f"🎯 [SCENE GENERATION] Using user-specified scene count: {max_scenes}")
    else:
        max_scenes_config = config.get("storyboard", {}).get("max_scenes")
        max_scenes = (
            max_scenes_config
            if isinstance(max_scenes_config, int) and max_scenes_config > 0
            else None
        )

    # Use AI to intelligently create scenes from the script
    print(f"🎬 [SCENE GENERATION] Analyzing script with {ai_provider} to create logical scenes...")
    if target_scene_count:
        print(f"🎯 [SCENE GENERATION] User requested {target_scene_count} scenes")
    paragraphs = _generate_scenes_with_ai(
        script,
        ai_provider=ai_provider,
        ai_model=ai_model,
        max_scenes=max_scenes,
        target_scene_count=target_scene_count,  # Pass target_scene_count explicitly
    )
    
    if not paragraphs:
        print(f"⚠️ [SCENE GENERATION] No scenes generated, returning empty list")
        return []
    
    print(f"✅ [SCENE GENERATION] Created {len(paragraphs)} scenes")

    prompt_service = PromptService(model=ai_model)
    scenes: List[Dict] = []
    previous_prompts = []

    for idx, paragraph in enumerate(paragraphs, start=1):
        try:
            image_prompt = prompt_service.generate_image_prompt(
                full_subtitles=script,
                previous_prompts=previous_prompts,
                group_text=paragraph,
                image_style=style,
                custom_instructions=custom_instructions,
            )
            scene = {
                "scene_number": idx,
                "text": paragraph,
                "image_prompt": image_prompt,
                "image_url": None,
                "audio_url": None,
                "duration": None,
            }
            scenes.append(scene)
            previous_prompts.append(image_prompt)
        except Exception as exc:
            print(f"Error generating prompt for scene {idx}: {exc}")
            scenes.append(
                {
                "scene_number": idx,
                "text": paragraph,
                "image_prompt": f"{style} style: {paragraph[:100]}...",
                "image_url": None,
                "audio_url": None,
                    "duration": None,
            }
            )
    
    return scenes
