import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Key, Save, Eye, EyeOff, Check, X } from 'lucide-react'
import api from '../services/api'
import toast from 'react-hot-toast'

interface APIKey {
  id?: number
  service_name: string
  key_name: string
  api_key?: string
  is_active?: boolean
}

interface ServiceConfig {
  name: string
  description: string
  required: boolean
  placeholder: string
}

const API_SERVICES: Record<string, ServiceConfig> = {
  // AI/LLM Providers
  'groq': {
    name: 'Groq',
    description: 'Fast LLM for generating image prompts (Get from console.groq.com)',
    required: false,
    placeholder: 'gsk_...'
  },
  'openai': {
    name: 'OpenAI',
    description: 'GPT models for prompt generation (Get from platform.openai.com)',
    required: false,
    placeholder: 'sk-...'
  },
  'google': {
    name: 'Google Gemini',
    description: 'Gemini AI for prompts (Get from makersuite.google.com)',
    required: false,
    placeholder: 'AIza...'
  },
  
  // Image Generation Services
  'replicate': {
    name: 'Replicate',
    description: 'Flux image models (Get from replicate.com)',
    required: false,
    placeholder: 'r8_...'
  },
  'together': {
    name: 'Together AI',
    description: 'Fast image generation (Get from together.ai)',
    required: false,
    placeholder: 'Together API key'
  },
  'fal': {
    name: 'FAL AI',
    description: 'Flux Schnell model (Get from fal.ai)',
    required: false,
    placeholder: 'FAL API key'
  },
  'runware': {
    name: 'Runware.ai',
    description: 'Multiple Flux models (Get from runware.ai)',
    required: false,
    placeholder: 'Runware API key'
  },
  
  // TTS Services
  'elevenlabs': {
    name: 'ElevenLabs',
    description: 'Premium voice synthesis (Get from elevenlabs.io)',
    required: false,
    placeholder: 'ElevenLabs API key'
  },
  'fish_audio': {
    name: 'Fish Audio',
    description: 'High-quality TTS (Get from fish.audio)',
    required: false,
    placeholder: 'Fish Audio API key'
  }
}

