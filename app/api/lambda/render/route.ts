import { NextRequest, NextResponse } from 'next/server';
import { AwsRegion, renderMediaOnLambda } from "@remotion/lambda/client";
import { LAMBDA_FUNCTION_NAME, SITE_NAME, REGION } from "@/lib/constants";

/**
 * POST endpoint handler for rendering media using Remotion Lambda
 * Following official Remotion Lambda documentation
 */
export async function POST(request: NextRequest) {
  console.log('🚀 Remotion Lambda render request received');
  
  try {
    const body = await request.json();
    console.log('📝 Request body:', body);
    
    // Validate AWS credentials
    const accessKeyId = process.env.REMOTION_AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.REMOTION_AWS_SECRET_ACCESS_KEY;
    
    if (!accessKeyId || !secretAccessKey) {
      throw new Error('AWS credentials not configured. Set REMOTION_AWS_ACCESS_KEY_ID and REMOTION_AWS_SECRET_ACCESS_KEY');
    }
    
    console.log('✅ AWS credentials validated');
    
    // Prepare input props from request
    const inputProps = body.inputProps || body.compositionProps || {
      overlays: [],
      durationInFrames: 60,
      fps: 30,
      width: 1280,
      height: 720,
      src: ''
    };
    
    const composition = body.id || body.composition || "Main";
    
    console.log('📊 Render parameters:', {
      composition,
      inputProps: Object.keys(inputProps),
      functionName: LAMBDA_FUNCTION_NAME,
      region: REGION,
      serveUrl: SITE_NAME
    });
    
    // Start Remotion Lambda render
    const result = await renderMediaOnLambda({
      codec: "h264",
      functionName: LAMBDA_FUNCTION_NAME,
      region: REGION as AwsRegion,
      serveUrl: SITE_NAME,
      composition,
      inputProps,
      framesPerLambda: 100,
      downloadBehavior: {
        type: "download",
        fileName: "video.mp4",
      },
      maxRetries: 2,
      logLevel: 'verbose',
    });
    
    console.log('✅ Remotion Lambda render completed:', {
      renderId: result.renderId,
      bucketName: result.bucketName,
      outputFile: result.outputFile
    });
    
    return NextResponse.json({
      success: true,
      message: 'Video rendered successfully!',
      renderId: result.renderId,
      bucketName: result.bucketName,
      outputFile: result.outputFile,
      videoUrl: result.outputFile,
      renderType: 'remotion-lambda',
      timestamp: new Date().toISOString()
    });
    
  } catch (error: any) {
    console.error('❌ Remotion Lambda render failed:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      details: 'Remotion Lambda render failed',
      troubleshooting: {
        functionName: LAMBDA_FUNCTION_NAME,
        region: REGION,
        serveUrl: SITE_NAME,
        hasCredentials: !!(process.env.REMOTION_AWS_ACCESS_KEY_ID && process.env.REMOTION_AWS_SECRET_ACCESS_KEY)
      }
    }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Remotion Lambda render endpoint',
    status: 'ready',
    configuration: {
      functionName: LAMBDA_FUNCTION_NAME,
      region: REGION,
      serveUrl: SITE_NAME,
      hasCredentials: !!(process.env.REMOTION_AWS_ACCESS_KEY_ID && process.env.REMOTION_AWS_SECRET_ACCESS_KEY)
    }
  });
}

