'use client'

import dynamic from 'next/dynamic'
import { ComponentProps } from 'react'

// Dynamically import Plot with SSR disabled
const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center w-full h-full min-h-[400px]">
      <div className="text-muted-foreground">Loading chart...</div>
    </div>
  ),
})

type PlotlyChartProps = ComponentProps<typeof Plot>

export function PlotlyChart(props: PlotlyChartProps) {
  const height = props.layout?.height || 600

  return (
    <div style={{ width: '100%', height: `${height}px`, position: 'relative' }}>
      <Plot
        {...props}
        style={{ width: '100%', height: '100%' }}
        config={{
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          ...props.config,
        }}
        layout={{
          ...props.layout,
          autosize: true,
        }}
      />
    </div>
  )
}
