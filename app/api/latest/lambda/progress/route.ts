import { NextRequest, NextResponse } from "next/server";
import { AwsRegion, getRenderProgress } from "@remotion/lambda/client";
import {
  LAMBDA_FUNCTION_NAME,
  REGION,
} from "@/lib/constants";

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
 * API endpoint to check the progress of a Remotion video render on AWS Lambda
 */
export async function POST(request: NextRequest) {
  try {
    const body: ProgressRequest = await request.json();
    
    console.log("Progress request", { body });
    console.log("Bucket name", { bucketName: body.bucketName });
    
    const renderProgress = await getRenderProgress({
      bucketName: body.bucketName || 'default-bucket',
      functionName: LAMBDA_FUNCTION_NAME,
      region: REGION as AwsRegion,
      renderId: body.id,
    });

    if (renderProgress.fatalErrorEncountered) {
      const response: ProgressResponse = {
        type: "error",
        message: renderProgress.errors[0]?.message || "Unknown error",
      };
      return NextResponse.json(response);
    }

    if (renderProgress.done) {
      const response: ProgressResponse = {
        type: "done",
        url: renderProgress.outputFile as string,
        size: renderProgress.outputSizeInBytes as number,
      };
      return NextResponse.json(response);
    }

    const response: ProgressResponse = {
      type: "progress",
      progress: Math.max(0.03, renderProgress.overallProgress),
    };
    return NextResponse.json(response);
    
  } catch (error) {
    console.error("Error in progress API:", error);
    const response: ProgressResponse = {
      type: "error",
      message: error instanceof Error ? error.message : "Unknown error",
    };
    return NextResponse.json(response, { status: 500 });
  }
}

