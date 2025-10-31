"use client"

import * as React from "react"
import { Send, Loader2, Bot, User, MapPin, BookOpen, ArrowDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { ResultViewer } from "@/components/result-viewer"
import { cn } from "@/lib/utils"
import Image from "next/image"
import { useTheme } from "next-themes"

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
  defaultsNotification?: string
  aiInsights?: string
  isError?: boolean
}

interface ChatInterfaceContentProps {
  geojsonData: string
  setGeojsonData: (geojson: string) => void
  externalInputValue?: string
  onInputValueChange?: (value: string) => void
  onClearMessagesRef?: React.MutableRefObject<(() => void) | null>
}

export function ChatInterfaceContent({
  geojsonData,
  setGeojsonData,
  externalInputValue = '',
  onInputValueChange,
  onClearMessagesRef
}: ChatInterfaceContentProps) {
  const { resolvedTheme } = useTheme()
  const [messages, setMessages] = React.useState<Message[]>([])
  const [input, setInput] = React.useState('')
  const [isLoading, setIsLoading] = React.useState(false)
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const [showScrollButton, setShowScrollButton] = React.useState(false)

  // Clear messages function - expose via ref to parent
  const clearMessages = React.useCallback(() => {
    setMessages([])
  }, [])

  // Expose clear function to parent via ref
  React.useEffect(() => {
    if (onClearMessagesRef) {
      onClearMessagesRef.current = clearMessages
    }
  }, [clearMessages, onClearMessagesRef])

  // Sync external input value (from examples sidebar)
  React.useEffect(() => {
    if (externalInputValue) {
      setInput(externalInputValue)
      // Clear the external value after setting
      onInputValueChange?.('')
    }
  }, [externalInputValue, onInputValueChange])

  // Auto-scroll to bottom when new messages arrive
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Handle scroll to show/hide scroll button
  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
      setShowScrollButton(!isNearBottom && messages.length > 0)
    }
  }

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }

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
        geojson: geojsonData || undefined
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

      // Debug: Log AI insights and error details
      console.log('🔍 Backend response ai_insights:', data.ai_insights)
      console.log('🔍 Backend response data:', { isError, response: data.response, summary: data.summary })

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        // For errors, show FULL response (detailed error). For success, prefer summary.
        content: isError ? data.response : (data.summary || data.response || 'No response received'),
        timestamp: new Date(),
        // For errors, DON'T set summary - let it fall back to content (which has full error)
        // For success, use summary
        summary: isError ? undefined : data.summary,
        files: data.files || [],
        rawOutput: data.response,
        defaultsNotification: data.defaults_notification,
        aiInsights: data.ai_insights,
        isError: isError
      }

      console.log('💬 Message aiInsights field:', assistantMessage.aiInsights)

      setMessages(prev => [...prev, assistantMessage])

    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to get response. Make sure the Python backend is running on https://transitionbackend.neuralio.ai'}`,
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
    <div className="flex flex-col h-[calc(100vh-8rem)] w-full">
      {/* Persistent GeoJSON Status (always visible when polygon exists) */}
      {geojsonData && (() => {
        const isDark = resolvedTheme === 'dark';
        const greenColor = isDark ? 'rgb(22, 101, 52)' : 'rgb(16, 185, 129)'; // green-800 for dark, green-500 for light
        return (
        <div
          className="mb-4 rounded-xl"
          style={{
            border: `1px solid ${greenColor}`,
            boxShadow: `0 0 0 1px ${greenColor}`
          }}
        >
          <Card
            className="p-3 border-0"
            style={{
              backgroundColor: 'rgba(6, 78, 59, 0.1)'
            }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4" style={{ color: isDark ? '#ffffff' : '#111827' }} />
                <p className="text-sm font-medium" style={{ color: isDark ? '#ffffff' : '#111827' }}>
                  ✓ Spatial filter active - Polygon will be applied to queries
                </p>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setGeojsonData('')}
                style={{ color: isDark ? '#ffffff' : '#111827' }}
              >
                Clear
              </Button>
            </div>
          </Card>
        </div>
        );
      })()}

      {/* Chat Messages */}
      <Card className="flex-1 mb-4 flex flex-col overflow-hidden relative">
        {/* Scroll to bottom button */}
        {showScrollButton && (
          <Button
            size="icon"
            className="absolute bottom-4 right-4 z-10 rounded-full shadow-lg"
            onClick={scrollToBottom}
          >
            <ArrowDown className="h-4 w-4" />
          </Button>
        )}
        <div className="flex-1 overflow-y-scroll overflow-x-hidden p-4 scrollbar-visible" ref={scrollRef} onScroll={handleScroll}>
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full min-h-[300px]">
                <div className="text-center space-y-4 max-w-md">
                  <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                    <BookOpen className="w-10 h-10 text-primary" />
                  </div>
                  <h3 className="text-xl font-semibold">Welcome to TRANSITION!</h3>
                  <p className="text-muted-foreground">
                    Get started by selecting an example from the right sidebar, or type your own query below.
                  </p>
                  <p className="text-sm text-muted-foreground">
                    💡 Use the left sidebar to draw polygons for spatial filtering
                  </p>
                </div>
              </div>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "flex gap-3 animate-in fade-in slide-in-from-bottom-2",
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                )}
              >
                {message.role === 'assistant' && (
                  <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center flex-shrink-0 p-1">
                    <Image
                      src="/transition-brandmark-darkbg-4x.png"
                      alt="TRANSITION"
                      width={32}
                      height={32}
                      className="object-contain"
                    />
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

                    {/* AI-Generated Insights - Display after results */}
                    {message.aiInsights && (() => {
                      const isDark = resolvedTheme === 'dark';
                      return (
                      <div
                        className="mt-4 p-5 rounded-xl shadow-lg"
                        style={{
                          background: isDark ? 'linear-gradient(to bottom right, rgba(30, 58, 138, 0.3), rgba(88, 28, 135, 0.3))' : 'linear-gradient(to bottom right, #dbeafe, #e0e7ff)',
                          border: isDark ? '2px solid #1e40af' : '2px solid #60a5fa'
                        }}
                      >
                        <h4 className="text-lg font-bold mb-4 flex items-center gap-2" style={{ color: isDark ? '#93c5fd' : '#1e3a8a' }}>
                          <span className="text-2xl">📊</span>
                          <span>AI-Generated Insights</span>
                        </h4>
                        <div className="space-y-4">
                          {(() => {
                            // Parse insights: split by lines that end with ':'
                            const sections = [];
                            const lines = message.aiInsights.split('\n');
                            let currentSection = null;

                            for (const line of lines) {
                              const trimmed = line.trim();
                              if (!trimmed) continue;

                              // Check if this is a section title (ends with :)
                              if (trimmed.endsWith(':')) {
                                if (currentSection) {
                                  sections.push(currentSection);
                                }
                                currentSection = { title: trimmed.slice(0, -1), content: '' };
                              } else if (currentSection) {
                                currentSection.content += (currentSection.content ? ' ' : '') + trimmed;
                              }
                            }
                            if (currentSection) {
                              sections.push(currentSection);
                            }

                            return sections.map((section, idx) => (
                              <div
                                key={idx}
                                className="p-4 rounded-lg shadow-md"
                                style={{
                                  backgroundColor: isDark ? 'rgba(17, 24, 39, 0.4)' : '#ffffff',
                                  borderLeft: isDark ? '4px solid #60a5fa' : '4px solid #2563eb'
                                }}
                              >
                                <h5 className="font-bold text-base mb-2" style={{ color: isDark ? '#93c5fd' : '#1e3a8a' }}>{section.title}</h5>
                                <p className="text-sm leading-relaxed" style={{ color: isDark ? '#d1d5db' : '#111827' }}>{section.content}</p>
                              </div>
                            ));
                          })()}
                        </div>
                      </div>
                    );
                    })()}
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
                <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center flex-shrink-0 p-1">
                  <Image
                    src="/transition-brandmark-darkbg-4x.png"
                    alt="TRANSITION"
                    width={32}
                    height={32}
                    className="object-contain"
                  />
                </div>
                <div className="rounded-lg px-4 py-2 bg-muted">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about climate scenarios, simulations, or land use analysis... (Press Enter to send, Shift+Enter for new line)"
          className="min-h-[60px] max-h-[200px] resize-none flex-1"
          disabled={isLoading}
        />
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
