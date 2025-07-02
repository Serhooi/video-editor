import { z } from "zod";
import { CompositionProps } from "@/components/editor/version-7.0.0/types";

export interface AWSRenderResponse {
  success: boolean;
  message?: string;
  videoUrl?: string;
  renderId?: string;
  renderType?: string;
  timestamp?: string;
  error?: string;
}

export interface AWSProgressResponse {
  renderId: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  message?: string;
  videoUrl?: string;
  timestamp?: string;
  renderType?: string;
  error?: string;
}

export const renderMedia = async (
  compositionProps: z.infer<typeof CompositionProps>
): Promise<AWSRenderResponse> => {
  console.log("🎬 AWS LAMBDA RENDER MEDIA FUNCTION CALLED!");
  alert("🎬 AWS LAMBDA RENDER STARTING!");
  
  try {
    console.log("📝 Sending AWS Lambda render request with props:", compositionProps);
    
    const response = await fetch('/api/aws-render', {
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
    console.log("✅ AWS Lambda render response:", result);

    return result;
  } catch (error: any) {
    console.error("❌ AWS Lambda render failed:", error);
    throw new Error(`AWS Lambda render failed: ${error.message}`);
  }
};

export const getAWSProgress = async (renderId: string): Promise<AWSProgressResponse> => {
  try {
    console.log("📊 Getting AWS Lambda render progress for:", renderId);
    
    const response = await fetch(`/api/aws-render/progress?renderId=${renderId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log("✅ AWS Lambda progress response:", result);

    return result;
  } catch (error: any) {
    console.error("❌ AWS Lambda progress check failed:", error);
    throw new Error(`AWS Lambda progress check failed: ${error.message}`);
  }
};