export default function SettingsPage() {
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({})
  const [savedKeys, setSavedKeys] = useState<APIKey[]>([])
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    loadSavedKeys()
  }, [])

  const loadSavedKeys = async () => {
    try {
      const response = await api.get('/settings/api-keys')
      setSavedKeys(response.data)
      
      // Mark which services have saved keys
      const savedServices: Record<string, boolean> = {}
      response.data.forEach((key: APIKey) => {
        savedServices[key.service_name] = true
      })
    } catch (error) {
      console.error('Failed to load API keys:', error)
    }
  }

  const handleSaveKey = async (serviceName: string) => {
    const apiKey = apiKeys[serviceName]
    if (!apiKey || !apiKey.trim()) {
      toast.error('Please enter an API key')
      return
    }

    setIsSaving(true)
    
    // Step 1: TEST the API key first
    const testToast = toast.loading(`🧪 Testing ${API_SERVICES[serviceName].name} API key...`)
    
    try {
      const testResponse = await api.post('/settings/api-keys/test', null, {
        params: {
          service_name: serviceName,
          api_key: apiKey
        }
      })
      
      if (!testResponse.data.valid) {
        // Key is INVALID
        toast.error(testResponse.data.message, { id: testToast })
        setIsSaving(false)
        return
      }
      
      // Key is VALID - show success and proceed to save
      toast.success(testResponse.data.message, { id: testToast })
      
      // Step 2: SAVE the validated key
      const saveToast = toast.loading('💾 Saving API key...')
      
      await api.post('/settings/api-keys', {
        service_name: serviceName,
        key_name: API_SERVICES[serviceName].name,
        api_key: apiKey
      })
      
      toast.success(`✅ ${API_SERVICES[serviceName].name} API key saved and ready to use!`, { id: saveToast })
      setApiKeys({ ...apiKeys, [serviceName]: '' }) // Clear input
      await loadSavedKeys() // Reload saved keys
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('qc-api-keys-updated', {
            detail: { service: serviceName, action: 'saved' }
          })
        )
      }
      
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to validate/save API key'
      toast.error(errorMessage, { id: testToast })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteKey = async (keyId: number, serviceName: string) => {
    if (!confirm(`Delete ${API_SERVICES[serviceName]?.name || serviceName} API key?`)) return

    try {
      await api.delete(`/settings/api-keys/${keyId}`)
      toast.success('API key deleted')
      await loadSavedKeys()
      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('qc-api-keys-updated', {
            detail: { service: serviceName, action: 'deleted' }
          })
        )
      }
    } catch (error) {
      toast.error('Failed to delete API key')
    }
  }

  const toggleShowKey = (service: string) => {
    setShowKeys({ ...showKeys, [service]: !showKeys[service] })
  }

  const getKeyStatus = (serviceName: string) => {
    const saved = savedKeys.find(k => k.service_name === serviceName)
    return saved ? saved : null
  }

  return (
    <div className="max-w-5xl mx-auto text-white">
      {/* Header */}
      <div className="mb-6 app-panel p-6 bg-gradient-to-r from-[#1a224b]/80 via-[#111a38]/80 to-[#0c1429]/90">
        <div className="flex items-center gap-3">
          <SettingsIcon className="w-8 h-8 text-indigo-300" />
          <div>
            <h1 className="text-3xl font-bold text-white">Settings</h1>
            <p className="text-indigo-100/80 mt-1">Configure your API keys for video generation</p>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="mb-6 rounded-desktop border border-indigo-500/20 bg-indigo-900/20 p-5 shadow-[0_18px_42px_rgba(24,37,95,0.35)]">
        <h3 className="font-bold text-indigo-100">Why API Keys?</h3>
        <p className="mt-2 text-sm text-indigo-100/80">
          This app uses AI services to generate videos. You need to provide your own API keys to unlock premium image, voice, and prompt providers.
        </p>
        <p className="mt-3 text-sm font-semibold text-emerald-200">
          ✅ FREE Options: Pollination AI (images) and Edge TTS (voice) work without any API keys!
            </p>
      </div>

      {/* AI/LLM Providers Section */}
      <div className="mb-6 app-panel p-6 bg-white/5 border border-white/10">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Key className="w-5 h-5 text-indigo-300" />
          AI/LLM Providers (for generating prompts)
        </h2>
        <p className="text-sm text-white/70 mb-6">At least one is recommended for better quality prompts</p>
        
        <div className="space-y-4">
          {['groq', 'openai', 'google'].map(service => {
            const saved = getKeyStatus(service)
            return (
              <div key={service} className="p-4 rounded-desktop border border-white/10 bg-white/5 backdrop-blur">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-bold text-white">{API_SERVICES[service].name}</h3>
                      {saved && (
                        <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-200 rounded text-xs font-semibold flex items-center gap-1">
                          <Check className="w-3 h-3" />
                          Configured
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white/70">{API_SERVICES[service].description}</p>
                    
                    {!saved ? (
                      <div className="mt-3 flex gap-2">
                        <div className="relative flex-1">
                          <input
                            type={showKeys[service] ? "text" : "password"}
                            value={apiKeys[service] || ''}
                            onChange={(e) => setApiKeys({ ...apiKeys, [service]: e.target.value })}
                            placeholder={API_SERVICES[service].placeholder}
                            className="w-full px-4 py-2.5 bg-[#0d1734] border border-white/20 rounded-desktop focus:ring-2 focus:ring-indigo-400 focus:border-indigo-300 transition-all font-mono text-sm text-white placeholder:text-white/40"
                          />
                          <button
                            onClick={() => toggleShowKey(service)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white"
                          >
                            {showKeys[service] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                        <button
                          onClick={() => handleSaveKey(service)}
                          disabled={isSaving || !apiKeys[service]}
                          className="px-4 py-2.5 bg-gradient-to-r from-[#5a7bff] via-[#6f58ff] to-[#8c4dff] text-white rounded-desktop font-semibold hover:brightness-110 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          <Save className="w-4 h-4" />
                          Save
                        </button>
                      </div>
                    ) : (
                      <div className="mt-3 flex items-center justify-between">
                        <p className="text-xs text-white/50 font-mono">••••••••••••••••</p>
                        <button
                          onClick={() => handleDeleteKey(saved.id!, service)}
                          className="px-3 py-1.5 bg-red-500/15 text-red-200 rounded-desktop text-sm font-semibold hover:bg-red-400/20 transition-colors flex items-center gap-1"
                        >
                          <X className="w-3 h-3" />
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Image Generation Services */}
      <div className="mb-6 app-panel p-6 bg-white/5 border border-white/10">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Key className="w-5 h-5 text-indigo-300" />
          Image Generation Services
        </h2>
        <p className="text-sm text-white/70 mb-6">
          <span className="px-2 py-1 bg-emerald-400/20 text-emerald-200 rounded text-xs font-bold mr-2">FREE</span>
          Pollination AI works without API key!
        </p>
        
        <div className="space-y-4">
          {['replicate', 'together', 'fal', 'runware'].map(service => {
            const saved = getKeyStatus(service)
            return (
              <div key={service} className="p-4 rounded-desktop border border-white/10 bg-white/5 backdrop-blur">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-bold text-white">{API_SERVICES[service].name}</h3>
                      {saved && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-semibold flex items-center gap-1">
                          <Check className="w-3 h-3" />
                          Configured
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white/70">{API_SERVICES[service].description}</p>
                    
                    {!saved ? (
                      <div className="mt-3 flex gap-2">
                        <div className="relative flex-1">
                          <input
                            type={showKeys[service] ? "text" : "password"}
                            value={apiKeys[service] || ''}
                            onChange={(e) => setApiKeys({ ...apiKeys, [service]: e.target.value })}
                            placeholder={API_SERVICES[service].placeholder}
                            className="w-full px-4 py-2.5 bg-[#0d1734] border border-white/20 rounded-desktop focus:ring-2 focus:ring-indigo-400 focus:border-indigo-300 transition-all font-mono text-sm text-white placeholder:text-white/40"
                          />
                          <button
                            onClick={() => toggleShowKey(service)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          >
                            {showKeys[service] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                        <button
                          onClick={() => handleSaveKey(service)}
                          disabled={isSaving || !apiKeys[service]}
                          className="px-4 py-2.5 bg-primary-500 text-white rounded-desktop font-semibold hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          <Save className="w-4 h-4" />
                          Save
                        </button>
                      </div>
                    ) : (
                      <div className="mt-3 flex items-center justify-between">
                        <p className="text-xs text-white/50 font-mono">••••••••••••••••</p>
                        <button
                          onClick={() => handleDeleteKey(saved.id!, service)}
                          className="px-3 py-1.5 bg-red-100 text-red-700 rounded-desktop text-sm font-semibold hover:bg-red-200 transition-colors flex items-center gap-1"
                        >
                          <X className="w-3 h-3" />
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* TTS Services */}
      <div className="rounded-desktop p-6 app-panel bg-white/5 border border-white/10">
        <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <Key className="w-5 h-5 text-indigo-300" />
          Text-to-Speech Services
        </h2>
        <p className="text-sm text-white/70 mb-6">
          <span className="px-2 py-1 bg-emerald-400/20 text-emerald-200 rounded text-xs font-bold mr-2">FREE</span>
          Edge TTS works without API key!
        </p>
        
        <div className="space-y-4">
          {['elevenlabs', 'fish_audio'].map(service => {
            const saved = getKeyStatus(service)
            return (
              <div key={service} className="p-4 rounded-desktop border border-white/10 bg-white/5 backdrop-blur">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-bold text-white">{API_SERVICES[service].name}</h3>
                      {saved && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-semibold flex items-center gap-1">
                          <Check className="w-3 h-3" />
                          Configured
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-white/70">{API_SERVICES[service].description}</p>
                    
                    {!saved ? (
                      <div className="mt-3 flex gap-2">
                        <div className="relative flex-1">
                          <input
                            type={showKeys[service] ? "text" : "password"}
                            value={apiKeys[service] || ''}
                            onChange={(e) => setApiKeys({ ...apiKeys, [service]: e.target.value })}
                            placeholder={API_SERVICES[service].placeholder}
                            className="w-full px-4 py-2.5 bg-[#0d1734] border border-white/20 rounded-desktop focus:ring-2 focus:ring-indigo-400 focus:border-indigo-300 transition-all font-mono text-sm text-white placeholder:text-white/40"
                          />
                          <button
                            onClick={() => toggleShowKey(service)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          >
                            {showKeys[service] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        </div>
                        <button
                          onClick={() => handleSaveKey(service)}
                          disabled={isSaving || !apiKeys[service]}
                          className="px-4 py-2.5 bg-primary-500 text-white rounded-desktop font-semibold hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                          <Save className="w-4 h-4" />
                          Save
                        </button>
                      </div>
                    ) : (
                      <div className="mt-3 flex items-center justify-between">
                        <p className="text-xs text-white/50 font-mono">••••••••••••••••</p>
                        <button
                          onClick={() => handleDeleteKey(saved.id!, service)}
                          className="px-3 py-1.5 bg-red-100 text-red-700 rounded-desktop text-sm font-semibold hover:bg-red-200 transition-colors flex items-center gap-1"
                        >
                          <X className="w-3 h-3" />
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Quick Start Guide */}
      <div className="mt-6 rounded-desktop border border-indigo-500/20 bg-indigo-900/20 p-6 shadow-[0_18px_42px_rgba(24,37,95,0.35)]">
        <h3 className="font-bold text-white mb-3 flex items-center gap-2">
          🚀 Quick Start (No API Keys Needed!)
        </h3>
        <div className="space-y-2 text-sm text-white/80">
          <p>✅ <strong>Image Generation:</strong> Select "Pollination AI" (FREE, no key needed)</p>
          <p>✅ <strong>Text-to-Speech:</strong> Select "Edge TTS" (FREE, no key needed)</p>
          <p>✅ <strong>AI Prompts:</strong> Works with fallback if no LLM key is provided</p>
          <p className="text-xs text-white/60 mt-3 pt-3 border-t border-white/15">
            💡 For better quality, add at least one LLM key (Groq, OpenAI, or Gemini) and one premium image service
          </p>
        </div>
      </div>
    </div>
  )
}
