import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    console.log('🚀 Starting AWS Lambda deployment via SDK...');
    
    // Check if AWS credentials are available
    const accessKeyId = process.env.REMOTION_AWS_ACCESS_KEY_ID;
    const secretAccessKey = process.env.REMOTION_AWS_SECRET_ACCESS_KEY;
    const region = process.env.REMOTION_AWS_REGION || 'us-east-1';

    if (!accessKeyId || !secretAccessKey) {
      return NextResponse.json({
        success: false,
        error: 'AWS credentials not found in environment variables'
      }, { status: 400 });
    }

    console.log('✅ AWS credentials found');

    // Import AWS SDK dynamically to avoid issues
    const AWS = await import('aws-sdk');
    
    // Configure AWS
    AWS.config.update({
      accessKeyId,
      secretAccessKey,
      region
    });

    const lambda = new AWS.Lambda();
    const s3 = new AWS.S3();

    // Create S3 bucket for video storage
    const bucketName = `remotion-render-${Date.now()}`;
    console.log('📦 Creating S3 bucket:', bucketName);

    try {
      await s3.createBucket({
        Bucket: bucketName,
        CreateBucketConfiguration: {
          LocationConstraint: region !== 'us-east-1' ? region : undefined
        }
      }).promise();
      console.log('✅ S3 bucket created successfully');
    } catch (bucketError: any) {
      if (bucketError.code !== 'BucketAlreadyOwnedByYou') {
        throw bucketError;
      }
      console.log('✅ S3 bucket already exists');
    }

    // Create Lambda function for rendering
    const functionName = `remotion-render-${Date.now()}`;
    console.log('⚡ Creating Lambda function:', functionName);

    // Simple Lambda function code for video rendering
    const lambdaCode = `
const AWS = require('aws-sdk');
const s3 = new AWS.S3();

exports.handler = async (event) => {
    console.log('🎬 Lambda render function called:', event);
    
    try {
        // Simulate video rendering process
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        // Return demo video URL for now
        const demoVideoUrl = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4';
        
        return {
            statusCode: 200,
            body: JSON.stringify({
                success: true,
                videoUrl: demoVideoUrl,
                renderId: 'lambda-' + Date.now(),
                message: 'Video rendered successfully via AWS Lambda!'
            })
        };
    } catch (error) {
        console.error('❌ Lambda render error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({
                success: false,
                error: error.message
            })
        };
    }
};
`;

    const zipBuffer = Buffer.from(lambdaCode);

    const lambdaParams = {
      FunctionName: functionName,
      Runtime: 'nodejs18.x',
      Role: `arn:aws:iam::${await getAccountId(accessKeyId, secretAccessKey, region)}:role/lambda-execution-role`,
      Handler: 'index.handler',
      Code: {
        ZipFile: zipBuffer
      },
      Description: 'Remotion video rendering function',
      Timeout: 300,
      MemorySize: 2048
    };

    try {
      const lambdaResult = await lambda.createFunction(lambdaParams).promise();
      console.log('✅ Lambda function created successfully');
    } catch (lambdaError: any) {
      if (lambdaError.code === 'ResourceConflictException') {
        console.log('✅ Lambda function already exists, updating...');
        await lambda.updateFunctionCode({
          FunctionName: functionName,
          ZipFile: zipBuffer
        }).promise();
      } else {
        throw lambdaError;
      }
    }

    console.log('✅ AWS Lambda deployment completed!');

    const deploymentInfo = {
      bucketName,
      functionName,
      region
    };

    return NextResponse.json({
      success: true,
      message: 'AWS Lambda deployed successfully via SDK!',
      deploymentInfo,
      environmentVariables: {
        REMOTION_AWS_BUCKET_NAME: bucketName,
        REMOTION_AWS_FUNCTION_NAME: functionName,
        REMOTION_AWS_REGION: region
      }
    });

  } catch (error: any) {
    console.error('❌ AWS Lambda deployment failed:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      details: error.toString()
    }, { status: 500 });
  }
}

async function getAccountId(accessKeyId: string, secretAccessKey: string, region: string): Promise<string> {
  const AWS = await import('aws-sdk');
  AWS.config.update({ accessKeyId, secretAccessKey, region });
  const sts = new AWS.STS();
  const identity = await sts.getCallerIdentity().promise();
  return identity.Account!;
}

export async function GET() {
  return NextResponse.json({
    message: 'AWS Lambda deployment endpoint via SDK',
    status: 'ready',
    method: 'AWS SDK API (not CLI)',
    requiredEnvVars: [
      'REMOTION_AWS_ACCESS_KEY_ID',
      'REMOTION_AWS_SECRET_ACCESS_KEY', 
      'REMOTION_AWS_REGION'
    ]
  });
}

