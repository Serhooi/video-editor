import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    console.log('🎬 Starting AWS Lambda render...');
    
    const body = await request.json();
    console.log('Render request:', body);

    // Check if AWS credentials and function name are available
    const accessKeyId = process.env.REMOTION_AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.REMOTION_AWS_SECRET_ACCESS_KEY;
    const region = process.env.REMOTION_AWS_REGION || 'us-east-1';
    const functionName = process.env.REMOTION_AWS_FUNCTION_NAME;

    if (!accessKeyId || !secretAccessKey) {
      return NextResponse.json({
        success: false,
        error: 'AWS credentials not found in environment variables'
      }, { status: 400 });
    }

    if (!functionName) {
      return NextResponse.json({
        success: false,
        error: 'AWS Lambda function name not found. Please deploy AWS Lambda first.'
      }, { status: 400 });
    }

    console.log('✅ AWS credentials and function name found');

    // Import AWS SDK dynamically
    const AWS = await import('aws-sdk');
    
    // Configure AWS
    AWS.config.update({
      accessKeyId,
      secretAccessKey,
      region
    });

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
      
      try {
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
      } catch (parseError) {
        console.error('❌ Failed to parse Lambda response:', parseError);
        throw new Error(`Failed to parse Lambda response: ${parseError.message}`);
      }
    } else {
      const errorMessage = lambdaResult.FunctionError 
        ? `Lambda function error: ${lambdaResult.FunctionError}`
        : `Lambda invocation failed with status: ${lambdaResult.StatusCode}`;
      throw new Error(errorMessage);
    }

  } catch (error: any) {
    console.error('❌ AWS Lambda render failed:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      details: 'AWS Lambda render process failed'
    }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    message: 'AWS Lambda render endpoint',
    status: 'ready',
    description: 'Video render using AWS Lambda function',
    requiredEnvVars: [
      'REMOTION_AWS_ACCESS_KEY_ID',
      'REMOTION_AWS_SECRET_ACCESS_KEY',
      'REMOTION_AWS_REGION',
      'REMOTION_AWS_FUNCTION_NAME'
    ]
  });
}

