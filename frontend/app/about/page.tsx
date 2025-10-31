import Image from "next/image";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--color-border)]">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Chat
              </Button>
            </Link>
            <Image
              src="/neuralio-logo-hor-lightbg.svg"
              alt="Neuralio Logo"
              width={120}
              height={40}
              className="dark:invert"
              priority
            />
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h2 className="text-4xl font-bold tracking-tight">
              EO-Informed Agent Based Models
            </h2>
            <p className="text-xl text-[var(--color-muted-foreground)]">
              Digital Twins for Climate Resilience and Sustainable Resource Management
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 pt-8">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-left">
              <h3 className="font-semibold mb-2">Climate Change Adaptation</h3>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Simulate crop yields and PV adoption under different climate scenarios
              </p>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-left">
              <h3 className="font-semibold mb-2">Multi-Land Use</h3>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Analyze land suitability and optimize resource allocation
              </p>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-6 text-left">
              <h3 className="font-semibold mb-2">Cross-Scale Interactions</h3>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Model interactions across individual, community, market, and policy levels
              </p>
            </div>
          </div>

          <div className="pt-8">
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Built with Next.js, TypeScript, and shadcn/ui
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
