import { z } from "zod";
import {
  RenderRequest,
  ProgressRequest,
  ProgressResponse,
} from "@/components/editor/version-7.0.0/types";
import { CompositionProps } from "@/components/editor/version-7.0.0/types";

type ApiResponse<T> = {
  type: "success" | "error";
  data?: T;
  message?: string;
};

const makeRequest = async <Res>(
  endpoint: string,
  body: unknown
): Promise<Res> => {
  console.log(`Making request to ${endpoint}`, { body });
  const result = await fetch(endpoint, {
    method: "post",
    body: JSON.stringify(body),
    headers: {
      "content-type": "application/json",
    },
  });
  
  if (!result.ok) {
    throw new Error(`HTTP error! status: ${result.status}`);
  }
  
  const json = await result.json();
  console.log(`Response received from ${endpoint}`, { json });
  
  // Check if response has error type
  if (json.type === "error") {
    console.error(`Error in response from ${endpoint}:`, json.error || json.message);
    throw new Error(json.error || json.message || "Unknown error");
  }

  // Return the response directly (not wrapped in data)
  return json as Res;
};

export interface RenderResponse {
  type: 'success' | 'error';
  renderId?: string;
  bucketName?: string;
  message?: string;
  error?: string;
}

export const renderVideo = async ({
  id,
  inputProps,
}: {
  id: string;
  inputProps: z.infer<typeof CompositionProps>;
}) => {
  console.log("Rendering video", { id, inputProps });
  const body: z.infer<typeof RenderRequest> = {
    id,
    inputProps,
  };

  const response = await makeRequest<RenderResponse>(
    "/api/latest/ssr/render",
    body
  );
  console.log("Video render response", { response });
  
  // Return the response with renderId extracted
  return {
    renderId: response.renderId!,
    bucketName: response.bucketName
  };
};

export const getProgress = async ({
  id,
  bucketName,
}: {
  id: string;
  bucketName: string;
}) => {
  console.log("Getting progress", { id });
  const body: z.infer<typeof ProgressRequest> = {
    id,
    bucketName,
  };

  const response = await makeRequest<ProgressResponse>(
    "/api/latest/ssr/progress",
    body
  );
  console.log("Progress response", { response });
  
  // Return the response directly as it already has the correct format
  return response;
};
