import { z } from "zod";
import { useCallback, useState } from "react";
import { CompositionProps } from "../types";
import { renderMedia, getAWSProgress } from "../ssr-helpers/aws-api";
import { useRenderProgress } from "./use-render-progress";

// Define possible states for the AWS rendering process
export type AWSState =
  | { status: "init" } // Initial state
  | { status: "invoking" } // API call is being made
  | {
      // Video render started, progress modal will handle the rest
      renderId: string;
      bucketName: string;
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
  const { renderState, startRender, onRenderComplete, onRenderError, closeProgress, resetRender } = useRenderProgress();

  const renderVideo = useCallback(
    async (inputProps?: z.infer<typeof CompositionProps>) => {
      console.log("🎬 RENDER VIDEO CALLED!");
      
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
        // Call AWS Lambda render API (just starts the render, doesn't poll)
        const response = await renderMedia(inputProps);
        
        if (response.success && response.renderId && response.bucketName) {
          // Update state to rendering
          setState({
            status: "rendering",
            renderId: response.renderId,
            bucketName: response.bucketName,
          });
          
          // Start the progress modal
          startRender(response.renderId, response.bucketName);
        } else {
          throw new Error(response.error || "AWS Lambda render failed - no renderId received");
        }
      } catch (error) {
        setState({
          status: "error",
          renderId: null,
          error: error instanceof Error ? error : new Error(String(error)),
        });
      }
    },
    [startRender]
  );

  const reset = useCallback(() => {
    setState({ status: "init" });
    resetRender();
  }, [resetRender]);

  // Handle render completion from progress modal
  const handleRenderComplete = useCallback((videoUrl: string) => {
    setState(prev => ({
      status: "done",
      renderId: prev.status === "rendering" ? prev.renderId : `aws-lambda-${Date.now()}`,
      url: videoUrl,
    }));
    onRenderComplete(videoUrl);
  }, [onRenderComplete]);

  // Handle render error from progress modal
  const handleRenderError = useCallback((error: string) => {
    setState(prev => ({
      status: "error",
      renderId: prev.status === "rendering" ? prev.renderId : null,
      error: new Error(error),
    }));
    onRenderError(error);
  }, [onRenderError]);

  return {
    state,
    renderVideo,
    reset,
    renderState,
    onRenderComplete: handleRenderComplete,
    onRenderError: handleRenderError,
    closeProgress,
  };
};

