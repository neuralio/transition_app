# TRANSITION Frontend Setup

## Overview

This is the frontend for the TRANSITION project - a Next.js 15 application with TypeScript, Tailwind CSS, and shadcn/ui.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui
- **Theme**: next-themes (dark/light mode support)
- **Icons**: Lucide React

## Project Structure

```
frontend/
├── app/                      # Next.js App Router
│   ├── layout.tsx           # Root layout with theme provider
│   ├── page.tsx             # Home page
│   └── globals.css          # Global styles with shadcn theme variables
├── components/              # React components
│   ├── ui/                  # shadcn/ui components
│   │   └── button.tsx
│   ├── theme-provider.tsx   # Theme provider wrapper
│   └── theme-toggle.tsx     # Dark/light mode toggle button
├── lib/                     # Utility functions
│   └── utils.ts             # cn() helper for class merging
├── hooks/                   # Custom React hooks (empty for now)
├── public/                  # Static assets
└── components.json          # shadcn/ui configuration
```

## Installation

### Prerequisites

- Node.js 18+ (recommended: Node.js 20+)
- npm (comes with Node.js)

### Initial Setup (Already Done)

The frontend has already been initialized with the following steps:

```bash
# 1. Create Next.js 15 project
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-npm --yes

# 2. Install core dependencies
cd frontend
npm install class-variance-authority clsx tailwind-merge lucide-react next-themes

# 3. Set up shadcn/ui
npx shadcn@latest add button
```

### Running the Development Server

```bash
# Navigate to frontend directory
cd /home/ggous/Models/Transition/frontend

# Install dependencies (if not already installed)
npm install

# Start the development server
npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000)

## Available Scripts

```bash
# Development server (with hot reload)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Theme Configuration

The application supports dark and light themes using `next-themes`.

### Theme Variables

Custom theme variables are defined in [app/globals.css](app/globals.css) using CSS custom properties:

- **Light mode**: `:root { ... }`
- **Dark mode**: `.dark { ... }`

### Theme Toggle

Users can switch themes using the theme toggle button in the header (sun/moon icon).

The theme preference is:
- Automatically detected from system preferences by default
- Persisted in localStorage
- Applied without page reload

## Adding shadcn/ui Components

To add more shadcn/ui components:

```bash
# Add a single component
npx shadcn@latest add [component-name]

# Example: Add card component
npx shadcn@latest add card

# Add multiple components
npx shadcn@latest add card dialog dropdown-menu
```

Available components: https://ui.shadcn.com/docs/components

## Customization

### Changing Theme Colors

Edit [app/globals.css](app/globals.css) to customize theme colors:

```css
:root {
  --primary: 0 0% 9%;           /* Primary color (light mode) */
  --background: 0 0% 100%;      /* Background (light mode) */
  /* ... */
}

.dark {
  --primary: 0 0% 98%;          /* Primary color (dark mode) */
  --background: 0 0% 3.9%;      /* Background (dark mode) */
  /* ... */
}
```

### Adding Custom Fonts

Fonts are configured in [app/layout.tsx](app/layout.tsx):

```typescript
import { Geist, Geist_Mono } from "next/font/google";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});
```

## Integration with Backend

The backend Python services are located in:
- `/home/ggous/Models/Transition/backend/` - Core simulation
- `/home/ggous/Models/Transition/use_cases/` - Use case implementations
- `/home/ggous/Models/Transition/llm_interface/` - Natural language interface

### API Integration (To Be Implemented)

Future tasks:
1. Create API routes in `app/api/` to communicate with Python backend
2. Set up API client for fetching simulation results
3. Create data visualization components for:
   - Land use maps (Leaflet/Mapbox)
   - Time-series charts (D3.js/Plotly)
   - Agent interaction diagrams
4. Build forms for simulation configuration

## Troubleshooting

### Port Already in Use

If port 3000 is already in use:

```bash
# Use a different port
PORT=3001 npm run dev
```

### Module Not Found Errors

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### Theme Not Working

Ensure `suppressHydrationWarning` is set on the `<html>` tag in [app/layout.tsx](app/layout.tsx):

```tsx
<html lang="en" suppressHydrationWarning>
```

## Next Steps

1. **API Integration**: Connect to Python backend via REST API or WebSocket
2. **State Management**: Add Zustand for global state management
3. **Visualization Components**: Implement Leaflet maps and Plotly charts
4. **User Authentication**: Add auth if needed
5. **Form Validation**: Add form handling for simulation parameters
6. **Testing**: Set up Jest and React Testing Library

## Resources

- **Next.js Docs**: https://nextjs.org/docs
- **shadcn/ui**: https://ui.shadcn.com
- **Tailwind CSS**: https://tailwindcss.com/docs
- **TypeScript**: https://www.typescriptlang.org/docs
- **next-themes**: https://github.com/pacocoursey/next-themes

## License

Part of the TRANSITION project - EO-Informed Agent Based Models for Digital Twins Applications
