"use client"

import { AppSidebar } from "@/components/app-sidebar"
import { ChatInterfaceContent } from "@/components/chat-interface-content"
import { ExamplesSidebar } from "@/components/examples-sidebar"
import { ThemeToggle } from "@/components/theme-toggle"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { useState, useRef } from "react"
import { Trash2 } from "lucide-react"
import Image from "next/image"

export default function Home() {
  const [geojsonData, setGeojsonData] = useState('')
  const [inputValue, setInputValue] = useState('')
  const clearMessagesRef = useRef<(() => void) | null>(null)

  const handleExampleClick = (example: string) => {
    setInputValue(example)
  }

  const handleClearChat = () => {
    if (clearMessagesRef.current) {
      clearMessagesRef.current()
    }
  }

  return (
    <SidebarProvider>
      <AppSidebar
        geojsonData={geojsonData}
        onGeojsonChange={setGeojsonData}
      />
      <SidebarInset className="flex flex-row h-screen">
        <div className="flex-1 flex flex-col">
          <header className="flex h-16 shrink-0 items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <div className="flex items-center justify-between flex-1">
              <div className="relative h-12 w-48">
                <Image
                  src="/transition-logo-vertical-darkbg-1x.png"
                  alt="TRANSITION - Multi-Level ABM"
                  fill
                  className="object-contain object-left"
                />
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  onClick={handleClearChat}
                  className="text-sm"
                >
                  Clear
                </Button>
                <ThemeToggle />
              </div>
            </div>
          </header>
          <div className="flex flex-1 flex-col gap-4 p-4 overflow-hidden">
            <ChatInterfaceContent
              geojsonData={geojsonData}
              setGeojsonData={setGeojsonData}
              externalInputValue={inputValue}
              onInputValueChange={setInputValue}
              onClearMessagesRef={clearMessagesRef}
            />
          </div>
        </div>
        <div className="h-full overflow-hidden">
          <ExamplesSidebar onExampleClick={handleExampleClick} />
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
