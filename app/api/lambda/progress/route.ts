import { NextRequest, NextResponse } from 'next/server';
import { AwsRegion, getRenderProgress } from "@remotion/lambda/client";
import { LAMBDA_FUNCTION_NAME, REGION } from "@/lib/constants";

/**
 * GET endpoint handler for checking render progress
 * Following official Remotion Lambda documentation
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const renderId = searchParams.get('renderId');
    const bucketName = searchParams.get('bucketName');
    
    if (!renderId || !bucketName) {
      return NextResponse.json({
        success: false,
        error: 'Missing renderId or bucketName parameters'
      }, { status: 400 });
    }
    
    console.log('🔍 Checking render progress:', { renderId, bucketName });
    
    // Check render progress
    const progress = await getRenderProgress({
      renderId,
      bucketName,
      functionName: LAMBDA_FUNCTION_NAME,
      region: REGION as AwsRegion,
    });
    
    console.log('📊 Render progress:', progress);
    
    return NextResponse.json({
      success: true,
      progress,
      renderId,
      bucketName
    });
    
  } catch (error: any) {
    console.error('❌ Failed to get render progress:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      details: 'Failed to get render progress'
    }, { status: 500 });
  }
}

/**
 * POST endpoint handler for checking render progress (alternative method)
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { renderId, bucketName } = body;
    
    if (!renderId || !bucketName) {
      return NextResponse.json({
        success: false,
        error: 'Missing renderId or bucketName in request body'
      }, { status: 400 });
    }
    
    console.log('🔍 Checking render progress (POST):', { renderId, bucketName });
    
    // Check render progress
    const progress = await getRenderProgress({
      renderId,
      bucketName,
      functionName: LAMBDA_FUNCTION_NAME,
      region: REGION as AwsRegion,
    });
    
    console.log('📊 Render progress:', progress);
    
    return NextResponse.json({
      success: true,
      progress,
      renderId,
      bucketName
    });
    
  } catch (error: any) {
    console.error('❌ Failed to get render progress:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      details: 'Failed to get render progress'
    }, { status: 500 });
  }
}

