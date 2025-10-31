"use client"

import * as React from "react"
import { Send, Loader2, Bot, User, MapPin } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { ResultViewer } from "@/components/result-viewer"
import { MapDisplayDraw } from "@/components/map-display-draw"
import { cn } from "@/lib/utils"

interface FileInfo {
  path: string
  type: string
  name: string
  title?: string
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  summary?: string
  files?: FileInfo[]
  rawOutput?: string
  defaultsNotification?: string  // Extracted defaults message
  isError?: boolean  // Flag for error messages
}

export function ChatInterface() {
  const [messages, setMessages] = React.useState<Message[]>([])
  const [input, setInput] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const [isInitialized, setIsInitialized] = React.useState(false)
  const [showMap, setShowMap] = React.useState(false)
  const [geojsonData, setGeojsonData] = React.useState('')

  // DEBUG: Monitor geojsonData and showMap changes
  React.useEffect(() => {
    console.log('🔍 STATE CHANGE: showMap =', showMap, ', geojsonData length =', geojsonData.length)
  }, [showMap, geojsonData])

  // Initialize welcome message on client side only
  React.useEffect(() => {
    if (!isInitialized) {
      setMessages([
        {
          id: '1',
          role: 'assistant',
          content: 'Hello! I\'m the TRANSITION AI assistant. You can ask me about climate scenarios, land use simulations, or crop yield predictions. For example:\n\n**Climate Change Adaptation (CCA):**\n• "Simulate wheat yield under moderate scenario for 10 years"\n• "Evaluate PV suitability under moderate scenario with 2 energy companies"\n\n**Multi-Land Use (MLU):**\n• "Simulate wheat under moderate scenario for 10 years with 15 parcels"\n• "Show future climate scenarios for wheat under moderate scenario with ensemble size 3"\n\n**Green Credit Policy (GCP):**\n• "Simulate PV adoption under moderate support policy for 10 years"\n• "Monitor policy feedback loop under high support for 15 years"',
          timestamp: new Date()
        }
      ])
      setIsInitialized(true)
    }
  }, [isInitialized])

  // Auto-scroll to bottom when new messages arrive
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const requestBody = {
        message: userMessage.content,
        geojson: geojsonData || undefined // Include GeoJSON if available
      }
      console.log('🔍 DEBUG: Sending request to /api/chat')
      console.log('🔍 DEBUG: geojsonData exists?', !!geojsonData)
      console.log('🔍 DEBUG: geojsonData:', geojsonData ? geojsonData.substring(0, 200) : 'null')

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to get response')
      }

      const data = await response.json()

      // Check if this is an error response
      const isError = data.metadata?.error === true

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        // For errors, use full response (details). For success, prefer summary over response.
        content: isError ? (data.response || data.summary || 'No response received') : (data.summary || data.response || 'No response received'),
        timestamp: new Date(),
        summary: isError ? null : data.summary,  // Don't show summary for errors (full content is in content field)
        files: data.files || [],
        rawOutput: data.response,
        defaultsNotification: data.defaults_notification,  // Real defaults from backend
        isError: isError  // Pass error flag for styling
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to get response. Make sure the Python backend is running on https://transitionbackend.neuralio.ai/'}`,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] w-full mx-auto">
      {/* Chat Messages */}
      <Card className="flex-1 mb-4">
        <div className="h-full overflow-y-scroll overflow-x-hidden p-4 scrollbar-visible" ref={scrollRef}>
          <div className="space-y-4 min-h-full">
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 animate-in fade-in slide-in-from-bottom-2",
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                    <Bot className="w-5 h-5 text-primary-foreground" />
                  </div>
                )}

                {/* Assistant messages - full width with defaults box */}
                {message.role === 'assistant' ? (
                  <div className="flex-1 space-y-2">
                    {/* Defaults notification - separate box above results - ONLY show if defaults were used */}
                    {message.defaultsNotification && (
                      <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded border border-blue-300 dark:border-blue-800">
                        <p className="text-xs text-foreground">
                          {message.defaultsNotification}
                        </p>
                      </div>
                    )}

                    <div
                      className={`rounded-lg px-4 py-2 break-words ${message.isError ? 'border-2 border-red-500 dark:border-red-700 font-medium' : 'bg-muted text-foreground'}`}
                      style={message.isError ? { backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#dc2626' } : undefined}
                    >
                      {(message.files?.length || message.summary) ? (
                        <ResultViewer
                          summary={message.summary}
                          files={message.files}
                          rawOutput={message.rawOutput}
                        />
                      ) : (
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      )}
                      <span className="text-xs opacity-50 mt-1 block">
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ) : (
                  /* User messages - auto width */
                  <div className="max-w-[80%] rounded-lg px-4 py-2 break-words bg-primary text-primary-foreground">
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <span className="text-xs opacity-50 mt-1 block">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                )}

                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                    <User className="w-5 h-5 text-secondary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3 justify-start animate-in fade-in">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                  <Bot className="w-5 h-5 text-primary-foreground" />
                </div>
                <div className="rounded-lg px-4 py-2 bg-muted">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Persistent GeoJSON Status with Mini Map Preview (always visible when polygon exists) */}
      {geojsonData && !showMap && (
        <Card className="mb-4 p-3 bg-green-50 dark:bg-green-900/10 border-green-300 dark:border-green-800">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Status + Mini Visual */}
            <div className="flex items-center gap-3">
              {/* Mini polygon visual indicator */}
              <div className="relative w-10 h-10 bg-gradient-to-br from-green-400/20 to-green-600/20 dark:from-green-500/20 dark:to-green-700/20 rounded border-2 border-green-500/50 dark:border-green-400/50 flex items-center justify-center">
                <svg className="w-6 h-6 text-green-600 dark:text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" opacity="0.6" />
                  <path d="M2 12l10 5 10-5" opacity="0.8" />
                </svg>
                {(() => {
                  try {
                    const geoData = JSON.parse(geojsonData);
                    const featureCount = geoData?.features?.length || 1;
                    return featureCount > 1 ? (
                      <span className="absolute -top-1 -right-1 bg-green-600 dark:bg-green-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                        {featureCount}
                      </span>
                    ) : null;
                  } catch {
                    return null;
                  }
                })()}
              </div>

              {/* Status text */}
              <div className="flex flex-col">
                <p className="text-sm font-medium text-foreground flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-green-600 dark:text-green-400" />
                  Spatial filter active
                </p>
                <p className="text-xs text-muted-foreground">
                  {(() => {
                    try {
                      const geoData = JSON.parse(geojsonData);
                      const featureCount = geoData?.features?.length || 1;
                      return `${featureCount} polygon${featureCount > 1 ? 's' : ''} will be applied to queries`;
                    } catch {
                      return 'Polygon will be applied to queries';
                    }
                  })()}
                </p>
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowMap(true)}
                className="text-xs"
              >
                Show Map
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setGeojsonData('')}
                className="text-xs"
              >
                Clear
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Map Display (always mounted, hidden with visibility when showMap=false) */}
      <div style={{ visibility: showMap ? 'visible' : 'hidden', height: showMap ? 'auto' : '0', overflow: 'hidden' }}>
        <Card className="mb-4 p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Draw Polygon for Spatial Filtering
            </h3>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowMap(false)}
            >
              Hide Map
            </Button>
          </div>
          <MapDisplayDraw
            isVisible={showMap}
            onGeojsonChange={(geojson) => {
              console.log('💬 ChatInterface: Received GeoJSON from MapDisplayDraw, length:', geojson.length)
              setGeojsonData(geojson)
            }}
          />
          {geojsonData && (
            <div className="mt-2 p-2 bg-green-100 dark:bg-green-900/20 rounded border border-green-300 dark:border-green-800">
              <p className="text-xs text-foreground">
                ✓ Polygon drawn - Will be applied to your next query
              </p>
            </div>
          )}
        </Card>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="flex-1 flex flex-col gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about climate scenarios, simulations, or land use analysis... (Press Enter to send, Shift+Enter for new line)"
            className="min-h-[60px] max-h-[200px] resize-none"
            disabled={isLoading}
          />
          {!showMap && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setShowMap(true)}
              className="self-start"
            >
              <MapPin className="w-4 h-4 mr-2" />
              Draw Polygon Filter
            </Button>
          )}
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={!input.trim() || isLoading}
          className="h-[60px] w-[60px]"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </Button>
      </form>
    </div>
  )
}
