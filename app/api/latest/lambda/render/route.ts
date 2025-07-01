import { NextRequest, NextResponse } from "next/server";
import { AwsRegion, renderMediaOnLambda } from "@remotion/lambda/client";
import {
  LAMBDA_FUNCTION_NAME,
  REGION,
  SITE_NAME,
} from "@/lib/constants";

interface RenderRequest {
  id: string;
  inputProps: any;
  bucketName?: string;
  composition?: string;
  codec?: string;
  crf?: number;
}

interface RenderResponse {
  type: 'success' | 'error';
  renderId?: string;
  bucketName?: string;
  message?: string;
  error?: string;
}

/**
 * API endpoint to start a Remotion video render on AWS Lambda
 */
export async function POST(request: NextRequest) {
  try {
    const body: RenderRequest = await request.json();
    
    console.log("Render request", { body });
    
    const renderResponse = await renderMediaOnLambda({
      region: REGION as AwsRegion,
      functionName: LAMBDA_FUNCTION_NAME,
      serveUrl: SITE_NAME,
      composition: body.composition || "Main",
      inputProps: body.inputProps,
      codec: (body.codec as any) || "h264",
      imageFormat: "jpeg",
      maxRetries: 1,
      framesPerLambda: 20,
    });

    const response: RenderResponse = {
      type: "success",
      renderId: renderResponse.renderId,
      bucketName: renderResponse.bucketName,
    };
    
    return NextResponse.json(response);
    
  } catch (error) {
    console.error("Error in render API:", error);
    const response: RenderResponse = {
      type: "error",
      error: error instanceof Error ? error.message : "Unknown error",
    };
    return NextResponse.json(response, { status: 500 });
  }
}

