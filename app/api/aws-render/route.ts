import { NextRequest, NextResponse } from 'next/server';
import { AwsRegion, RenderMediaOnLambdaOutput, renderMediaOnLambda } from "@remotion/lambda/client";

/**
 * Configuration for the Lambda render function
 */
const LAMBDA_CONFIG = {
  FRAMES_PER_LAMBDA: 100,
  MAX_RETRIES: 2,
  CODEC: "h264" as const,
} as const;

/**
 * Validates AWS credentials are present in environment variables
 * Prioritizes REMOTION_ prefixed variables over standard AWS variables
 * @throws {TypeError} If AWS credentials are missing
 */
const validateAwsCredentials = () => {
  console.log("🔍 Validating AWS credentials...");
  
  const accessKeyId = process.env.REMOTION_AWS_ACCESS_KEY_ID || process.env.AWS_ACCESS_KEY_ID;
  const secretAccessKey = process.env.REMOTION_AWS_SECRET_ACCESS_KEY || process.env.AWS_SECRET_ACCESS_KEY;
  
  if (!accessKeyId) {
    throw new TypeError(
      "Set up Remotion Lambda to render videos. REMOTION_AWS_ACCESS_KEY_ID or AWS_ACCESS_KEY_ID is missing."
    );
  }
  
  if (!secretAccessKey) {
    throw new TypeError(
      "The environment variable REMOTION_AWS_SECRET_ACCESS_KEY or AWS_SECRET_ACCESS_KEY is missing."
    );
  }
  
  console.log("✅ AWS credentials validation passed", {
    usingRemotionPrefix: !!process.env.REMOTION_AWS_ACCESS_KEY_ID,
    accessKeyId: accessKeyId.substring(0, 8) + '...'
  });
};

/**
 * POST endpoint handler for rendering media using Remotion Lambda
 */
