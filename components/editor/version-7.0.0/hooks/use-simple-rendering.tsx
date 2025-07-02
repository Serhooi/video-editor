import { z } from "zod";
import { useCallback, useState } from "react";
import { CompositionProps } from "../types";
import { renderMedia, getSimpleProgress } from "../ssr-helpers/simple-api";

// Define possible states for the simple rendering process
export type SimpleState =
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

export const useSimpleRendering = () => {
  const [state, setState] = useState<SimpleState>({ status: "init" });

  const renderVideo = useCallback(
    async (inputProps: z.infer<typeof CompositionProps>) => {
      console.log("🎬 Starting simple video render with props:", inputProps);
      
      setState({ status: "invoking" });

      try {
        // Call simple render API
        const response = await renderMedia(inputProps);
        
        if (response.success && response.videoUrl) {
          console.log("✅ Simple render completed immediately:", response);
          
          setState({
            status: "done",
            renderId: `simple-${Date.now()}`,
            url: response.videoUrl,
          });
          
          alert("🎉 Video rendered successfully! Demo video is ready.");
        } else {
          throw new Error(response.error || "Simple render failed");
        }
      } catch (error) {
        console.error("❌ Simple render error:", error);
        setState({
          status: "error",
          renderId: null,
          error: error instanceof Error ? error : new Error(String(error)),
        });
        
        alert(`❌ Render failed: ${error instanceof Error ? error.message : String(error)}`);
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

