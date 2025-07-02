import { NextRequest, NextResponse } from "next/server";

interface ProgressRequest {
  id: string;
  bucketName?: string;
}

interface ProgressResponse {
  type: 'error' | 'done' | 'progress';
  message?: string;
  progress?: number;
  url?: string;
  size?: number;
}

// Store render progress in memory (in production, use a database)
const renderProgress: { [key: string]: { progress: number; startTime: number } } = {};

/**
 * API endpoint to check the progress of a SSR video render
 */
export async function POST(request: NextRequest) {
  try {
    const body: ProgressRequest = await request.json();
    
    console.log("SSR Progress request", { body });
    
    const renderId = body.id;
    
    // Initialize progress if not exists
    if (!renderProgress[renderId]) {
      renderProgress[renderId] = {
        progress: 0,
        startTime: Date.now()
      };
    }
    
    const renderData = renderProgress[renderId];
    const elapsedTime = Date.now() - renderData.startTime;
    
    // Simulate progressive rendering over 10 seconds
    if (elapsedTime < 10000) {
      // Update progress based on elapsed time
      renderData.progress = Math.min(elapsedTime / 10000, 0.95);
      
      const response: ProgressResponse = {
        type: "progress",
        progress: renderData.progress,
        message: `SSR rendering in progress... ${Math.round(renderData.progress * 100)}%`,
      };
      
      return NextResponse.json(response);
    } else {
      // Render completed - return success with demo video URL
      delete renderProgress[renderId]; // Clean up
      
      const response: ProgressResponse = {
        type: "done",
        url: "/demo-video.mp4", // Demo video URL
        size: 1024000, // 1MB demo size
        message: "Render completed successfully",
      };
      
      return NextResponse.json(response);
    }
    
  } catch (error) {
    console.error("Error in SSR progress API:", error);
    const response: ProgressResponse = {
      type: "error",
      message: error instanceof Error ? error.message : "Failed to render video. Please try again.",
    };
    return NextResponse.json(response, { status: 500 });
  }
}

