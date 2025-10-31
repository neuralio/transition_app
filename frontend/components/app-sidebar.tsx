"use client"

import * as React from "react"
import dynamic from "next/dynamic"
import { MapPin, User, LogIn, Settings, ChevronDown, ChevronUp, Terminal, AlertCircle, CheckCircle2 } from "lucide-react"
import Image from "next/image"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarFooter,
} from "@/components/ui/sidebar"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

// Dynamic import for MapDisplayDraw to avoid SSR issues with OpenLayers
const MapDisplayDraw = dynamic(() => import("@/components/map-display-draw").then(mod => ({ default: mod.MapDisplayDraw })), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center p-4">Loading map...</div>
})

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  geojsonData: string
  onGeojsonChange: (geojson: string) => void
}

export function AppSidebar({ geojsonData, onGeojsonChange, ...props }: AppSidebarProps) {
  const [isMapOpen, setIsMapOpen] = React.useState(false)
  const [ndviAlert, setNdviAlert] = React.useState<{
    type: 'success' | 'warning' | 'error'
    title: string
    message: string
  } | null>(null)

  // Handler for NDVI processing
  const handleNdviRequest = async (geojson: string, startDate: string, endDate: string) => {
    console.log('📡 NDVI Request initiated')
    console.log('  GeoJSON length:', geojson.length)
    console.log('  Date range:', startDate, 'to', endDate)

    try {
      const response = await fetch('http://localhost:8000/api/sentinel/compute-indices', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          geojson: JSON.parse(geojson),
          start_date: startDate,
          end_date: endDate
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process NDVI request')
      }

      const result = await response.json()
      console.log('✅ NDVI processing result:', result)

      // Show user-friendly message using shadcn Alert
      if (result.message) {
        console.log('📡 SENTINEL-2 RESULT:', result.message)

        if (result.ndvi_raster_path) {
          // Success case
          setNdviAlert({
            type: 'success',
            title: 'NDVI Processing Complete',
            message: result.message
          })
        } else {
          // No data case
          setNdviAlert({
            type: 'warning',
            title: 'No Satellite Data Found',
            message: result.message
          })
        }
      }
    } catch (error) {
      console.error('❌ NDVI request failed:', error)
      setNdviAlert({
        type: 'error',
        title: 'Processing Failed',
        message: error instanceof Error ? error.message : 'Unknown error occurred'
      })
      // Don't throw - error is already displayed in alert
    }
  }

  return (
    <Sidebar
      collapsible="none"
      {...props}
      className="transition-all duration-300 bg-card"
      style={{
        '--sidebar-width': isMapOpen ? '32rem' : '14rem'
      } as React.CSSProperties}
    >
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="https://transition.neuralio.ai/" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
                <div className="relative w-full h-12">
                  <Image
                    src="/transition-logo-full-horizontal-darkbg-4x.png"
                    alt="TRANSITION - Multi-Level ABM"
                    fill
                    className="object-contain object-left"
                  />
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <div className="px-2 pb-2 flex justify-center">
              <a
                href="https://neuralio.ai/"
                target="_blank"
                rel="noopener noreferrer"
                className="relative w-36 h-10"
              >
                <Image
                  src="/neuralio-logo-hor-lightbg.svg"
                  alt="Neuralio"
                  fill
                  className="object-contain opacity-70 hover:opacity-100 transition-opacity"
                />
              </a>
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {/* Navigation Menu */}
        <SidebarGroup>
          <SidebarGroupLabel>Account</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <a href="#" className="flex items-center gap-2">
                    <LogIn className="w-4 h-4" />
                    <span>Login</span>
                  </a>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <a href="#" className="flex items-center gap-2">
                    <User className="w-4 h-4" />
                    <span>Profile</span>
                  </a>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <a href="#" className="flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    <span>Settings</span>
                  </a>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Map Section - Always Visible */}
        <SidebarGroup>
          <Collapsible open={isMapOpen} onOpenChange={setIsMapOpen} className="group/collapsible">
            <SidebarGroupLabel asChild>
              <CollapsibleTrigger className="flex w-full items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  <span>Spatial Filter</span>
                </div>
                {isMapOpen ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </CollapsibleTrigger>
            </SidebarGroupLabel>
            <CollapsibleContent>
              <SidebarGroupContent>
                <div className="px-2 py-2">
                  {/* Map Component - Always Rendered */}
                  <div className="rounded-md overflow-hidden">
                    <MapDisplayDraw
                      onGeojsonChange={onGeojsonChange}
                      onNdviRequest={handleNdviRequest}
                      ndviAlert={ndviAlert}
                      onDismissAlert={() => setNdviAlert(null)}
                      className="w-full"
                      compact={true}
                    />
                  </div>
                </div>
              </SidebarGroupContent>
            </CollapsibleContent>
          </Collapsible>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <div className="px-2 py-2 text-xs text-muted-foreground text-center">
              EO-Informed Agent Based Models
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
