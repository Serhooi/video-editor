import { z } from "zod";
import { CompositionProps } from "@/components/editor/version-7.0.0/types";

export interface AWSRenderResponse {
  success: boolean;
  message?: string;
  videoUrl?: string;
  renderId?: string;
  bucketName?: string;
  outputFile?: string;
  renderType?: string;
  timestamp?: string;
  error?: string;
}

export interface AWSProgressResponse {
  success: boolean;
  progress?: any;
  renderId: string;
  bucketName?: string;
  error?: string;
}

export const renderMedia = async (
  compositionProps: z.infer<typeof CompositionProps>
): Promise<AWSRenderResponse> => {
  console.log("🎬 Starting Remotion Lambda render with new API!");
  
  try {
    console.log("📝 Sending render request to /api/lambda/render with props:", compositionProps);
    
    const response = await fetch('/api/lambda/render', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        id: "TestComponent",
        composition: "TestComponent",
        inputProps: compositionProps,
        compositionProps: compositionProps,
        timestamp: new Date().toISOString()
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    console.log("✅ Remotion Lambda render response:", result);

    // Return the result immediately without polling
    // The progress modal will handle polling
    return result;
  } catch (error: any) {
    console.error("❌ Remotion Lambda render failed:", error);
    throw new Error(`Remotion Lambda render failed: ${error.message}`);
  }
};

export const getAWSProgress = async (renderId: string, bucketName?: string): Promise<AWSProgressResponse> => {
  try {
    console.log("📊 Getting render progress for:", { renderId, bucketName });
    
    const response = await fetch(`/api/lambda/progress?renderId=${renderId}&bucketName=${bucketName || ''}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    console.log("✅ Progress response:", result);

    return result;
  } catch (error: any) {
    console.error("❌ Progress check failed:", error);
    throw new Error(`Progress check failed: ${error.message}`);
  }
};

