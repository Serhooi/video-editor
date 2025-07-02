import { z } from "zod";
import { CompositionProps } from "@/components/editor/version-7.0.0/types";

export interface SimpleRenderResponse {
  success: boolean;
  message?: string;
  videoUrl?: string;
  renderType?: string;
  duration?: string;
  timestamp?: string;
  error?: string;
}

export interface SimpleProgressResponse {
  renderId: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  message?: string;
  videoUrl?: string;
  timestamp?: string;
  error?: string;
}

export const renderMedia = async (
  compositionProps: z.infer<typeof CompositionProps>
): Promise<SimpleRenderResponse> => {
  console.log("🎬 SIMPLE RENDER MEDIA FUNCTION CALLED!");
  alert("🎬 SIMPLE RENDER STARTING!");
  
  try {
    console.log("📝 Sending simple render request with props:", compositionProps);
    
    const response = await fetch('/api/simple-render', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        compositionProps,
        timestamp: new Date().toISOString()
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log("✅ Simple render response:", result);

    return result;
  } catch (error: any) {
    console.error("❌ Simple render failed:", error);
    throw new Error(`Simple render failed: ${error.message}`);
  }
};

export const getSimpleProgress = async (renderId: string): Promise<SimpleProgressResponse> => {
  try {
    console.log("📊 Getting simple render progress for:", renderId);
    
    const response = await fetch(`/api/simple-render/progress?renderId=${renderId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log("✅ Simple progress response:", result);

    return result;
  } catch (error: any) {
    console.error("❌ Simple progress check failed:", error);
    throw new Error(`Progress check failed: ${error.message}`);
  }
};

