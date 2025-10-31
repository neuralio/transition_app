import { NextRequest, NextResponse } from 'next/server';
import { Agent, setGlobalDispatcher } from 'undici';

// Configure undici agent with no timeouts for long-running phenology analysis
// AND disable SSL verification for self-signed certificates
const agent = new Agent({
  headersTimeout: 0, // Disable headers timeout (default 300s)
  bodyTimeout: 0,    // Disable body timeout
  connectTimeout: 0, // Disable connection timeout
  connect: {
    rejectUnauthorized: false, // Allow self-signed SSL certificates
  },
});
setGlobalDispatcher(agent);

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
// Note: Next.js has platform limits - Vercel free tier max is 10s, Hobby 60s, Pro 300s
// For self-hosted deployment, this can be unlimited. Adjust based on your deployment platform.
// export const maxDuration = 3600; // Commented out - let platform decide max duration

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatRequest {
  message: string;
  history?: ChatMessage[];
  geojson?: string;  // Add geojson field
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { message, geojson } = body;  // Extract geojson too

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required and must be a string' },
        { status: 400 }
      );
    }

    // Call Python backend (transition_agent.py via HTTP server)
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

    // Forward to Python backend with both message and geojson
    const backendPayload: any = { query: message };
    if (geojson) {
      backendPayload.geojson = geojson;
    }

    const response = await fetch(`${backendUrl}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendPayload),
      // Timeouts are configured globally via setGlobalDispatcher above
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error:', errorText);
      return NextResponse.json(
        { error: 'Backend service error', details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json({
      response: data.response || data.result || 'No response from backend',
      summary: data.summary || null,
      files: data.files || [],
      metadata: data.metadata || {},
      defaults_notification: data.defaults_notification || null,
      ai_insights: data.ai_insights || null,
    });

  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      {
        error: 'Failed to process chat request',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
