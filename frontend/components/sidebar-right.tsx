"use client"

import * as React from "react"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { BookOpen } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

interface SidebarRightProps {
  onExampleClick?: (example: string) => void
}

export function SidebarRight({ onExampleClick }: SidebarRightProps) {
  const examples = [
    {
      category: "Climate Change Adaptation (CCA)",
      color: "green",
      items: [
        {
          text: "Simulate wheat yield under moderate scenario for 10 years with 20 farmers",
          code: "CCA-03"
        },
        {
          text: "Evaluate PV suitability under optimistic scenario with 2 energy companies",
          code: "CCA-04"
        },
        {
          text: "Show cross-scale interactions under moderate scenario for 10 years",
          code: "CCA-10"
        }
      ]
    },
    {
      category: "Multi-Land Use (MLU)",
      color: "blue",
      items: [
        {
          text: "Show LUSA data for wheat under moderate scenario",
          code: "MLU-01"
        },
        {
          text: "Simulate land use under moderate scenario for 10 years with 15 parcels",
          code: "MLU-05"
        },
        {
          text: "Show future climate scenarios for wheat under pessimistic scenario with ensemble size 3",
          code: "MLU-08"
        }
      ]
    },
    {
      category: "Green Credit Policy (GCP)",
      color: "amber",
      items: [
        {
          text: "Simulate PV adoption under moderate support with optimistic scenario and 20 landowners",
          code: "GCP-03"
        },
        {
          text: "Map PV adoption under low support policy with pessimistic scenario",
          code: "GCP-07"
        },
        {
          text: "Monitor feedback loops under moderate scenario for 15 years with 30 landowners",
          code: "GCP-16"
        }
      ]
    }
  ]

  const getColorClasses = (color: string) => {
    const colors: Record<string, { text: string; bg: string; badge: string; bullet: string }> = {
      green: {
        text: "text-green-700 dark:text-green-400",
        bg: "bg-green-100 dark:bg-green-900/30",
        badge: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
        bullet: "text-green-600 dark:text-green-500"
      },
      blue: {
        text: "text-blue-700 dark:text-blue-400",
        bg: "bg-blue-100 dark:bg-blue-900/30",
        badge: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
        bullet: "text-blue-600 dark:text-blue-500"
      },
      amber: {
        text: "text-amber-700 dark:text-amber-400",
        bg: "bg-amber-100 dark:bg-amber-900/30",
        badge: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
        bullet: "text-amber-600 dark:text-amber-500"
      }
    }
    return colors[color]
  }

  return (
    <Sidebar side="right" variant="sidebar" collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 className="font-semibold text-base">Example Queries</h2>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>
            <div className="flex items-center gap-2">
              <span className="text-lg">📊</span>
              <span>Data Sources per Use Case</span>
            </div>
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <div className="space-y-3 px-2">
              {/* CCA & MLU */}
              <div className="p-3 bg-sidebar-accent/50 rounded-lg border">
                <h4 className="font-semibold text-xs mb-2">
                  CCA & MLU
                </h4>
                <p className="text-xs leading-relaxed text-sidebar-foreground/80">
                  Satellite terrain data (<span className="font-mono text-[11px] px-1">Copernicus DEM</span>),
                  historical & projected climate (<span className="font-mono text-[11px] px-1">ERA5-Land</span>, <span className="font-mono text-[11px] px-1">CORDEX</span>),
                  crop yield estimations (<span className="font-mono text-[11px] px-1">Aquacrop</span>),
                  soil information (<span className="font-mono text-[11px] px-1">SoilGrids</span>)
                </p>
              </div>
              {/* GCP */}
              <div className="p-3 bg-sidebar-accent/50 rounded-lg border">
                <h4 className="font-semibold text-xs mb-2">
                  GCP
                </h4>
                <p className="text-xs leading-relaxed text-sidebar-foreground/80">
                  Satellite terrain data (<span className="font-mono text-[11px] px-1">Copernicus DEM</span>),
                  soil information (<span className="font-mono text-[11px] px-1">SoilGrids</span>),
                  climate projections (<span className="font-mono text-[11px] px-1">CORDEX</span>),
                  socioeconomic indicators (<span className="font-mono text-[11px] px-1">EUROSTAT</span>, <span className="font-mono text-[11px] px-1">FADN</span>, <span className="font-mono text-[11px] px-1">ECB</span>),
                  renewable energy potential (<span className="font-mono text-[11px] px-1">ENSPRESO</span>)
                </p>
              </div>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupContent>
            <div className="p-3 bg-sidebar-accent/30 rounded-lg border mx-2">
              <p className="text-xs text-sidebar-foreground/60">
                Click any example below to copy it to the input box, or use them as templates for your own queries.
              </p>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>

        {examples.map((section, idx) => {
          const colors = getColorClasses(section.color)
          return (
            <SidebarGroup key={idx}>
              <SidebarGroupLabel className={cn(colors.text)}>
                {section.category}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {section.items.map((item, itemIdx) => (
                    <SidebarMenuItem key={itemIdx}>
                      <div
                        className="relative p-3 rounded-lg border hover:border-primary/50 hover:bg-sidebar-accent transition-all group cursor-pointer mx-2"
                        onClick={() => onExampleClick?.(item.text)}
                      >
                        <div className="flex items-start gap-2">
                          <span className={cn("mt-0.5", colors.bullet)}>•</span>
                          <div className="flex-1 space-y-2">
                            <p className="text-sm text-sidebar-foreground/90 group-hover:text-sidebar-foreground leading-relaxed select-text">
                              "{item.text}"
                            </p>
                            <div className="flex items-center justify-between">
                              <span className={cn(
                                "inline-block text-xs font-mono px-2 py-0.5 rounded",
                                colors.badge
                              )}>
                                {item.code}
                              </span>
                              <span className="text-xs text-sidebar-foreground/40 opacity-0 group-hover:opacity-100 transition-opacity">
                                Click to use
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })}

        <SidebarGroup>
          <SidebarGroupContent>
            <div className="mt-6 p-3 bg-sidebar-accent/50 border rounded-lg mx-2">
              <p className="text-sm text-sidebar-foreground flex items-center gap-2">
                <span className="text-lg">💡</span>
                <span className="font-medium">Use the left sidebar to draw polygons for spatial filtering!</span>
              </p>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
