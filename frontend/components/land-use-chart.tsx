"use client"

import { Area, AreaChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from "recharts"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

interface LandUseData {
  year: number
  WHEAT: number
  MAIZE: number
  SOLAR: number
}

interface LandUseChartProps {
  data: LandUseData[]
  scenario: string
}

const chartConfig = {
  WHEAT: {
    label: "Wheat",
    color: "hsl(var(--chart-1))",  // Blue from globals.css
  },
  MAIZE: {
    label: "Maize",
    color: "hsl(var(--chart-2))",  // Orange from globals.css
  },
  SOLAR: {
    label: "Solar PV",
    color: "hsl(var(--chart-3))",  // From globals.css
  },
}

export function LandUseChart({ data, scenario }: LandUseChartProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Dynamic Land Use Evolution - {scenario}</CardTitle>
        <CardDescription>
          How parcels adapt to changing conditions over time
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[400px] w-full">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="year"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              className="text-muted-foreground"
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              className="text-muted-foreground"
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Legend />
            <Area
              type="monotone"
              dataKey="WHEAT"
              stackId="1"
              stroke={chartConfig.WHEAT.color}
              fill={chartConfig.WHEAT.color}
              fillOpacity={0.6}
            />
            <Area
              type="monotone"
              dataKey="MAIZE"
              stackId="1"
              stroke={chartConfig.MAIZE.color}
              fill={chartConfig.MAIZE.color}
              fillOpacity={0.6}
            />
            <Area
              type="monotone"
              dataKey="SOLAR"
              stackId="1"
              stroke={chartConfig.SOLAR.color}
              fill={chartConfig.SOLAR.color}
              fillOpacity={0.6}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
