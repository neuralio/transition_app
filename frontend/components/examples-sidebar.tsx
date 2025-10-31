"use client"

import * as React from "react"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { ChevronRight, ChevronLeft, BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"

interface ExamplesSidebarProps {
  onExampleClick?: (example: string) => void
}

export function ExamplesSidebar({ onExampleClick }: ExamplesSidebarProps) {
  const [isCollapsed, setIsCollapsed] = React.useState(false)

  const examples = [
    {
      category: "Climate Change Adaptation (CCA)",
      color: "green",
      items: [
        {
          text: "Simulate wheat yield under moderate scenario for 10 years with 20 farmers",
          code: "CCA-03",
          queries: [
            "Simulate wheat yield under moderate scenario for 10 years with 20 farmers",
            "Simulate wheat yield with 50 farmers, 3 cooperatives, 2 markets, and 2 policymakers under optimistic scenario"
          ]
        },
        {
          text: "Evaluate PV suitability under optimistic scenario with 2 energy companies",
          code: "CCA-04",
          queries: [
            "Evaluate PV suitability under optimistic scenario with 2 energy companies",
            "Show PV installation potential under pessimistic scenario with 3 energy companies"
          ]
        },
        {
          text: "Show cross-scale interactions under moderate scenario for 10 years",
          code: "CCA-10",
          queries: [
            "Show cross-scale interactions under moderate scenario for 10 years with 20 farmers",
            "Run cross-scale interactions with 20 farmers, 4 collectives, 2 markets, and 1 policymaker under pessimistic scenario",
            "Analyze policy impacts under pessimistic scenario for 10 years with 30 farmers"
          ]
        }
      ]
    },
    {
      category: "Multi-Land Use (MLU)",
      color: "cyan",
      items: [
        {
          text: "Categorize 15 land parcels under moderate scenario",
          code: "MLU-04",
          queries: [
            "Categorize 15 land parcels under moderate scenario",
            "Categorize 20 land parcels under optimistic scenario",
            "Categorize at (40.65, 22.75), (40.6, 22.58) parcels under moderate scenario"
          ]
        },
        {
          text: "Simulate land use under moderate scenario for 10 years with 15 parcels",
          code: "MLU-05",
          queries: [
            "Simulate land use under moderate scenario for 10 years with 15 parcels",
            "Simulate wheat at (40.65, 22.75), maize at (40.70, 22.80) under moderate scenario for 10 years",
            "Simulate 10 years: wheat at (40.65, 22.7), maize at (40.7, 22.8), wheat at (40.75, 22.85) with 5 collectives, 2 markets, and 1 policymaker under moderate scenario"
          ]
        },
        {
          text: "Compare historical vs future suitability for wheat",
          code: "MLU-07",
          queries: [
            "Compare historical vs future suitability for wheat under moderate scenario",
            "Show wheat suitability changes under optimistic scenario",
            "Benchmark historical vs future land suitability for maize under pessimistic scenario"
          ]
        },
        {
          text: "Show future climate scenarios for wheat under pessimistic scenario with ensemble size 3",
          code: "MLU-08",
          queries: [
            "Show future climate scenarios for wheat under pessimistic scenario with ensemble size 3",
            "Compare climate scenarios for maize under moderate scenario with ensemble size 5",
            "Analyze future projections under optimistic scenario with ensemble size 3"
          ]
        }
      ]
    },
    {
      category: "Green Credit Policy (GCP)",
      color: "amber",
      items: [
        {
          text: "Simulate PV adoption under moderate support with optimistic scenario and 20 landowners",
          code: "GCP-03",
          queries: [
            "Simulate PV adoption under moderate support with optimistic scenario and 20 landowners",
            "Analyze solar installation under low support with pessimistic scenario for 15 years"
          ]
        },
        {
          text: "Map PV adoption under low support policy with pessimistic scenario",
          code: "GCP-07",
          queries: [
            "Map PV adoption under low support policy with pessimistic scenario for 10 years with 20 landowners",
            "Display solar adoption map under high support with moderate scenario for 25 landowners"
          ]
        },
        {
          text: "Monitor feedback loops under moderate scenario for 15 years with 30 landowners",
          code: "GCP-16",
          queries: [
            "Monitor feedback loops under moderate scenario for 10years with 30 landowners",
            "Analyze policy feedback under optimistic scenario for 10 years with 25 landowners",
            "Track subsidy effectiveness under pessimistic scenario for 20 years"
          ]
        }
      ]
    },
 
  ]

  const getColorClasses = (color: string) => {
    const colors: Record<string, { text: string; bg: string; badge: string; bullet: string }> = {
      green: {
        text: "text-green-700 dark:text-green-400",
        bg: "bg-green-100 dark:bg-green-900/30",
        badge: "bg-green-700 text-white dark:bg-green-900/50 dark:text-green-300",
        bullet: "text-green-600 dark:text-green-500"
      },
      cyan: {
        text: "text-primary",
        bg: "bg-primary/10",
        badge: "bg-primary text-primary-foreground",
        bullet: "text-primary"
      },
      amber: {
        text: "text-amber-700 dark:text-amber-400",
        bg: "bg-amber-100 dark:bg-amber-900/30",
        badge: "bg-amber-700 text-white dark:bg-amber-900/50 dark:text-amber-300",
        bullet: "text-amber-600 dark:text-amber-500"
      },
      purple: {
        text: "text-purple-700 dark:text-purple-400",
        bg: "bg-purple-100 dark:bg-purple-900/30",
        badge: "bg-purple-700 text-white dark:bg-purple-900/50 dark:text-purple-300",
        bullet: "text-purple-600 dark:text-purple-500"
      },
      indigo: {
        text: "text-indigo-700 dark:text-indigo-400",
        bg: "bg-indigo-100 dark:bg-indigo-900/30",
        badge: "bg-indigo-700 text-white dark:bg-indigo-900/50 dark:text-indigo-300",
        bullet: "text-indigo-600 dark:text-indigo-500"
      }
    }
    return colors[color]
  }

  if (isCollapsed) {
    return (
      <div className="h-full border-l bg-background flex flex-col items-center p-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsCollapsed(false)}
          className="mb-4"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <div className="writing-mode-vertical text-sm font-medium text-muted-foreground">
          Examples
        </div>
      </div>
    )
  }

  return (
    <div style={{ height: 'calc(100vh - 8rem)' }} className="w-80 border-l bg-background flex flex-col">
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="font-semibold text-base">Example Queries</h2>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setIsCollapsed(true)}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-6">
          {/* Data Sources Section */}
          <div className="space-y-3 p-4 bg-accent/30 rounded-xl border">
            <h3 className="font-bold text-sm flex items-center gap-2">
              <span className="text-lg">📊</span>
              Data Sources per Use Case
            </h3>
            <div className="space-y-3">
              {/* CCA & MLU */}
              <div className="p-3 bg-card rounded-lg border">
                <h4 className="font-semibold text-xs mb-2 text-primary">
                  CCA & MLU
                </h4>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Satellite terrain data (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">Copernicus DEM</span>),
                  historical & projected climate (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">ERA5-Land</span>, <span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">CORDEX</span>),
                  crop yield estimations (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">Aquacrop</span>),
                  soil information (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">SoilGrids</span>)
                </p>
              </div>
              {/* GCP */}
              <div className="p-3 bg-card rounded-lg border">
                <h4 className="font-semibold text-xs mb-2 text-primary">
                  GCP
                </h4>
                <p className="text-xs leading-relaxed text-muted-foreground">
                  Satellite terrain data (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">Copernicus DEM</span>),
                  soil information (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">SoilGrids</span>),
                  climate projections (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">CORDEX</span>),
                  socioeconomic indicators (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">EUROSTAT</span>, <span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">FADN</span>, <span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">ECB</span>),
                  renewable energy potential (<span className="font-mono text-[11px] px-1.5 py-0.5 bg-muted rounded font-semibold text-foreground">ENSPRESO</span>)
                </p>
              </div>
            </div>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border">
            <p className="text-xs text-muted-foreground">
              Click any example below to copy it to the input box, or use them as templates for your own queries.
            </p>
          </div>

          {examples.map((section, idx) => {
            const colors = getColorClasses(section.color)
            return (
              <div key={idx} className="space-y-3">
                <h3 className={cn("font-bold text-sm", colors.text)}>
                  {section.category}
                </h3>
                <div className="space-y-4">
                  {section.items.map((item, itemIdx) => (
                    <div
                      key={itemIdx}
                      className="relative p-4 rounded-lg border bg-card"
                    >
                      {/* Code badge header */}
                      <div className="flex items-center justify-between mb-3">
                        <span className={cn(
                          "inline-block text-xs font-mono px-2 py-1 rounded font-semibold",
                          colors.badge
                        )}>
                          {item.code}
                        </span>
                      </div>

                      {/* Query examples */}
                      <div className="space-y-2">
                        {item.queries?.map((query, queryIdx) => (
                          <div
                            key={queryIdx}
                            className="relative p-2.5 rounded-md border hover:border-primary/50 hover:bg-accent/50 transition-all group cursor-pointer"
                            onClick={() => onExampleClick?.(query)}
                          >
                            <div className="flex items-start gap-2">
                              <span className={cn("mt-0.5 text-xs", colors.bullet)}>{queryIdx + 1}.</span>
                              <div className="flex-1">
                                <p className="text-xs text-foreground/90 group-hover:text-foreground leading-relaxed select-text">
                                  "{query}"
                                </p>
                                <span className="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                                  Click to use
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          <div className="mt-6 p-3 bg-accent/50 border rounded-lg">
            <p className="text-sm flex items-center gap-2">
              <span className="text-lg">💡</span>
              <span className="font-medium">Use the left sidebar to draw polygons for spatial filtering!</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

