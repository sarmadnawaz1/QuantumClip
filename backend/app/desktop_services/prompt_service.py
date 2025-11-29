"""
Service to generate image prompts using OpenAI or Groq.
Based on the RapidClips implementation.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ai_client

class PromptService:
    """
    Service to generate image prompts using the current AI provider (OpenAI, Groq, or OpenRouter).
    """

    def __init__(self, model=None):
        """
        Initialize the prompt service.

        Args:
            model (str, optional): Specific model to use. If None, uses the current provider's default.
        """
        self.model = model

    def generate_image_prompt(
        self, full_subtitles: str, previous_prompts: list, group_text: str, image_style: str = "cinematic", custom_instructions: str = None
    ) -> str:
        """
        Generate a prompt for image generation based on subtitle context,
        ensuring consistency of style across prompts, historical coherence if applicable,
        and avoiding repetitive ideas.

        Args:
            full_subtitles (str): The entire subtitle text for context.
            previous_prompts (list): List of previously generated image prompts.
            group_text (str): The specific subtitle segment to create an image prompt for.
            image_style (str): The desired visual style for the image (e.g., "cinematic", "anime").
            custom_instructions (str, optional): User-provided custom instructions for image generation context.

        Returns:
            str: The generated image prompt in English.
        """

        # Log context size for debugging
        print(f"📏 [PROMPT] Context size: {len(full_subtitles)} characters")

        # Get the detailed style description
        style_description = self._get_style_description(image_style)
        print(f"🎨 [PROMPT] Selected image style: '{image_style}'")
        print(f"🎨 [PROMPT] Using style description: {style_description[:100]}...")
        print(f"🎨 [PROMPT] Style enforcement: ENABLED - All prompts will include '{image_style}' style")

        # Build the base prompt
        prompt = (
            f"You are an expert visual storytelling prompt generator for text-to-image models. "
            "Your primary goal is to create highly relevant, scene-specific image prompts that perfectly capture what is being spoken about in the subtitle. "
            "Analyze the subtitle content deeply and generate prompts that visually represent the exact concepts, emotions, actions, or subjects being discussed. "
            "Create vivid, detailed visual descriptions that directly relate to the spoken content. "
            f"\n\n🎨 CRITICAL STYLE REQUIREMENT: ALL IMAGES MUST BE CREATED IN THIS EXACT STYLE: {style_description}\n"
            f"🎨 STYLE ENFORCEMENT: Every single prompt you generate MUST include and emphasize the '{image_style}' style characteristics.\n"
            f"🎨 STYLE CONSISTENCY: Apply the style description throughout the entire prompt, not just as an afterthought.\n"
            f"🎨 MANDATORY STYLE APPLICATION: The selected style '{image_style}' must be the dominant visual characteristic of every image.\n\n"
        )

        # Add custom instructions if provided with validation
        if custom_instructions and custom_instructions.strip():
            # Validate custom instructions length
            custom_instructions = custom_instructions.strip()
            if len(custom_instructions) > 2000:
                print(f"⚠️ [PROMPT] Custom instructions too long ({len(custom_instructions)} chars), truncating to 2000 chars")
                custom_instructions = custom_instructions[:2000] + "..."

            print(f"📝 [PROMPT] Applying custom instructions ({len(custom_instructions)} chars): {custom_instructions[:100]}...")
            prompt += (
                f"🎯 CUSTOM CONTEXT INSTRUCTIONS: The user has provided specific guidance for image generation. "
                f"These instructions must be carefully integrated into every image prompt to ensure consistency and accuracy:\n"
                f"{custom_instructions}\n\n"
                f"🎯 CUSTOM CONTEXT INTEGRATION: Apply these custom instructions throughout the image generation process. "
                f"Ensure that character descriptions, settings, time periods, and other contextual elements from the custom instructions "
                f"are consistently reflected in all generated images while maintaining the specified artistic style.\n\n"
            )

        prompt += (
            "Focus on the core subject matter, key visual elements, mood, and atmosphere that best represent what the speaker is talking about. "
            "If the content mentions specific objects, people, places, concepts, or emotions, make sure these are prominently featured in the visual description. "
            "Avoid any text, lettering, or written elements in the image. "
            "Prioritize scene relevance and visual storytelling while maintaining the specified artistic style.\n\n"
            f"1. Subtitle context for understanding the narrative:\n{full_subtitles}\n\n"
        )

        if previous_prompts:
            # Limit previous prompts to prevent token overflow
            max_previous_prompts = 3
            limited_prompts = previous_prompts[-max_previous_prompts:] if len(previous_prompts) > max_previous_prompts else previous_prompts

            prompt += (
                "2. Previously generated prompts (maintain visual consistency and avoid repetition while ensuring each new prompt is uniquely relevant to its specific subtitle):\n"
                f"{limited_prompts}\n\n"
            )

        prompt += (
            f"3. Current subtitle segment to create a highly relevant visual for:\n{group_text}\n\n"
            f"INSTRUCTIONS:\n"
            f"- Analyze what is being spoken about in this specific subtitle segment\n"
            f"- Identify the key subjects, concepts, emotions, or actions mentioned\n"
            f"- Create a detailed visual description that directly represents these elements in the specified artistic style\n"
        )

        # Add custom instructions guidance if provided
        if custom_instructions and custom_instructions.strip():
            prompt += (
                f"- 🎯 CRITICAL: Apply the custom context instructions provided above to ensure consistency\n"
                f"- 🎯 CONTEXT ADHERENCE: Ensure all character descriptions, settings, and contextual elements match the custom instructions\n"
                f"- 🎯 CONSISTENCY: Maintain the same character appearances, time period, and environmental details as specified\n"
            )

        prompt += (
            f"- 🎨 CRITICAL: Start your prompt with the style '{image_style}' and weave style elements throughout\n"
            f"- 🎨 MANDATORY: Apply the style description throughout: {style_description}\n"
            f"- 🎨 STYLE DOMINANCE: The '{image_style}' style must be the most prominent visual characteristic\n"
            f"- 🎨 STYLE INTEGRATION: Every visual element must reflect the '{image_style}' aesthetic\n"
            f"- Make the image prompt highly specific to what the speaker is discussing\n"
            f"- Include relevant environmental details, lighting, mood, and atmosphere that enhance the spoken content\n"
            f"- Ensure the visual perfectly complements and illustrates the subtitle content\n"
            f"- Do not include any text, words, or lettering in the image\n"
            f"- Focus on visual storytelling that makes the subtitle content come alive\n\n"
            f"Generate ONE highly relevant, detailed image prompt that perfectly visualizes what is being spoken about in the subtitle segment. "
            f"🎨 CRITICAL: Begin your prompt with '{image_style} style' and ensure every visual element reflects this style. "
        )

        # Add final custom instructions reminder if provided
        if custom_instructions and custom_instructions.strip():
            prompt += (
                f"🎯 CONTEXT REMINDER: Incorporate the custom context instructions to ensure character consistency, appropriate settings, and accurate contextual details. "
            )

        prompt += (
            f"Make it specific, vivid, and directly connected to the spoken content while maintaining the artistic style dominance. "
            f"IMPORTANT: Respond with ONLY the image prompt as a single paragraph. Do not include explanations, titles, or additional text. "
            f"Just provide the concise, detailed image prompt that starts with the style and incorporates all style elements:"
        )

        # Use the ai_client with specified model or current provider's model
        try:
            print(f"🤖 [PROMPT] Generating image prompt using AI...")
            if self.model:
                print(f"🎯 [PROMPT] Using specified model: {self.model}")
                completion = ai_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model,
                    temperature=0.7,
                )
            else:
                print(f"🎯 [PROMPT] Using default model for current provider")
                completion = ai_client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
            print(f"✅ [PROMPT] Successfully generated image prompt")

            # Verify style is included in the generated prompt
            generated_prompt = completion.choices[0].message.content.strip()
            if image_style.lower() in generated_prompt.lower():
                print(f"✅ [PROMPT] Style '{image_style}' confirmed in generated prompt")
            else:
                print(f"⚠️ [PROMPT] WARNING: Style '{image_style}' not found in generated prompt!")
                print(f"🔍 [PROMPT] Generated prompt preview: {generated_prompt[:100]}...")

        except Exception as e:
            print(f"❌ [PROMPT] Error generating prompt: {e}")
            # Fallback to a style-enhanced prompt
            style_description = self._get_style_description(image_style)
            return f"{image_style} style image with {style_description[:50]}... depicting: {group_text[:100]}..."

        # Return the response directly
        final_prompt = completion.choices[0].message.content.strip()
        print(f"🎨 [PROMPT] Final prompt generated with style '{image_style}': {final_prompt[:100]}...")
        return final_prompt

    def _get_style_description(self, image_style: str) -> str:
        """
        Get a detailed description of the selected image style.
        First checks for custom styles, then falls back to built-in styles.

        Args:
            image_style (str): The image style name

        Returns:
            str: A detailed description of the style
        """
        # First check if this is a custom style
        try:
            from utils import get_custom_styles
            custom_styles = get_custom_styles()

            if image_style in custom_styles:
                custom_description = custom_styles[image_style]['description']
                print(f"🎨 [PROMPT] Using custom style description for '{image_style}': {custom_description[:100]}...")
                return custom_description

        except Exception as e:
            print(f"⚠️ [PROMPT] Error checking custom styles: {e}")

        # Fall back to built-in styles
        # Convert to lowercase and normalize for case-insensitive matching
        style_lower = image_style.lower()
        # Remove spaces and hyphens for more flexible matching
        style_normalized = style_lower.replace(" ", "").replace("-", "")

        # Enhanced dictionary of style descriptions - pure visual styles without gender references
        style_descriptions = {
            "photorealistic": "Hyperrealistic professional photography with perfect lighting, ultra-detailed textures, photographic quality depth of field, natural color grading, cinematic composition, authentic environmental details, and lifelike material properties. Professional studio quality with masterful technical execution.",

            "cinematic": "Professional cinematic lighting with dramatic atmosphere, masterful composition, high-quality film production values, movie still quality framing, dynamic camera angles, film-like color grading, and epic visual storytelling. Blockbuster movie aesthetic with perfect cinematography.",

            "anime": "Vibrant Japanese anime style with clean linework, studio Ghibli inspired aesthetics, detailed character design, expressive features, dynamic poses, high quality anime aesthetic, cel-shaded coloring, atmospheric backgrounds, and emotional visual storytelling. Premium anime production quality.",

            # Trendy faceless content styles
            "minimalistinfographic": "Clean minimalist infographic design with simple geometric shapes, modern typography, data visualization elements, professional business aesthetic, white background, subtle shadows, clear visual hierarchy, and contemporary design principles. Corporate presentation excellence.",

            "corporatepresentation": "Professional corporate presentation style with clean layouts, business-appropriate color schemes, modern typography, subtle gradients, professional charts and graphs, executive boardroom aesthetic, and polished business design. Corporate excellence.",

            "techtutorial": "Modern tech tutorial aesthetic with clean interface elements, software screenshots, digital workspace design, modern UI components, tech-focused color palette, professional documentation style, and contemporary digital design. Tech education mastery.",

            "educationaldiagram": "Educational diagram style with clear visual explanations, instructional design elements, academic presentation aesthetic, clean infographic layout, learning-focused design, professional educational materials, and pedagogical visual communication. Educational design excellence.",

            "datavisualization": "Data visualization style with modern charts, graphs, statistical displays, analytical dashboard aesthetic, clean data presentation, professional metrics design, business intelligence visuals, and contemporary data design. Data visualization mastery.",

            "abstractgeometric": "Abstract geometric design with modern shapes, minimalist patterns, contemporary art aesthetic, clean geometric forms, sophisticated color palettes, artistic composition, and modern abstract artistry. Geometric design excellence.",

            "gradientbackground": "Gradient background style with smooth color transitions, modern gradient design, contemporary color blending, atmospheric gradients, professional background aesthetics, and sophisticated color harmony. Gradient design mastery.",

            "neongaming": "Neon gaming aesthetic with bright RGB lighting, gaming setup atmosphere, cyberpunk gaming vibes, LED lighting effects, modern gaming environment, high-tech gaming aesthetic, and contemporary esports design. Gaming excellence.",

            "productivityaesthetic": "Productivity aesthetic with clean workspace design, organized environment, minimalist productivity setup, modern office aesthetic, efficient workspace layout, professional productivity tools, and contemporary work environment. Productivity design mastery.",

            "studymotivation": "Study motivation aesthetic with inspiring learning environment, academic workspace design, motivational study setup, clean educational atmosphere, focused learning environment, and inspirational academic design. Study motivation excellence.",

            "ambientworkspace": "Ambient workspace design with cozy work environment, atmospheric lighting, comfortable productivity space, modern home office aesthetic, relaxing work atmosphere, and contemporary workspace design. Ambient workspace mastery.",

            "cozyreading": "Cozy reading aesthetic with warm lighting, comfortable reading nook, literary atmosphere, bookish environment, relaxing reading space, intimate library setting, and peaceful reading ambiance. Cozy reading excellence.",

            "naturedocumentary": "Nature documentary style with wildlife photography aesthetic, natural environment beauty, documentary cinematography, outdoor exploration visuals, environmental storytelling, and authentic nature presentation. Nature documentary mastery.",

            "spaceexploration": "Space exploration aesthetic with cosmic visuals, astronomical photography, space mission design, futuristic space technology, celestial beauty, scientific space imagery, and contemporary space exploration design. Space exploration excellence.",

            "oceandeep": "Ocean deep aesthetic with underwater photography, marine environment beauty, aquatic exploration visuals, deep sea atmosphere, oceanic color palette, and underwater documentary style. Ocean exploration mastery.",

            "mountainlandscape": "Mountain landscape photography with dramatic natural vistas, outdoor adventure aesthetic, alpine environment beauty, landscape photography excellence, natural lighting, and majestic mountain scenery. Mountain landscape mastery.",

            "cityskyline": "City skyline aesthetic with urban photography, metropolitan atmosphere, modern architecture, cityscape beauty, urban exploration visuals, and contemporary city design. Urban skyline excellence.",

            "sunsetvibes": "Sunset vibes aesthetic with golden hour lighting, warm atmospheric colors, peaceful evening atmosphere, romantic sunset beauty, natural lighting excellence, and serene sunset ambiance. Sunset photography mastery.",

            "rainaesthetic": "Rain aesthetic with atmospheric weather photography, moody rain atmosphere, cozy rainy day vibes, peaceful precipitation beauty, natural weather patterns, and contemplative rain ambiance. Rain photography excellence.",

            "coffeeshop": "Coffee shop aesthetic with cozy café atmosphere, warm lighting, artisanal coffee culture, comfortable café environment, modern coffee shop design, and inviting café ambiance. Coffee shop excellence.",

            "librarystudy": "Library study aesthetic with academic atmosphere, scholarly environment, quiet study space, intellectual setting, educational ambiance, and peaceful learning environment. Library study mastery.",

            "meditationspace": "Meditation space aesthetic with peaceful atmosphere, zen environment, mindful design, calming colors, spiritual ambiance, and tranquil meditation setting. Meditation space excellence.",

            "zengarden": "Zen garden aesthetic with minimalist Japanese design, peaceful garden atmosphere, meditative landscape, natural harmony, serene outdoor space, and contemplative garden beauty. Zen garden mastery.",

            "minimalistroom": "Minimalist room design with clean interior aesthetic, modern minimalism, uncluttered space, contemporary home design, sophisticated simplicity, and elegant minimalist living. Minimalist interior excellence.",

            "comicbook": "Professional comic book illustration with dynamic poses, bold black outlines, vibrant saturated colors, Marvel/DC style composition, dramatic action scenes, heroic proportions, graphic novel quality artwork, and powerful visual narrative. Striking comic book artistry.",

            "pixarart": "3D animated Pixar style with exaggerated proportions, smooth polished textures, vibrant cheerful colors, expressive character animation, detailed environmental modeling, warm emotional lighting, and charming visual storytelling. Technical excellence in 3D animation.",

            "digitalart": "Professional digital illustration with vibrant colors, detailed textures, advanced digital painting techniques, concept art quality, intricate details, atmospheric effects, modern artistic sensibilities, and gallery-worthy technical mastery. Contemporary digital artistry.",

            "oilpainting": "Traditional oil painting style with rich impasto textures, visible expressive brushstrokes, classical composition techniques, fine art museum quality, warm color harmonies, masterful light studies, and timeless artistic beauty. Classical painting mastery.",

            "watercolor": "Delicate watercolor painting with gentle color blending, translucent layered washes, artistic color bleeds, traditional watercolor technique, soft edges, luminous transparency effects, ethereal beauty, and spontaneous artistic expression. Watercolor artistry.",

            "pixelart": "Detailed pixel art with carefully limited color palette, crisp clean edges, nostalgic retro gaming aesthetic, precise pixel placement, classic 8-bit or 16-bit style charm, and celebration of classic video game graphics artistry. Retro pixel perfection.",

            "darkaesthetic": "Moody atmospheric scenes with dark sophisticated color palette, dramatic chiaroscuro lighting, gothic architectural elements, mysterious ambiance, deep shadows, noir-inspired composition, and hauntingly beautiful emotional depth. Dark artistic atmosphere.",

            "neoncyberpunk": "Futuristic cyberpunk cityscape with vibrant neon lighting, high-tech architecture, cyberpunk aesthetic elements, rain-slicked streets, holographic displays, contrasting bright colors against dark urban environments, and dystopian future atmosphere. Cyberpunk visual excellence.",

            "minimalist": "Clean minimalist design with simple geometric lines, carefully limited color palette, strategic negative space, elegant sophisticated simplicity, modern design principles, refined aesthetic restraint, and powerful purposeful imagery. Minimalist perfection.",

            "filmnoir": "Classic film noir with high contrast black and white photography, dramatic angular shadows, moody atmospheric lighting, cinematic composition, 1940s aesthetic elements, vintage Hollywood glamour, and timeless cinematic drama. Film noir mastery.",

            "horrorgothic": "Gothic horror atmosphere with dark medieval architecture, dramatic shadows, candlelit ambiance, ornate stone details, mysterious fog, ancient textures, haunting gothic elements, classic horror aesthetic, eerie architectural beauty, and spine-chilling atmospheric depth. Gothic horror mastery.",

            "horrorrealistic": "Realistic horror style with photorealistic horror elements, unsettling atmosphere, dramatic lighting, psychological tension, modern horror cinematography, detailed textures, eerie realism, cinematic horror quality, disturbing beauty, and masterful horror artistry. Realistic horror excellence.",

            "horrorvintage": "Vintage horror aesthetic with classic 1950s-70s horror movie style, grain texture, muted color palette, retro horror poster design, vintage film quality, nostalgic horror atmosphere, classic cinema horror, timeless horror beauty, and authentic vintage horror charm. Vintage horror perfection.",

            "hyperrealistic": "Extreme photorealism with incredible fine detail beyond normal photography, perfect technical lighting, flawless surface textures, microscopic accuracy, surreal clarity, and reality-challenging imagery. Hyperrealistic perfection.",

            "flatdesign": "Modern flat design with clean vector style graphics, solid colors without gradients, simplified geometric shapes, contemporary design principles, minimalist visual hierarchy, and clean digital media imagery. Flat design excellence.",

            "3dcartoon": "3D animated cartoon style with exaggerated proportions, smooth polished textures, vibrant playful colors, expressive animation-ready design, family-friendly aesthetic appeal, and charming 3D artwork. Cartoon animation mastery.",

            "pasteldreamscape": "Soft pastel color palette with dreamy ethereal atmosphere, gentle diffused lighting, surreal fantastical elements, fantasy-like magical quality, otherworldly beauty, and beautiful dream imagery. Pastel dream artistry.",

            "fantasyvibrant": "Vibrant fantasy art with magical elements, enchanted environments, mystical creatures, epic fantasy landscapes, rich saturated colors, dramatic fantasy lighting, and otherworldly beauty. Fantasy art mastery.",

            "aigenerated": "AI-generated art style with digital perfection, algorithmic precision, contemporary AI aesthetic, futuristic design elements, computational artistry, and modern artificial intelligence creativity. AI art excellence.",

            "synthwave": "Synthwave aesthetic with retro-futuristic style, neon pink and cyan colors, grid patterns, sunset gradients, 80s sci-fi inspired design, outrun aesthetic, nostalgic electronic music vibes, cyberpunk elements, and retro-future perfection. Synthwave mastery.",

            "cyberpunk2077": "Cyberpunk 2077 style with high-tech dystopian future, neon-lit urban environment, advanced technology, dark atmosphere with bright accents, futuristic vehicles and architecture, cybernetic elements, next-gen cyberpunk aesthetic, and dystopian beauty. Cyberpunk excellence.",

            "ghibli": "Studio Ghibli style with soft watercolor-like textures, gentle harmonious color palette, whimsical character design, detailed natural environments, dreamy atmospheric lighting, hand-drawn animation quality, and Miyazaki-inspired artistic magic. Ghibli masterpiece quality.",

            "lofiaesthetic": "Lofi aesthetic with nostalgic warm colors, vintage film grain, cozy atmosphere, retro elements, peaceful ambiance, study vibes, relaxing mood, and contemporary lofi culture. Lofi aesthetic mastery.",

            "genzcore": "Gen Z core aesthetic with bright saturated colors, Y2K revival elements, digital native aesthetic, social media inspired design, trendy modern style, contemporary youth culture vibes, viral aesthetic appeal, and cutting-edge trends. Gen Z excellence.",

            "darkacademia": "Dark academia aesthetic with gothic architecture, vintage books, warm candlelight, rich browns and deep greens, scholarly atmosphere, classical elements, mysterious academic setting, intellectual beauty, and timeless elegance. Dark academia mastery.",

            "liminalspace": "Liminal space aesthetic with transitional spaces, eerie emptiness, fluorescent lighting, nostalgic yet unsettling atmosphere, abandoned public spaces, dreamlike quality, surreal familiarity, and haunting beauty. Liminal photography excellence.",

            "backrooms": "Backrooms aesthetic with endless yellow rooms, fluorescent lighting, damp carpet, liminal horror atmosphere, infinite maze-like spaces, unsettling familiarity, creepy empty interiors, psychological horror, and disturbing comfort. Backrooms horror mastery.",

            "monochrome": "Monochrome photography with dramatic black and white contrast, artistic grayscale tones, classic photography aesthetic, timeless visual appeal, sophisticated composition, and elegant monochromatic beauty. Monochrome mastery.",

            "oldhistorypainting": "Classical history painting style with Renaissance techniques, historical accuracy, dramatic composition, rich oil painting textures, museum-quality artistry, traditional fine art methods, and timeless historical beauty. Historical painting excellence.",

            "stickanimation": "Simple stick figure animation style with basic line-drawn characters, circular heads, minimalist design, clean black outlines on white background, basic geometric shapes, educational diagram aesthetic, clear visual communication, and simplified representation. Stick figure illustration excellence.",

            "charcoaldrawing": "Charcoal drawing style with rich black tones, soft smudging effects, dramatic contrast between light and dark, textured paper appearance, artistic sketching techniques, expressive line work, traditional drawing medium aesthetic, and masterful charcoal artistry. Charcoal drawing mastery.",

            "whiteboarddrawing": "Whiteboard drawing style with clean marker lines, bright white background, colorful marker strokes, educational presentation aesthetic, simple diagram style, clear visual communication, hand-drawn marker appearance, and professional whiteboard illustration. Whiteboard marker excellence.",

            "2dcartoonhorror": "2D cartoon horror style with spooky animated aesthetic, creepy but cartoonish features, horror cartoon illustration with bold outlines, eerie atmosphere, gothic cartoon design, dark animated style, frightening yet family-friendly elements, and supernatural cartoon artistry. Horror cartoon excellence.",

            "2doldcavetimecartoons": "2D old caveman cartoon style with prehistoric animated aesthetic, stone age cartoon design, primitive 2D animation, classic cartoon caveman characters, simple bold outlines, earthy colors, vintage cartoon style, prehistoric humor, and nostalgic animation charm. Caveman cartoon mastery.",

            "simple2dcartoon": "Simple 2D cartoon style with basic animation aesthetic, clean lines, minimal details, flat colors, classic cartoon design, easy-to-animate characters, family-friendly appearance, straightforward cartoon illustration, and timeless animated simplicity. Simple cartoon excellence.",

            "medievalcartoonsatire": "Medieval cartoon satire style with humorous exaggerated features, satirical medieval art aesthetic, hand-drawn cartoon with distorted expressive faces, medieval clothing and props, muted earthy color palette with browns and ochres, bold outlines and flat shading, comedic historical parody design, absurd anachronistic elements, and entertaining medieval humor. Medieval satire cartoon mastery.",

            "cartoon": "Classic cartoon style with bold outlines, vibrant colors, exaggerated features, animated character design, family-friendly aesthetic, traditional animation principles, and timeless cartoon charm. Cartoon animation excellence.",

            "sketch": "Hand-drawn sketch style with artistic line work, pencil drawing aesthetics, sketchy art techniques, traditional drawing methods, expressive sketching, and artistic illustration quality. Sketch artistry mastery.",

            "retro80s": "Retro 1980s aesthetic with neon colors, geometric patterns, vintage 80s design elements, nostalgic atmosphere, classic 80s style, retro-futuristic vibes, and authentic 1980s visual culture. Retro 80s excellence.",

            "vaporwave": "Vaporwave aesthetic with pastel pink and purple colors, retro computer graphics, nostalgic 80s-90s elements, dreamy atmosphere, vintage technology references, and contemporary internet culture. Vaporwave mastery.",

            "cottagecore": "Cottagecore aesthetic with rustic countryside charm, vintage floral patterns, cozy cottage atmosphere, natural elements, pastoral beauty, handmade crafts aesthetic, and peaceful rural living. Cottagecore excellence.",

            "nostalgicfilter": "Nostalgic filter aesthetic with vintage photo effects, warm sepia tones, film grain texture, retro photography style, memory-like quality, and sentimental visual atmosphere. Nostalgic photography mastery.",

            "vhsaesthetic": "VHS aesthetic with retro video quality, analog distortion effects, 80s-90s home video style, vintage recording atmosphere, nostalgic video culture, and authentic VHS visual characteristics. VHS retro excellence.",

            "y2k": "Y2K aesthetic with early 2000s design elements, metallic textures, futuristic millennium style, digital age optimism, tech-inspired design, and nostalgic early internet culture. Y2K design mastery.",

            "fantasyvibrant": "Vibrant fantasy world with magical mystical elements, rich saturated colors, detailed fantasy environments, otherworldly creatures, epic landscapes, enchanting magical atmosphere, and fantastical world creation. Fantasy art excellence.",

            "aigenerated": "AI-generated art style with modern digital characteristics, smooth gradients, surreal elements, contemporary digital aesthetic, trending AI art style, polished digital rendering, cutting-edge technology, futuristic artistry, and innovative visual design. AI art excellence.",

            "synthwave": "Synthwave aesthetic with retro-futuristic style, neon pink and cyan colors, grid patterns, sunset gradients, 80s sci-fi inspired design, outrun aesthetic, nostalgic electronic music vibes, cyberpunk elements, and retro-future perfection. Synthwave mastery.",

            "cyberpunk": "Cyberpunk aesthetic with neon-lit futuristic cityscape, high-tech dystopian atmosphere, electric blue and magenta lighting, advanced technology, dark urban environment with bright neon accents, cybernetic elements, futuristic architecture, and sci-fi dystopian beauty. Cyberpunk mastery.",

            "cyberpunk2077": "Cyberpunk 2077 style with high-tech dystopian future, neon-lit urban environment, advanced technology, dark atmosphere with bright accents, futuristic vehicles and architecture, cybernetic elements, next-gen cyberpunk aesthetic, and dystopian beauty. Cyberpunk excellence.",

            "lofiaesthetic": "Lofi aesthetic with soft muted colors, cozy atmosphere, vintage elements, warm lighting, nostalgic mood, relaxed vibe, study room aesthetic, calming peaceful ambiance, minimalist comfort, and serene beauty. Lofi perfection.",

            "genzcore": "Gen Z core aesthetic with bright saturated colors, Y2K revival elements, digital native aesthetic, social media inspired design, trendy modern style, contemporary youth culture vibes, viral aesthetic appeal, and cutting-edge trends. Gen Z excellence.",

            "darkacademia": "Dark academia aesthetic with gothic architecture, vintage books, warm candlelight, rich browns and deep greens, scholarly atmosphere, classical elements, mysterious academic setting, intellectual beauty, and timeless elegance. Dark academia mastery.",

            "liminalspace": "Liminal space aesthetic with transitional spaces, eerie emptiness, fluorescent lighting, nostalgic yet unsettling atmosphere, abandoned public spaces, dreamlike quality, surreal familiarity, and haunting beauty. Liminal photography excellence.",

            "backrooms": "Backrooms aesthetic with endless yellow rooms, fluorescent lighting, damp carpet, liminal horror atmosphere, infinite maze-like spaces, unsettling familiarity, creepy empty interiors, psychological horror, and disturbing comfort. Backrooms horror mastery.",

            "ghibli": "Studio Ghibli style with soft watercolor-like textures, gentle harmonious color palette, whimsical character design, detailed natural environments, dreamy atmospheric lighting, hand-drawn animation quality, and Miyazaki-inspired artistic magic. Ghibli masterpiece quality.",

            "islamic": "Rich Islamic geometric patterns, intricate arabesque designs, calligraphy-inspired decorative elements, traditional architectural motifs, jewel-toned color palette, ornate detailed craftsmanship, cultural symbols, historical accuracy, and elegant sophisticated composition. Islamic artistic heritage.",

            "stickanimationstyle": "Simple stick figure characters with basic line-drawn bodies, circular heads, minimalist design approach, clear black outlines, basic geometric shapes, clean white background, black line art style, and simplified scene representation. Stick animation simplicity.",

            "monochrome": "Classic black and white photography with dramatic contrast, rich grayscale tones, artistic monochromatic composition, timeless aesthetic appeal, sophisticated lighting, elegant shadows and highlights, vintage photographic quality, and powerful emotional depth. Monochrome artistic mastery.",

            "oldhistorypainting": "Classical historical painting style reminiscent of Dutch Golden Age masters like Rembrandt and Vermeer. Features dramatic chiaroscuro lighting with strong contrasts between light and shadow, rich oil painting textures with visible brushstrokes, period-appropriate 16th-18th century clothing including doublets, ruffs, cloaks, and ornate fabrics. Classical architectural elements with stone columns, arched doorways, and grand interiors. Warm earth tones, deep browns, golden highlights, and muted colors typical of old master paintings. Museum-quality composition with multiple figures arranged in classical poses, masterful use of light and shadow, and the timeless grandeur of historical European art. Renaissance and Baroque painting excellence.",

            "stickanimation": "Simple stick figure animation style with basic line-drawn characters, circular heads, minimalist design, clean black outlines on white background, basic geometric shapes, educational diagram aesthetic, clear visual communication, and simplified representation. Stick figure illustration excellence.",

            "charcoaldrawing": "Charcoal drawing style with rich black tones, soft smudging effects, dramatic contrast between light and dark, textured paper appearance, artistic sketching techniques, expressive line work, traditional drawing medium aesthetic, and masterful charcoal artistry. Charcoal drawing mastery.",

            "whiteboarddrawing": "Whiteboard drawing style with clean marker lines, bright white background, colorful marker strokes, educational presentation aesthetic, simple diagram style, clear visual communication, hand-drawn marker appearance, and professional whiteboard illustration. Whiteboard marker excellence.",

            "2dcartoonhorror": "2D cartoon horror style with spooky animated aesthetic, creepy but cartoonish features, horror cartoon illustration with bold outlines, eerie atmosphere, gothic cartoon design, dark animated style, frightening yet family-friendly elements, and supernatural cartoon artistry. Horror cartoon excellence.",

            "2doldcavetimecartoons": "2D old caveman cartoon style with prehistoric animated aesthetic, stone age cartoon design, primitive 2D animation, classic cartoon caveman characters, simple bold outlines, earthy colors, vintage cartoon style, prehistoric humor, and nostalgic animation charm. Caveman cartoon mastery.",

            "simple2dcartoon": "Simple 2D cartoon style with basic animation aesthetic, clean lines, minimal details, flat colors, classic cartoon design, easy-to-animate characters, family-friendly appearance, straightforward cartoon illustration, and timeless animated simplicity. Simple cartoon excellence.",

            "medievalcartoonsatire": "Medieval cartoon satire style with humorous exaggerated features, satirical medieval art aesthetic, hand-drawn cartoon with distorted expressive faces, medieval clothing and props, muted earthy color palette with browns and ochres, bold outlines and flat shading, comedic historical parody design, absurd anachronistic elements, and entertaining medieval humor. Medieval satire cartoon mastery."
        }

        # Print debug information
        print(f"Original style: {image_style}")
        print(f"Normalized style: {style_normalized}")

        # Enhanced special handling for specific styles
        if "anime" in style_lower:
            print("Anime style detected, using enhanced anime description")
            return "Vibrant Japanese anime style with clean linework, studio Ghibli inspired aesthetics, detailed character design, expressive features, dynamic poses, high quality anime aesthetic, cel-shaded coloring, atmospheric backgrounds, and emotional visual storytelling. Premium anime production quality."
        elif "ghibli" in style_lower:
            print("Ghibli style detected, using enhanced ghibli description")
            return "Studio Ghibli style with soft watercolor-like textures, gentle harmonious color palette, whimsical character design, detailed natural environments, dreamy atmospheric lighting, hand-drawn animation quality, and Miyazaki-inspired artistic magic. Ghibli masterpiece quality."
        elif "islamic" in style_lower:
            print("Islamic style detected, using enhanced Islamic description")
            return "Rich Islamic geometric patterns, intricate arabesque designs, calligraphy-inspired decorative elements, traditional architectural motifs, jewel-toned color palette, ornate detailed craftsmanship, cultural symbols, historical accuracy, and elegant sophisticated composition. Islamic artistic heritage."
        elif "horror" in style_lower:
            print("Horror style detected, using enhanced horror description")
            if "gothic" in style_lower:
                return "Gothic horror atmosphere with dark medieval architecture, dramatic shadows, candlelit ambiance, ornate stone details, mysterious fog, ancient textures, haunting gothic elements, classic horror aesthetic, eerie architectural beauty, and spine-chilling atmospheric depth. Gothic horror mastery."
            elif "realistic" in style_lower:
                return "Realistic horror style with photorealistic horror elements, unsettling atmosphere, dramatic lighting, psychological tension, modern horror cinematography, detailed textures, eerie realism, cinematic horror quality, disturbing beauty, and masterful horror artistry. Realistic horror excellence."
            elif "vintage" in style_lower:
                return "Vintage horror aesthetic with classic 1950s-70s horror movie style, grain texture, muted color palette, retro horror poster design, vintage film quality, nostalgic horror atmosphere, classic cinema horror, timeless horror beauty, and authentic vintage horror charm. Vintage horror perfection."
        elif "cyberpunk" in style_lower and "2077" in style_lower:
            print("Cyberpunk 2077 style detected, using enhanced cyberpunk description")
            return "Cyberpunk 2077 style with high-tech dystopian future, neon-lit urban environment, advanced technology, dark atmosphere with bright accents, futuristic vehicles and architecture, cybernetic elements, next-gen cyberpunk aesthetic, and dystopian beauty. Cyberpunk excellence."
        elif "synthwave" in style_lower:
            print("Synthwave style detected, using enhanced synthwave description")
            return "Synthwave aesthetic with retro-futuristic style, neon pink and cyan colors, grid patterns, sunset gradients, 80s sci-fi inspired design, outrun aesthetic, nostalgic electronic music vibes, cyberpunk elements, and retro-future perfection. Synthwave mastery."
        elif "gen" in style_lower and "z" in style_lower:
            print("Gen Z Core style detected, using enhanced Gen Z description")
            return "Gen Z core aesthetic with bright saturated colors, Y2K revival elements, digital native aesthetic, social media inspired design, trendy modern style, contemporary youth culture vibes, viral aesthetic appeal, and cutting-edge trends. Gen Z excellence."
        elif "dark" in style_lower and "academia" in style_lower:
            print("Dark Academia style detected, using enhanced dark academia description")
            return "Dark academia aesthetic with gothic architecture, vintage books, warm candlelight, rich browns and deep greens, scholarly atmosphere, classical elements, mysterious academic setting, intellectual beauty, and timeless elegance. Dark academia mastery."
        elif "liminal" in style_lower:
            print("Liminal Space style detected, using enhanced liminal description")
            return "Liminal space aesthetic with transitional spaces, eerie emptiness, fluorescent lighting, nostalgic yet unsettling atmosphere, abandoned public spaces, dreamlike quality, surreal familiarity, and haunting beauty. Liminal photography excellence."
        elif "backrooms" in style_lower:
            print("Backrooms style detected, using enhanced backrooms description")
            return "Backrooms aesthetic with endless yellow rooms, fluorescent lighting, damp carpet, liminal horror atmosphere, infinite maze-like spaces, unsettling familiarity, creepy empty interiors, psychological horror, and disturbing comfort. Backrooms horror mastery."
        elif "stickanimation" in style_lower or "stick-animation" in style_lower:
            print("Stick Animation style detected, using enhanced stick animation description")
            return "Simple stick figure animation style with basic line-drawn characters, circular heads, minimalist design, clean black outlines on white background, basic geometric shapes, educational diagram aesthetic, clear visual communication, and simplified representation. Stick figure illustration excellence."
        elif "charcoaldrawing" in style_lower or "charcoal-drawing" in style_lower:
            print("Charcoal Drawing style detected, using enhanced charcoal drawing description")
            return "Charcoal drawing style with rich black tones, soft smudging effects, dramatic contrast between light and dark, textured paper appearance, artistic sketching techniques, expressive line work, traditional drawing medium aesthetic, and masterful charcoal artistry. Charcoal drawing mastery."
        elif "whiteboarddrawing" in style_lower or "whiteboard-drawing" in style_lower:
            print("Whiteboard Drawing style detected, using enhanced whiteboard drawing description")
            return "Whiteboard drawing style with clean marker lines, bright white background, colorful marker strokes, educational presentation aesthetic, simple diagram style, clear visual communication, hand-drawn marker appearance, and professional whiteboard illustration. Whiteboard marker excellence."
        elif "2dcartoonhorror" in style_lower or "2d-cartoon-horror" in style_lower:
            print("2D Cartoon Horror style detected, using enhanced 2D cartoon horror description")
            return "2D cartoon horror style with spooky animated aesthetic, creepy but cartoonish features, horror cartoon illustration with bold outlines, eerie atmosphere, gothic cartoon design, dark animated style, frightening yet family-friendly elements, and supernatural cartoon artistry. Horror cartoon excellence."
        elif "2doldcavetimecartoons" in style_lower or "2d-old-cavetime-cartoons" in style_lower:
            print("2D Old Cavetime Cartoons style detected, using enhanced cavetime cartoon description")
            return "2D old caveman cartoon style with prehistoric animated aesthetic, stone age cartoon design, primitive 2D animation, classic cartoon caveman characters, simple bold outlines, earthy colors, vintage cartoon style, prehistoric humor, and nostalgic animation charm. Caveman cartoon mastery."
        elif "simple2dcartoon" in style_lower or "simple-2d-cartoon" in style_lower:
            print("Simple 2D Cartoon style detected, using enhanced simple cartoon description")
            return "Simple 2D cartoon style with basic animation aesthetic, clean lines, minimal details, flat colors, classic cartoon design, easy-to-animate characters, family-friendly appearance, straightforward cartoon illustration, and timeless animated simplicity. Simple cartoon excellence."
        elif "medievalcartoonsatire" in style_lower or "medieval-cartoon-satire" in style_lower:
            print("Medieval Cartoon Satire style detected, using enhanced medieval satire description")
            return "Medieval cartoon satire style with humorous exaggerated features, satirical medieval art aesthetic, hand-drawn cartoon with distorted expressive faces, medieval clothing and props, muted earthy color palette with browns and ochres, bold outlines and flat shading, comedic historical parody design, absurd anachronistic elements, and entertaining medieval humor. Medieval satire cartoon mastery."
        elif "photorealistic" in style_lower:
            print("Photorealistic style detected, using enhanced photorealistic description")
            return "Hyperrealistic professional photography with perfect lighting, ultra-detailed textures, photographic quality depth of field, natural color grading, cinematic composition, authentic environmental details, and lifelike material properties. Professional studio quality with masterful technical execution."
        elif "cinematic" in style_lower:
            print("Cinematic style detected, using enhanced cinematic description")
            return "Professional cinematic lighting with dramatic atmosphere, masterful composition, high-quality film production values, movie still quality framing, dynamic camera angles, film-like color grading, and epic visual storytelling. Blockbuster movie aesthetic with perfect cinematography."

        # Return the description for the specified style, or a default if not found
        description = style_descriptions.get(style_normalized)
        if description:
            print(f"Found style description for: {style_normalized}")
            return description
        else:
            print(f"No exact match found for style: {style_normalized}, using default description")
            return "High-quality detailed image with professional lighting and composition."


