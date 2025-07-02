import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  console.log('🚀 AWS Lambda render request received');
  
  try {
    const body = await request.json();
    console.log('📝 Request body:', body);

    // Get AWS configuration from environment variables
    const accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
    const region = process.env.AWS_REGION || 'us-east-1';
    const functionName = process.env.AWS_LAMBDA_FUNCTION_NAME;

    console.log('🔧 AWS Configuration:', {
      hasAccessKey: !!accessKeyId,
      hasSecretKey: !!secretAccessKey,
      region,
      functionName
    });

    if (!accessKeyId || !secretAccessKey || !functionName) {
      throw new Error('Missing AWS configuration. Please check environment variables.');
    }

    // Import AWS SDK dynamically
    const AWS = await import('aws-sdk');
    
    // Configure AWS
    AWS.config.update({
      accessKeyId,
      secretAccessKey,
      region
    });

    // Initialize AWS Lambda client
    const lambda = new AWS.Lambda();

    // Invoke Lambda function for rendering
    console.log('⚡ Invoking Lambda function:', functionName);
    
    const lambdaParams = {
      FunctionName: functionName,
      Payload: JSON.stringify({
        compositionProps: body.compositionProps,
        timestamp: new Date().toISOString()
      })
    };

    const lambdaResult = await lambda.invoke(lambdaParams).promise();
    
    console.log('🔍 Lambda result:', {
      StatusCode: lambdaResult.StatusCode,
      Payload: lambdaResult.Payload?.toString(),
      FunctionError: lambdaResult.FunctionError
    });
    
    if (lambdaResult.StatusCode === 200 && lambdaResult.Payload) {
      const payloadString = lambdaResult.Payload.toString();
      
      if (!payloadString || payloadString === 'undefined' || payloadString.trim() === '') {
        throw new Error('Lambda function returned empty or undefined payload');
      }
      
      const payload = JSON.parse(payloadString);
      
      if (!payload.body) {
        throw new Error('Lambda response missing body field');
      }
      
      const result = JSON.parse(payload.body);
      
      console.log('✅ Lambda render completed:', result);
      
      return NextResponse.json({
        success: result.success,
        message: result.message,
        videoUrl: result.videoUrl,
        renderId: result.renderId,
        renderType: 'aws-lambda',
        timestamp: new Date().toISOString()
      });
    } else {
      const errorMessage = lambdaResult.FunctionError 
        ? `Lambda function error: ${lambdaResult.FunctionError}`
        : `Lambda invocation failed with status: ${lambdaResult.StatusCode}`;
      throw new Error(errorMessage);
    }

  } catch (error: any) {
    console.error('❌ AWS Lambda render failed:', error);
    console.error('Error details:', {
      message: error.message,
      stack: error.stack,
      functionName: process.env.AWS_LAMBDA_FUNCTION_NAME,
      region: process.env.AWS_REGION,
      hasCredentials: !!(process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY)
    });
    
    // Fallback to simple render if Lambda fails
    console.log('🔄 Falling back to simple render...');
    
    try {
      // Call simple render API as fallback
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
          fallbackReason: 'AWS Lambda failed',
          originalError: error.message
        });
      } else {
        throw new Error(`Simple render fallback also failed: ${simpleRenderResponse.status}`);
      }
    } catch (fallbackError: any) {
      console.error('❌ Fallback render also failed:', fallbackError);
      
      return NextResponse.json({
        success: false,
        error: error.message,
        fallbackError: fallbackError.message,
        details: 'Both AWS Lambda and fallback render failed',
        troubleshooting: {
          checkLambdaFunction: 'Verify AWS Lambda function exists and is deployed',
          checkCredentials: 'Verify AWS credentials in environment variables',
          checkPermissions: 'Verify IAM permissions for Lambda invocation',
          functionName: process.env.AWS_LAMBDA_FUNCTION_NAME || 'NOT_SET',
          region: process.env.AWS_REGION,
          hasCredentials: !!(process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY)
        }
      }, { status: 500 });
    }
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'AWS Lambda render endpoint',
    status: 'ready',
    timestamp: new Date().toISOString()
  });
}

