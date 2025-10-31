"use client"

import * as React from "react"
import { FileText, Image as ImageIcon, Download, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PlotlyChart } from "@/components/plotly-chart"

interface FileInfo {
  path: string
  type: string
  name: string
  title?: string
}

interface ResultViewerProps {
  summary?: string
  files?: FileInfo[]
  rawOutput?: string
  defaultsNotification?: string  // Extracted defaults message
}

// Component to load and render Plotly JSON data
function PlotlyPreview({ url }: { url: string }) {
  const [plotData, setPlotData] = React.useState<any>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    fetch(url)
      .then(res => res.json())
      .then(data => {
        setPlotData(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [url])

  if (loading) {
    return (
      <div className="flex items-center justify-center w-full min-h-[400px]">
        <div className="text-muted-foreground">Loading visualization...</div>
      </div>
    )
  }

  if (error || !plotData) {
    return (
      <div className="flex items-center justify-center w-full min-h-[400px]">
        <div className="text-destructive">Failed to load visualization</div>
      </div>
    )
  }

  return (
    <div className="w-full" style={{ width: '100%' }}>
      <PlotlyChart
        data={plotData.data}
        layout={plotData.layout}
      />
    </div>
  )
}

// Component to load and display text/CSV content
function TextFilePreview({ url, type }: { url: string, type: string }) {
  const [content, setContent] = React.useState<string>('')
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    fetch(url)
      .then(res => res.text())
      .then(text => {
        setContent(text)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [url])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="text-sm text-muted-foreground">Loading {type.toUpperCase()} file...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-4">
        <div className="text-sm text-destructive">Failed to load file: {error}</div>
      </div>
    )
  }

  return (
    <div className="w-full">
      <pre className="p-4 bg-muted rounded text-xs overflow-auto max-h-[400px] whitespace-pre-wrap font-mono">
        {content}
      </pre>
      <div className="mt-2 flex gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => window.open(url, '_blank')}
        >
          <ExternalLink className="mr-2 h-4 w-4" />
          Open in New Tab
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            const a = document.createElement('a')
            a.href = url
            a.download = url.split('/').pop() || 'file'
            a.click()
          }}
        >
          <Download className="mr-2 h-4 w-4" />
          Download
        </Button>
      </div>
    </div>
  )
}

export function ResultViewer({ summary, files = [], rawOutput, defaultsNotification }: ResultViewerProps) {
  const [expandedFiles, setExpandedFiles] = React.useState<Set<string>>(new Set())
  const [csvSectionExpanded, setCsvSectionExpanded] = React.useState(false)

  const toggleFile = (filePath: string) => {
    const newExpanded = new Set(expandedFiles)
    if (newExpanded.has(filePath)) {
      newExpanded.delete(filePath)
    } else {
      newExpanded.add(filePath)
    }
    setExpandedFiles(newExpanded)
  }

  const getFileUrl = (filePath: string) => {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://transitionbackend.neuralio.ai'
    return `${backendUrl}/api/files/${encodeURIComponent(filePath)}`
  }

  const renderFilePreview = (file: FileInfo) => {
    const url = getFileUrl(file.path)

    // Check if this is a Plotly JSON file
    if (file.type === 'json' && file.name.includes('_plotly.json')) {
      return <PlotlyPreview url={url} />
    }

    if (file.type === 'html') {
      // Use iframe - simpler and more reliable
      return (
        <div className="w-full" style={{ width: '100%', maxWidth: '100%' }}>
          <iframe
            src={url}
            className="w-full border-0"
            title={file.name}
            style={{
              width: '100%',
              height: '900px',
              display: 'block'
            }}
          />
        </div>
      )
    }

    if (file.type === 'png' || file.type === 'jpg' || file.type === 'jpeg') {
      return (
        <div className="w-full" style={{ width: '100%', maxWidth: '100%' }}>
          <img
            src={url}
            alt={file.name}
            className="w-full"
            style={{ width: '100%', maxWidth: '100%', display: 'block' }}
          />
        </div>
      )
    }

    // TXT and CSV files - show content inline
    if (file.type === 'txt' || file.type === 'csv') {
      return <TextFilePreview url={url} type={file.type} />
    }

    // Other JSON files (not plotly) - just download buttons
    if (file.type === 'json') {
      return (
        <div className="mt-2 flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => window.open(url, '_blank')}
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            View JSON
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              const a = document.createElement('a')
              a.href = url
              a.download = file.name
              a.click()
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        </div>
      )
    }

    return null
  }

  const getFileIcon = (type: string) => {
    if (type === 'html' || type === 'png' || type === 'jpg' || type === 'jpeg') {
      return <ImageIcon className="h-4 w-4" />
    }
    return <FileText className="h-4 w-4" />
  }

  // If no files and only raw output, show a simple message
  if (files.length === 0 && !summary) {
    return (
      <div className="text-sm text-muted-foreground">
        <p className="font-semibold mb-2">✅ Simulation complete!</p>
      </div>
    )
  }

  // Separate CSV files from visualization files
  const csvFiles = files.filter(file => file.type === 'csv')
  const visualizationFiles = files.filter(file => file.type !== 'json' && file.type !== 'csv' || file.name.includes('_plotly.json'))

  return (
    <div className="space-y-4 w-full">
      {/* Summary text */}
      {summary && (
        <div className="text-sm whitespace-pre-wrap">
          {summary}
        </div>
      )}

      {/* CSV Files Section - Collapsible with smaller font */}
      {csvFiles.length > 0 && (
        <div className="border border-border rounded-lg overflow-hidden">
          <div
            className="flex items-center justify-between cursor-pointer p-2 bg-muted/50 hover:bg-muted"
            onClick={() => setCsvSectionExpanded(!csvSectionExpanded)}
          >
            <div className="flex items-center gap-2">
              <Download className="h-3.5 w-3.5" />
              <span className="text-xs font-medium text-muted-foreground">
                📥 Raw Data Files ({csvFiles.length})
              </span>
            </div>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
              <span className="text-xs">{csvSectionExpanded ? '▼' : '▶'}</span>
            </Button>
          </div>

          {csvSectionExpanded && (
            <div className="p-3 space-y-2">
              {csvFiles.map((file) => (
                <div key={file.path} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <FileText className="h-3 w-3" />
                    <span className="text-muted-foreground">{file.name}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 text-xs"
                    onClick={() => {
                      const url = getFileUrl(file.path)
                      const a = document.createElement('a')
                      a.href = url
                      a.download = file.name
                      a.click()
                    }}
                  >
                    <Download className="mr-1 h-3 w-3" />
                    Download
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Visualization Files - NO technical output, plots only */}
      {visualizationFiles.length > 0 && (
        <div className="space-y-2 w-full">
          {visualizationFiles.map((file) => (
            <div key={file.path} className="w-full border border-border rounded-lg overflow-hidden">
              <div
                className="flex items-center justify-between cursor-pointer p-3 bg-muted hover:bg-muted/80"
                onClick={() => toggleFile(file.path)}
              >
                <div className="flex items-center gap-2">
                  {getFileIcon(file.type)}
                  <span className="text-sm font-medium">{file.title || file.name}</span>
                </div>
                <Button variant="ghost" size="sm">
                  {expandedFiles.has(file.path) ? '▼' : '▶'}
                </Button>
              </div>

              {expandedFiles.has(file.path) && (
                <div className="w-full" style={{ width: '100%', padding: '1rem' }}>
                  {renderFilePreview(file)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
