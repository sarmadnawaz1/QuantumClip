/**
 * Complete list of all 73 visual styles from the desktop app
 * Each style has a preview image in public/styles/
 */

export interface StyleInfo {
  id: string
  name: string
  normalizedName: string
  description: string
  previewImage: string
  category: string
  icon: string
}

export const ALL_STYLES: StyleInfo[] = [
  // Photography & Realistic
  {
    id: 'photorealistic',
    name: 'Photorealistic',
    normalizedName: 'photorealistic',
    description: 'Hyperrealistic professional photography with perfect lighting and ultra-detailed textures',
    previewImage: '/styles/photorealistic_preview.png',
    category: 'Photography',
    icon: '📸'
  },
  {
    id: 'hyperrealistic',
    name: 'Hyperrealistic',
    normalizedName: 'hyperrealistic',
    description: 'Extreme photorealism with incredible fine detail beyond normal photography',
    previewImage: '/styles/hyperrealistic_preview.png',
    category: 'Photography',
    icon: '🔍'
  },
  {
    id: 'cinematic',
    name: 'Cinematic',
    normalizedName: 'cinematic',
    description: 'Professional cinematic lighting with dramatic atmosphere and epic visual storytelling',
    previewImage: '/styles/cinematic_preview.png',
    category: 'Photography',
    icon: '🎬'
  },
  {
    id: 'film_noir',
    name: 'Film Noir',
    normalizedName: 'film_noir',
    description: 'Classic film noir with high contrast black and white photography and dramatic shadows',
    previewImage: '/styles/film_noir_preview.png',
    category: 'Photography',
    icon: '🎥'
  },
  {
    id: 'monochrome',
    name: 'Monochrome',
    normalizedName: 'monochrome',
    description: 'Black and white photography with dramatic contrast and artistic composition',
    previewImage: '/styles/monochrome_preview.png',
    category: 'Photography',
    icon: '⬛'
  },

  // Anime & Cartoon
  {
    id: 'anime',
    name: 'Anime',
    normalizedName: 'anime',
    description: 'Vibrant Japanese anime style with clean linework and studio Ghibli inspired aesthetics',
    previewImage: '/styles/anime_preview.png',
    category: 'Anime & Cartoon',
    icon: '🎨'
  },
  {
    id: 'ghibli',
    name: 'Studio Ghibli',
    normalizedName: 'ghibli',
    description: 'Studio Ghibli style with soft watercolor textures and whimsical character design',
    previewImage: '/styles/ghibli_preview.png',
    category: 'Anime & Cartoon',
    icon: '🌸'
  },
  {
    id: 'cartoon',
    name: 'Cartoon',
    normalizedName: 'cartoon',
    description: 'Classic cartoon style with bold outlines and vibrant colors',
    previewImage: '/styles/cartoon_preview.png',
    category: 'Anime & Cartoon',
    icon: '🎪'
  },
  {
    id: '3d_cartoon',
    name: '3D Cartoon',
    normalizedName: '3d_cartoon',
    description: '3D animated cartoon style with smooth textures and playful colors',
    previewImage: '/styles/3d_cartoon_preview.png',
    category: 'Anime & Cartoon',
    icon: '🎪'
  },
  {
    id: 'pixar_art',
    name: 'Pixar Art',
    normalizedName: 'pixar_art',
    description: '3D animated Pixar style with exaggerated proportions and warm lighting',
    previewImage: '/styles/pixar_art_preview.png',
    category: 'Anime & Cartoon',
    icon: '✨'
  },
  {
    id: 'simple_2d_cartoon',
    name: 'Simple 2D Cartoon',
    normalizedName: 'simple_2d_cartoon',
    description: 'Simple 2D cartoon style with basic animation aesthetic and clean lines',
    previewImage: '/styles/simple_2d_cartoon_preview.png',
    category: 'Anime & Cartoon',
    icon: '🎭'
  },
  {
    id: '2d_cartoon_horror',
    name: '2D Cartoon Horror',
    normalizedName: '2d_cartoon_horror',
    description: '2D cartoon horror style with spooky animated aesthetic',
    previewImage: '/styles/2d_cartoon_horror_preview.png',
    category: 'Anime & Cartoon',
    icon: '👻'
  },
  {
    id: '2d_old_cavetime_cartoons',
    name: '2D Old Cavetime Cartoons',
    normalizedName: '2d_old_cavetime_cartoons',
    description: 'Prehistoric cartoon style with stone age aesthetic',
    previewImage: '/styles/2d_old_cavetime_cartoons_preview.png',
    category: 'Anime & Cartoon',
    icon: '🦴'
  },
  {
    id: 'medieval_cartoon_satire',
    name: 'Medieval Cartoon Satire',
    normalizedName: 'medieval_cartoon_satire',
    description: 'Medieval cartoon satire with humorous exaggerated features',
    previewImage: '/styles/medieval_cartoon_satire_preview.png',
    category: 'Anime & Cartoon',
    icon: '⚔️'
  },
  {
    id: 'god_anime_vine',
    name: 'God Anime Vine',
    normalizedName: 'god_anime_vine',
    description: 'Epic anime character with divine powers and dramatic art style',
    previewImage: '/styles/god_anime_vine_preview.png',
    category: 'Anime & Cartoon',
    icon: '⚡'
  },

  // Digital & Modern
  {
    id: 'digital_art',
    name: 'Digital Art',
    normalizedName: 'digital_art',
    description: 'Professional digital illustration with vibrant colors and detailed textures',
    previewImage: '/styles/digital_art_preview.png',
    category: 'Digital & Modern',
    icon: '💻'
  },
  {
    id: 'ai_generated',
    name: 'AI Generated',
    normalizedName: 'ai_generated',
    description: 'AI-generated art style with digital perfection and algorithmic precision',
    previewImage: '/styles/ai_generated_preview.png',
    category: 'Digital & Modern',
    icon: '🤖'
  },
  {
    id: 'flat_design',
    name: 'Flat Design',
    normalizedName: 'flat_design',
    description: 'Modern flat design with clean vector graphics and solid colors',
    previewImage: '/styles/flat_design_preview.png',
    category: 'Digital & Modern',
    icon: '🎨'
  },
  {
    id: 'minimalist',
    name: 'Minimalist',
    normalizedName: 'minimalist',
    description: 'Clean minimalist design with simple geometric lines and elegant simplicity',
    previewImage: '/styles/minimalist_preview.png',
    category: 'Digital & Modern',
    icon: '⬜'
  },

  // Artistic Styles
  {
    id: 'oil_painting',
    name: 'Oil Painting',
    normalizedName: 'oil_painting',
    description: 'Traditional oil painting with rich textures and visible brushstrokes',
    previewImage: '/styles/oil_painting_preview.png',
    category: 'Artistic',
    icon: '🖌️'
  },
  {
    id: 'watercolor',
    name: 'Watercolor',
    normalizedName: 'watercolor',
    description: 'Delicate watercolor painting with gentle color blending',
    previewImage: '/styles/watercolor_preview.png',
    category: 'Artistic',
    icon: '🎨'
  },
  {
    id: 'sketch',
    name: 'Sketch',
    normalizedName: 'sketch',
    description: 'Hand-drawn sketch style with artistic line work',
    previewImage: '/styles/sketch_preview.png',
    category: 'Artistic',
    icon: '✏️'
  },
  {
    id: 'charcoal_drawing',
    name: 'Charcoal Drawing',
    normalizedName: 'charcoal_drawing',
    description: 'Charcoal drawing with rich black tones and soft smudging',
    previewImage: '/styles/charcoal_drawing_preview.png',
    category: 'Artistic',
    icon: '⚫'
  },
  {
    id: 'whiteboard_drawing',
    name: 'Whiteboard Drawing',
    normalizedName: 'whiteboard_drawing',
    description: 'Whiteboard style with clean marker lines and educational aesthetic',
    previewImage: '/styles/whiteboard_drawing_preview.png',
    category: 'Artistic',
    icon: '✍️'
  },
  {
    id: 'stick_animation',
    name: 'Stick Animation',
    normalizedName: 'stick_animation',
    description: 'Simple stick figure style with minimalist design',
    previewImage: '/styles/stick_animation_preview.png',
    category: 'Artistic',
    icon: '🧍'
  },
  {
    id: 'stick_animation_style',
    name: 'Stick Animation Style',
    normalizedName: 'stick_animation_style',
    description: 'Basic line art stick figures on white background',
    previewImage: '/styles/stick_animation_style_preview.png',
    category: 'Artistic',
    icon: '🧍'
  },
  {
    id: 'comic_book',
    name: 'Comic Book',
    normalizedName: 'comic_book',
    description: 'Professional comic book illustration with dynamic poses and bold outlines',
    previewImage: '/styles/comic_book_preview.png',
    category: 'Artistic',
    icon: '💥'
  },
  {
    id: 'pixel_art',
    name: 'Pixel Art',
    normalizedName: 'pixel_art',
    description: 'Detailed pixel art with nostalgic retro gaming aesthetic',
    previewImage: '/styles/pixel_art_preview.png',
    category: 'Artistic',
    icon: '🎮'
  },
  {
    id: 'old_history_painting',
    name: 'Old History Painting',
    normalizedName: 'old_history_painting',
    description: 'Classical history painting with Renaissance techniques',
    previewImage: '/styles/old_history_painting_preview.png',
    category: 'Artistic',
    icon: '🖼️'
  },

  // Futuristic & Cyberpunk
  {
    id: 'neon_cyberpunk',
    name: 'Neon Cyberpunk',
    normalizedName: 'neon_cyberpunk',
    description: 'Futuristic cyberpunk with vibrant neon lighting and high-tech atmosphere',
    previewImage: '/styles/neon_cyberpunk_preview.png',
    category: 'Futuristic',
    icon: '🌃'
  },
  {
    id: 'cyberpunk_2077',
    name: 'Cyberpunk 2077',
    normalizedName: 'cyberpunk_2077',
    description: 'Cyberpunk 2077 style with dystopian future and neon-lit urban environment',
    previewImage: '/styles/cyberpunk_2077_preview.png',
    category: 'Futuristic',
    icon: '🤖'
  },
  {
    id: 'synthwave',
    name: 'Synthwave',
    normalizedName: 'synthwave',
    description: 'Synthwave aesthetic with retro-futuristic style and neon colors',
    previewImage: '/styles/synthwave_preview.png',
    category: 'Futuristic',
    icon: '🌆'
  },
  {
    id: 'space_exploration',
    name: 'Space Exploration',
    normalizedName: 'space_exploration',
    description: 'Space exploration with cosmic visuals and astronomical photography',
    previewImage: '/styles/space_exploration_preview.png',
    category: 'Futuristic',
    icon: '🚀'
  },
  {
    id: 'neon_gaming',
    name: 'Neon Gaming',
    normalizedName: 'neon_gaming',
    description: 'Neon gaming aesthetic with RGB lighting and cyberpunk vibes',
    previewImage: '/styles/neon_gaming_preview.png',
    category: 'Futuristic',
    icon: '🎮'
  },

  // Horror & Dark
  {
    id: 'horror_gothic',
    name: 'Horror Gothic',
    normalizedName: 'horror_gothic',
    description: 'Gothic horror with dark medieval architecture and dramatic shadows',
    previewImage: '/styles/horror_gothic_preview.png',
    category: 'Horror & Dark',
    icon: '🏰'
  },
  {
    id: 'horror_realistic',
    name: 'Horror Realistic',
    normalizedName: 'horror_realistic',
    description: 'Realistic horror with unsettling atmosphere and dramatic lighting',
    previewImage: '/styles/horror_realistic_preview.png',
    category: 'Horror & Dark',
    icon: '😱'
  },
  {
    id: 'horror_vintage',
    name: 'Horror Vintage',
    normalizedName: 'horror_vintage',
    description: 'Vintage horror with classic 1950s horror movie style',
    previewImage: '/styles/horror_vintage_preview.png',
    category: 'Horror & Dark',
    icon: '📼'
  },
  {
    id: 'dark_aesthetic',
    name: 'Dark Aesthetic',
    normalizedName: 'dark_aesthetic',
    description: 'Moody dark aesthetic with sophisticated color palette',
    previewImage: '/styles/dark_aesthetic_preview.png',
    category: 'Horror & Dark',
    icon: '🌑'
  },
  {
    id: 'dark_academia',
    name: 'Dark Academia',
    normalizedName: 'dark_academia',
    description: 'Dark academia with gothic architecture and scholarly atmosphere',
    previewImage: '/styles/dark_academia_preview.png',
    category: 'Horror & Dark',
    icon: '📚'
  },
  {
    id: 'liminal_space',
    name: 'Liminal Space',
    normalizedName: 'liminal_space',
    description: 'Liminal space with eerie emptiness and surreal atmosphere',
    previewImage: '/styles/liminal_space_preview.png',
    category: 'Horror & Dark',
    icon: '🚪'
  },
  {
    id: 'backrooms',
    name: 'Backrooms',
    normalizedName: 'backrooms',
    description: 'Backrooms aesthetic with endless yellow rooms and fluorescent lighting',
    previewImage: '/styles/backrooms_preview.png',
    category: 'Horror & Dark',
    icon: '💡'
  },

  // Retro & Nostalgic
  {
    id: 'retro_80s',
    name: 'Retro 80s',
    normalizedName: 'retro_80s',
    description: 'Retro 1980s aesthetic with neon colors and geometric patterns',
    previewImage: '/styles/retro_80s_preview.png',
    category: 'Retro',
    icon: '📻'
  },
  {
    id: 'vaporwave',
    name: 'Vaporwave',
    normalizedName: 'vaporwave',
    description: 'Vaporwave aesthetic with pastel colors and retro computer graphics',
    previewImage: '/styles/vaporwave_preview.png',
    category: 'Retro',
    icon: '💿'
  },
  {
    id: 'vhs_aesthetic',
    name: 'VHS Aesthetic',
    normalizedName: 'vhs_aesthetic',
    description: 'VHS aesthetic with retro video quality and analog distortion',
    previewImage: '/styles/vhs_aesthetic_preview.png',
    category: 'Retro',
    icon: '📼'
  },
  {
    id: 'y2k',
    name: 'Y2K',
    normalizedName: 'y2k',
    description: 'Y2K aesthetic with early 2000s design and metallic textures',
    previewImage: '/styles/y2k_preview.png',
    category: 'Retro',
    icon: '💾'
  },
  {
    id: 'nostalgic_filter',
    name: 'Nostalgic Filter',
    normalizedName: 'nostalgic_filter',
    description: 'Nostalgic filter with vintage photo effects and warm sepia tones',
    previewImage: '/styles/nostalgic_filter_preview.png',
    category: 'Retro',
    icon: '📷'
  },
  {
    id: 'lofi_aesthetic',
    name: 'Lofi Aesthetic',
    normalizedName: 'lofi_aesthetic',
    description: 'Lofi aesthetic with soft muted colors and cozy atmosphere',
    previewImage: '/styles/lofi_aesthetic_preview.png',
    category: 'Retro',
    icon: '🎧'
  },
  {
    id: 'gen_z_core',
    name: 'Gen Z Core',
    normalizedName: 'gen_z_core',
    description: 'Gen Z core with bright saturated colors and social media inspired design',
    previewImage: '/styles/gen_z_core_preview.png',
    category: 'Retro',
    icon: '📱'
  },

  // Fantasy & Dreams
  {
    id: 'fantasy_vibrant',
    name: 'Fantasy Vibrant',
    normalizedName: 'fantasy_vibrant',
    description: 'Vibrant fantasy with magical elements and enchanted environments',
    previewImage: '/styles/fantasy_vibrant_preview.png',
    category: 'Fantasy',
    icon: '✨'
  },
  {
    id: 'pastel_dreamscape',
    name: 'Pastel Dreamscape',
    normalizedName: 'pastel_dreamscape',
    description: 'Soft pastel dreamscape with ethereal atmosphere',
    previewImage: '/styles/pastel_dreamscape_preview.png',
    category: 'Fantasy',
    icon: '🌈'
  },

  // Nature & Environment
  {
    id: 'nature_documentary',
    name: 'Nature Documentary',
    normalizedName: 'nature_documentary',
    description: 'Nature documentary with wildlife photography aesthetic',
    previewImage: '/styles/nature_documentary_preview.png',
    category: 'Nature',
    icon: '🌿'
  },
  {
    id: 'ocean_deep',
    name: 'Ocean Deep',
    normalizedName: 'ocean_deep',
    description: 'Ocean deep with underwater photography and marine beauty',
    previewImage: '/styles/ocean_deep_preview.png',
    category: 'Nature',
    icon: '🌊'
  },
  {
    id: 'mountain_landscape',
    name: 'Mountain Landscape',
    normalizedName: 'mountain_landscape',
    description: 'Mountain landscape with dramatic natural vistas',
    previewImage: '/styles/mountain_landscape_preview.png',
    category: 'Nature',
    icon: '⛰️'
  },
  {
    id: 'zen_garden',
    name: 'Zen Garden',
    normalizedName: 'zen_garden',
    description: 'Zen garden with minimalist Japanese design and peaceful atmosphere',
    previewImage: '/styles/zen_garden_preview.png',
    category: 'Nature',
    icon: '🍃'
  },
  {
    id: 'sunset_vibes',
    name: 'Sunset Vibes',
    normalizedName: 'sunset_vibes',
    description: 'Sunset vibes with golden hour lighting and warm colors',
    previewImage: '/styles/sunset_vibes_preview.png',
    category: 'Nature',
    icon: '🌅'
  },
  {
    id: 'rain_aesthetic',
    name: 'Rain Aesthetic',
    normalizedName: 'rain_aesthetic',
    description: 'Rain aesthetic with atmospheric weather photography',
    previewImage: '/styles/rain_aesthetic_preview.png',
    category: 'Nature',
    icon: '🌧️'
  },

  // Urban & Lifestyle
  {
    id: 'city_skyline',
    name: 'City Skyline',
    normalizedName: 'city_skyline',
    description: 'City skyline with urban photography and modern architecture',
    previewImage: '/styles/city_skyline_preview.png',
    category: 'Urban',
    icon: '🏙️'
  },
  {
    id: 'coffee_shop',
    name: 'Coffee Shop',
    normalizedName: 'coffee_shop',
    description: 'Cozy café atmosphere with warm lighting',
    previewImage: '/styles/coffee_shop_preview.png',
    category: 'Urban',
    icon: '☕'
  },
  {
    id: 'cottagecore',
    name: 'Cottagecore',
    normalizedName: 'cottagecore',
    description: 'Cottagecore with rustic countryside charm',
    previewImage: '/styles/cottagecore_preview.png',
    category: 'Urban',
    icon: '🌻'
  },

  // Productivity & Work
  {
    id: 'minimalist_infographic',
    name: 'Minimalist Infographic',
    normalizedName: 'minimalist_infographic',
    description: 'Clean minimalist infographic with simple geometric shapes',
    previewImage: '/styles/minimalist_infographic_preview.png',
    category: 'Productivity',
    icon: '📊'
  },
  {
    id: 'corporate_presentation',
    name: 'Corporate Presentation',
    normalizedName: 'corporate_presentation',
    description: 'Professional corporate presentation with clean layouts',
    previewImage: '/styles/corporate_presentation_preview.png',
    category: 'Productivity',
    icon: '💼'
  },
  {
    id: 'tech_tutorial',
    name: 'Tech Tutorial',
    normalizedName: 'tech_tutorial',
    description: 'Modern tech tutorial with clean interface elements',
    previewImage: '/styles/tech_tutorial_preview.png',
    category: 'Productivity',
    icon: '💻'
  },
  {
    id: 'educational_diagram',
    name: 'Educational Diagram',
    normalizedName: 'educational_diagram',
    description: 'Educational diagram with clear visual explanations',
    previewImage: '/styles/educational_diagram_preview.png',
    category: 'Productivity',
    icon: '📚'
  },
  {
    id: 'data_visualization',
    name: 'Data Visualization',
    normalizedName: 'data_visualization',
    description: 'Data visualization with modern charts and graphs',
    previewImage: '/styles/data_visualization_preview.png',
    category: 'Productivity',
    icon: '📈'
  },
  {
    id: 'productivity_aesthetic',
    name: 'Productivity Aesthetic',
    normalizedName: 'productivity_aesthetic',
    description: 'Productivity aesthetic with clean workspace design',
    previewImage: '/styles/productivity_aesthetic_preview.png',
    category: 'Productivity',
    icon: '⚡'
  },
  {
    id: 'study_motivation',
    name: 'Study Motivation',
    normalizedName: 'study_motivation',
    description: 'Study motivation with inspiring learning environment',
    previewImage: '/styles/study_motivation_preview.png',
    category: 'Productivity',
    icon: '📖'
  },
  {
    id: 'ambient_workspace',
    name: 'Ambient Workspace',
    normalizedName: 'ambient_workspace',
    description: 'Ambient workspace with cozy work environment',
    previewImage: '/styles/ambient_workspace_preview.png',
    category: 'Productivity',
    icon: '🖥️'
  },
  {
    id: 'library_study',
    name: 'Library Study',
    normalizedName: 'library_study',
    description: 'Library study with academic atmosphere and scholarly environment',
    previewImage: '/styles/library_study_preview.png',
    category: 'Productivity',
    icon: '📕'
  },

  // Minimalist & Abstract
  {
    id: 'abstract_geometric',
    name: 'Abstract Geometric',
    normalizedName: 'abstract_geometric',
    description: 'Abstract geometric design with modern shapes',
    previewImage: '/styles/abstract_geometric_preview.png',
    category: 'Abstract',
    icon: '🔷'
  },
  {
    id: 'gradient_background',
    name: 'Gradient Background',
    normalizedName: 'gradient_background',
    description: 'Gradient background with smooth color transitions',
    previewImage: '/styles/gradient_background_preview.png',
    category: 'Abstract',
    icon: '🌈'
  },
  {
    id: 'minimalist_room',
    name: 'Minimalist Room',
    normalizedName: 'minimalist_room',
    description: 'Minimalist room with clean interior aesthetic',
    previewImage: '/styles/minimalist_room_preview.png',
    category: 'Abstract',
    icon: '🏠'
  },

  // Cozy & Peaceful
  {
    id: 'cozy_reading',
    name: 'Cozy Reading',
    normalizedName: 'cozy_reading',
    description: 'Cozy reading with warm lighting and comfortable atmosphere',
    previewImage: '/styles/cozy_reading_preview.png',
    category: 'Cozy',
    icon: '📖'
  },
  {
    id: 'meditation_space',
    name: 'Meditation Space',
    normalizedName: 'meditation_space',
    description: 'Meditation space with peaceful atmosphere and zen environment',
    previewImage: '/styles/meditation_space_preview.png',
    category: 'Cozy',
    icon: '🧘'
  },
]

export const STYLE_CATEGORIES = [
  'All Styles',
  'Photography',
  'Anime & Cartoon',
  'Digital & Modern',
  'Artistic',
  'Futuristic',
  'Horror & Dark',
  'Retro',
  'Fantasy',
  'Nature',
  'Urban',
  'Productivity',
  'Abstract',
  'Cozy',
]

export function getStyleByName(name: string): StyleInfo | undefined {
  return ALL_STYLES.find(s => 
    s.normalizedName === name.toLowerCase() || 
    s.name.toLowerCase() === name.toLowerCase()
  )
}

export function getStylesByCategory(category: string): StyleInfo[] {
  if (category === 'All Styles') return ALL_STYLES
  return ALL_STYLES.filter(s => s.category === category)
}

