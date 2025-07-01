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

/**
 * API endpoint to check the progress of a SSR video render
 */
export async function POST(request: NextRequest) {
  try {
    const body: ProgressRequest = await request.json();
    
    console.log("SSR Progress request", { body });
    
    // For SSR, we'll simulate progress since we don't have actual SSR rendering
    // In a real implementation, this would check the status of a server-side render job
    
    const response: ProgressResponse = {
      type: "progress",
      progress: 0.5, // Simulate 50% progress
      message: "SSR rendering in progress...",
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error("Error in SSR progress API:", error);
    const response: ProgressResponse = {
      type: "error",
      message: error instanceof Error ? error.message : "Unknown error",
    };
    return NextResponse.json(response, { status: 500 });
  }
}

