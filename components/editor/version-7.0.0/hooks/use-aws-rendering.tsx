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
    async (inputProps?: z.infer<typeof CompositionProps>) => {
      // If no props provided, use default props
      if (!inputProps) {
        inputProps = {
          overlays: [],
          aspectRatio: { width: 16, height: 9 },
          durationInFrames: 60,
        };
      }
      
      setState({ status: "invoking" });

      try {
        // Call AWS Lambda render API
        const response = await renderMedia(inputProps);
        
        if (response.success && response.videoUrl) {
          setState({
            status: "done",
            renderId: response.renderId || `aws-lambda-${Date.now()}`,
            url: response.videoUrl,
          });
        } else {
          throw new Error(response.error || "AWS Lambda render failed");
        }
      } catch (error) {
        setState({
          status: "error",
          renderId: null,
          error: error instanceof Error ? error : new Error(String(error)),
        });
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