export async function POST(request: NextRequest) {
  console.log('🚀 Remotion Lambda render request received');
  
  // Parse request body first (outside try block for fallback access)
  const body = await request.json();
  console.log('📝 Request body:', body);
  
  try {
    
    // Validate AWS credentials
    validateAwsCredentials();
    
    // Get configuration from environment variables (prioritize REMOTION_ prefix)
    const region = (process.env.REMOTION_AWS_REGION || process.env.AWS_REGION || 'us-east-1') as AwsRegion;
    const functionName = process.env.REMOTION_LAMBDA_FUNCTION_NAME || process.env.AWS_LAMBDA_FUNCTION_NAME;
    const serveUrl = process.env.REMOTION_SERVE_URL || process.env.SITE_NAME;
    
    console.log('🔧 Remotion Lambda Configuration:', {
      region,
      functionName,
      serveUrl,
      usingRemotionPrefix: {
        credentials: !!process.env.REMOTION_AWS_ACCESS_KEY_ID,
        region: !!process.env.REMOTION_AWS_REGION,
        functionName: !!process.env.REMOTION_LAMBDA_FUNCTION_NAME,
        serveUrl: !!process.env.REMOTION_SERVE_URL
      }
    });
    
    if (!functionName) {
      throw new Error('Missing REMOTION_LAMBDA_FUNCTION_NAME or AWS_LAMBDA_FUNCTION_NAME environment variable');
    }
    
    if (!serveUrl) {
      throw new Error('Missing REMOTION_SERVE_URL or SITE_NAME environment variable');
    }
    
    // Prepare input props - handle both formats
    let inputProps;
    
    // Check if data comes as compositionProps (from frontend)
    if (body.compositionProps) {
      inputProps = body.compositionProps;
      console.log('📊 Using compositionProps from request body');
    } 
    // Check if data comes as inputProps (legacy format)
    else if (body.inputProps) {
      inputProps = body.inputProps;
      console.log('📊 Using inputProps from request body');
    }
    // Use default values if no props provided
    else {
      inputProps = {
        overlays: [],
        aspectRatio: { width: 16, height: 9 },
        durationInFrames: 60,
      };
      console.log('📊 Using default inputProps');
    }
    
    const composition = body.id || body.composition || "Main";
    
    console.log('⚡ Starting Remotion Lambda render...');
    console.log('📊 Render parameters:', {
      composition,
      inputProps,
      functionName,
      region,
      serveUrl
    });
    
    // Call Remotion Lambda render
    const result: RenderMediaOnLambdaOutput = await renderMediaOnLambda({
      codec: LAMBDA_CONFIG.CODEC,
      functionName,
      region,
      serveUrl,
      composition,
      inputProps,
      framesPerLambda: LAMBDA_CONFIG.FRAMES_PER_LAMBDA,
      downloadBehavior: {
        type: "download",
        fileName: "video.mp4",
      },
      maxRetries: LAMBDA_CONFIG.MAX_RETRIES,
      everyNthFrame: 1,
      logLevel: 'verbose', // Enable verbose logging for debugging
    });
    
    console.log('✅ Remotion Lambda render completed:', {
      renderId: result.renderId,
      bucketName: result.bucketName,
      outputFile: result.outputFile,
      cloudWatchLogs: result.cloudWatchLogs
    });
    
    return NextResponse.json({
      success: true,
      message: 'Remotion Lambda render completed successfully',
      renderId: result.renderId,
      bucketName: result.bucketName,
      outputFile: result.outputFile,
      cloudWatchLogs: result.cloudWatchLogs,
      renderType: 'remotion-lambda',
      timestamp: new Date().toISOString(),
      result
    });
    
  } catch (error: any) {
    console.error('❌ Remotion Lambda render failed:', error);
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      name: error.name,
      functionName: process.env.REMOTION_LAMBDA_FUNCTION_NAME || process.env.AWS_LAMBDA_FUNCTION_NAME,
      region: process.env.REMOTION_AWS_REGION || process.env.AWS_REGION,
      serveUrl: process.env.REMOTION_SERVE_URL || process.env.SITE_NAME,
      hasCredentials: !!(
        (process.env.REMOTION_AWS_ACCESS_KEY_ID || process.env.AWS_ACCESS_KEY_ID) &&
        (process.env.REMOTION_AWS_SECRET_ACCESS_KEY || process.env.AWS_SECRET_ACCESS_KEY)
      )
    });
    
    // Fallback to simple render if Remotion Lambda fails
    console.log('🔄 Falling back to simple render...');
    
    try {
      // Call simple render API as fallback (body already parsed above)
      const simpleRenderResponse = await fetch(`${request.nextUrl.origin}/api/simple-render`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body)
      });
      
      if (simpleRenderResponse.ok) {
        const simpleResult = await simpleRenderResponse.json();
        console.log('✅ Fallback simple render completed:', simpleResult);
        
        return NextResponse.json({
          ...simpleResult,
          renderType: 'simple-fallback',
          fallbackReason: 'Remotion Lambda failed',
          originalError: error.message
        }, { status: 200 });
      } else {
        const errorText = await simpleRenderResponse.text();
        throw new Error(`Simple render fallback failed: ${simpleRenderResponse.status} - ${errorText}`);
      }
    } catch (fallbackError: any) {
      console.error('❌ Fallback render also failed:', fallbackError);
      
      return NextResponse.json({
        success: false,
        error: error.message,
        fallbackError: fallbackError.message,
        details: 'Both Remotion Lambda and fallback render failed',
        troubleshooting: {
          checkLambdaFunction: 'Verify Remotion Lambda function exists and is deployed',
          checkCredentials: 'Verify REMOTION_AWS_* credentials in environment variables',
          checkServeUrl: 'Verify REMOTION_SERVE_URL is set correctly',
          functionName: process.env.REMOTION_LAMBDA_FUNCTION_NAME || process.env.AWS_LAMBDA_FUNCTION_NAME || 'NOT_SET',
          region: process.env.REMOTION_AWS_REGION || process.env.AWS_REGION,
          serveUrl: process.env.REMOTION_SERVE_URL || process.env.SITE_NAME,
          hasCredentials: !!(
            (process.env.REMOTION_AWS_ACCESS_KEY_ID || process.env.AWS_ACCESS_KEY_ID) &&
            (process.env.REMOTION_AWS_SECRET_ACCESS_KEY || process.env.AWS_SECRET_ACCESS_KEY)
          ),
          usingRemotionPrefix: {
            credentials: !!process.env.REMOTION_AWS_ACCESS_KEY_ID,
            region: !!process.env.REMOTION_AWS_REGION,
            functionName: !!process.env.REMOTION_LAMBDA_FUNCTION_NAME,
            serveUrl: !!process.env.REMOTION_SERVE_URL
          }
        }
      }, { status: 500 });
    }
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'Remotion Lambda render endpoint',
    status: 'ready',
    timestamp: new Date().toISOString(),
    configuration: {
      functionName: process.env.REMOTION_LAMBDA_FUNCTION_NAME || process.env.AWS_LAMBDA_FUNCTION_NAME || 'NOT_SET',
      region: process.env.REMOTION_AWS_REGION || process.env.AWS_REGION || 'us-east-1',
      serveUrl: process.env.REMOTION_SERVE_URL || process.env.SITE_NAME || 'NOT_SET',
      hasCredentials: !!(
        (process.env.REMOTION_AWS_ACCESS_KEY_ID || process.env.AWS_ACCESS_KEY_ID) &&
        (process.env.REMOTION_AWS_SECRET_ACCESS_KEY || process.env.AWS_SECRET_ACCESS_KEY)
      ),
      usingRemotionPrefix: {
        credentials: !!process.env.REMOTION_AWS_ACCESS_KEY_ID,
        region: !!process.env.REMOTION_AWS_REGION,
        functionName: !!process.env.REMOTION_LAMBDA_FUNCTION_NAME,
        serveUrl: !!process.env.REMOTION_SERVE_URL
      }
    }
  });
}

