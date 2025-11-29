import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { FileText, Settings as SettingsIcon, Video, Sparkles, ArrowLeft } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../services/api'

interface VideoForm {
  title: string
  description?: string
  script: string
  style: string
  resolution: string
  orientation: string
}

export default function CreateVideoPage() {
  const navigate = useNavigate()
  const [isLoading, setIsLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<VideoForm>({
    defaultValues: {
      style: 'cinematic',
      resolution: '1080p',
      orientation: 'portrait',
    }
  })

  const onSubmit = async (data: VideoForm) => {
    setIsLoading(true)
    try {
      const response = await api.post('/videos/', data)
      toast.success('🎬 Video generation started!')
      navigate(`/videos/${response.data.id}`)
    } catch (error) {
      toast.error('Failed to create video')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-6 bg-white rounded-desktop p-6 shadow-sm border border-gray-200">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-100 rounded-desktop transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Video className="w-8 h-8 text-primary-500" />
              Create New Video
            </h1>
            <p className="text-gray-600 mt-1">Configure your AI-generated video settings</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Video Details Section */}
        <div className="bg-white rounded-desktop p-6 shadow-sm border border-gray-200">
          <div className="flex items-center gap-2 mb-5 pb-4 border-b border-gray-200">
            <FileText className="w-5 h-5 text-primary-500" />
            <h2 className="text-xl font-bold text-gray-900">Video Details</h2>
          </div>
          
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Video Title <span className="text-red-500">*</span>
              </label>
              <input
                {...register('title', { required: 'Title is required' })}
                type="text"
                className="w-full px-4 py-3 bg-[#F9F9FA] border-2 border-gray-300 rounded-desktop focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 font-medium placeholder-gray-400"
                placeholder="My Amazing AI Video"
              />
              {errors.title && (
                <p className="mt-2 text-sm text-red-600 font-medium">⚠️ {errors.title.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Description <span className="text-gray-400">(Optional)</span>
              </label>
              <textarea
                {...register('description')}
                className="w-full px-4 py-3 bg-[#F9F9FA] border-2 border-gray-300 rounded-desktop focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 font-medium placeholder-gray-400"
                rows={3}
                placeholder="Brief description of your video..."
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Video Script <span className="text-red-500">*</span>
              </label>
              <textarea
                {...register('script', { 
                  required: 'Script is required', 
                  minLength: { value: 10, message: 'Script must be at least 10 characters' } 
                })}
                className="w-full px-4 py-3 bg-[#F9F9FA] border-2 border-gray-300 rounded-desktop focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 font-medium placeholder-gray-400 font-mono text-sm"
                rows={12}
                placeholder="Enter your video script here...&#10;&#10;Each paragraph will become a scene.&#10;&#10;You can write multiple paragraphs for multiple scenes."
              />
              {errors.script && (
                <p className="mt-2 text-sm text-red-600 font-medium">⚠️ {errors.script.message}</p>
              )}
              <p className="mt-2 text-xs text-gray-500 bg-blue-50 p-3 rounded-desktop border border-blue-200">
                💡 <strong>Tip:</strong> Separate each scene with a blank line. Each paragraph becomes one scene in your video.
              </p>
            </div>
          </div>
        </div>

        {/* Video Settings Section */}
        <div className="bg-white rounded-desktop p-6 shadow-sm border border-gray-200">
          <div className="flex items-center gap-2 mb-5 pb-4 border-b border-gray-200">
            <SettingsIcon className="w-5 h-5 text-primary-500" />
            <h2 className="text-xl font-bold text-gray-900">Video Settings</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                <Sparkles className="w-4 h-4 inline mr-1 text-primary-500" />
                Visual Style
              </label>
              <select 
                {...register('style')} 
                className="w-full px-4 py-3 bg-[#F9F9FA] border-2 border-gray-300 rounded-desktop focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 font-semibold cursor-pointer"
              >
                <option value="cinematic">🎬 Cinematic</option>
                <option value="anime">🎨 Anime</option>
                <option value="photorealistic">📸 Photorealistic</option>
                <option value="cartoon">🎭 Cartoon</option>
                <option value="minimalist">✨ Minimalist</option>
                <option value="3dcartoon">🎪 3D Cartoon</option>
                <option value="ghibli">🌸 Studio Ghibli</option>
                <option value="cyberpunk">🌃 Cyberpunk</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                📺 Resolution
              </label>
              <select 
                {...register('resolution')} 
                className="w-full px-4 py-3 bg-[#F9F9FA] border-2 border-gray-300 rounded-desktop focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 font-semibold cursor-pointer"
              >
                <option value="720p">720p (HD)</option>
                <option value="1080p">1080p (Full HD) ⭐</option>
                <option value="2K">2K (QHD)</option>
                <option value="4K">4K (Ultra HD)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                📱 Orientation
              </label>
              <select 
                {...register('orientation')} 
                className="w-full px-4 py-3 bg-[#F9F9FA] border-2 border-gray-300 rounded-desktop focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all text-gray-900 font-semibold cursor-pointer"
              >
                <option value="portrait">📱 Portrait (9:16)</option>
                <option value="landscape">🖥️ Landscape (16:9)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center bg-white rounded-desktop p-6 shadow-sm border border-gray-200">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-desktop font-semibold hover:bg-gray-300 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 inline mr-2" />
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading}
            className="px-8 py-3 bg-primary-500 text-white rounded-desktop font-bold hover:bg-primary-hover transition-colors shadow-md hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Creating Video...
              </>
            ) : (
              <>
                <Video className="w-5 h-5" />
                Create Video
                <Sparkles className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

