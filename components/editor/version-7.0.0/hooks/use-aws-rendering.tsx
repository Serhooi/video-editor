import { z } from "zod";
import { useCallback, useState } from "react";
import { CompositionProps } from "../types";
import { renderMedia, getAWSProgress } from "../ssr-helpers/aws-api";

// Define possible states for the AWS rendering process
export type AWSState =
  | { status: "init" } // Initial state
  | { status: "invoking" } // API call is being made
  | {
      // Video is being rendered
      renderId: string;
      progress: number;
      status: "rendering";
    }
  | {
      // Error occurred during rendering
      renderId: string | null;
      status: "error";
      error: Error;
    }
  | {
      // Video rendering completed successfully
      renderId: string;
      status: "done";
      url: string;
    };

export const useAWSRendering = () => {
  const [state, setState] = useState<AWSState>({ status: "init" });

  const renderVideo = useCallback(
    async (inputProps: z.infer<typeof CompositionProps>) => {
      console.log("🎬 Starting AWS Lambda video render with props:", inputProps);
      
      setState({ status: "invoking" });

      try {
        // Call AWS Lambda render API
        const response = await renderMedia(inputProps);
        
        if (response.success && response.videoUrl) {
          console.log("✅ AWS Lambda render completed:", response);
          
          setState({
            status: "done",
            renderId: response.renderId || `aws-lambda-${Date.now()}`,
            url: response.videoUrl,
          });
          
          alert("🎉 Video rendered successfully via AWS Lambda!");
        } else {
          throw new Error(response.error || "AWS Lambda render failed");
        }
      } catch (error) {
        console.error("❌ AWS Lambda render error:", error);
        setState({
          status: "error",
          renderId: null,
          error: error instanceof Error ? error : new Error(String(error)),
        });
        
        alert(`❌ AWS Lambda render failed: ${error instanceof Error ? error.message : String(error)}`);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setState({ status: "init" });
  }, []);

  return {
    state,
    renderVideo,
    reset,
  };
};

