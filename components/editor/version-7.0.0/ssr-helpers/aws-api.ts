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
        id: "Main",
        composition: "Main",
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

    // If we have renderId and bucketName, start polling for progress
    if (result.renderId && result.bucketName) {
      console.log("🔄 Starting progress polling...");
      return await pollRenderProgress(result.renderId, result.bucketName);
    }

    return result;
  } catch (error: any) {
    console.error("❌ Remotion Lambda render failed:", error);
    throw new Error(`Remotion Lambda render failed: ${error.message}`);
  }
};

async function pollRenderProgress(renderId: string, bucketName: string): Promise<AWSRenderResponse> {
  const maxAttempts = 120; // 10 minutes max (5 seconds * 120 = 600 seconds)
  let attempts = 0;

  console.log("📊 Starting progress polling for:", { renderId, bucketName });

  while (attempts < maxAttempts) {
    try {
      const response = await fetch("/api/lambda/progress", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          renderId: renderId,
          bucketName: bucketName,
        }),
      });

      if (!response.ok) {
        throw new Error(`Progress check failed: ${response.status}`);
      }

      const progressResult = await response.json();
      console.log("📊 Render progress:", progressResult);

      if (progressResult.success && progressResult.progress) {
        const progress = progressResult.progress;
        
        // Check if render is complete
        if (progress.type === "done") {
          console.log("✅ Render completed successfully:", progress);
          return {
            success: true,
            message: "Video rendered successfully!",
            videoUrl: progress.outputFile || progress.url,
            outputFile: progress.outputFile,
            renderId: renderId,
            bucketName: bucketName,
            renderType: 'remotion-lambda',
            timestamp: new Date().toISOString()
          };
        }
        
        // Check if render failed
        if (progress.type === "error") {
          throw new Error(progress.message || "Render failed");
        }
        
        // Still in progress, continue polling
        console.log(`🔄 Render in progress... (attempt ${attempts + 1}/${maxAttempts})`);
      }

      // Wait 5 seconds before next check
      await new Promise(resolve => setTimeout(resolve, 5000));
      attempts++;
    } catch (error) {
      console.error("❌ Progress check error:", error);
      attempts++;
      
      // If we're near the end, throw the error
      if (attempts >= maxAttempts - 5) {
        throw error;
      }
      
      // Otherwise, wait and try again
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }

  throw new Error("Render timeout - exceeded maximum wait time (10 minutes)");
}

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

