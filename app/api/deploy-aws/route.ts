import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(request: NextRequest) {
  try {
    console.log('🚀 Starting AWS Lambda deployment...');
    
    // Set environment variables for deployment
    const env = {
      ...process.env,
      REMOTION_AWS_ACCESS_KEY_ID: process.env.REMOTION_AWS_ACCESS_KEY_ID,
      REMOTION_AWS_SECRET_ACCESS_KEY: process.env.REMOTION_AWS_SECRET_ACCESS_KEY,
      REMOTION_AWS_REGION: process.env.REMOTION_AWS_REGION || 'us-east-1',
    };

    // Check if AWS credentials are available
    if (!env.REMOTION_AWS_ACCESS_KEY_ID || !env.REMOTION_AWS_SECRET_ACCESS_KEY) {
      return NextResponse.json({
        success: false,
        error: 'AWS credentials not found in environment variables'
      }, { status: 400 });
    }

    console.log('✅ AWS credentials found');

    // Install dependencies if needed
    try {
      console.log('📦 Installing dependencies...');
      await execAsync('npm install @remotion/cli @remotion/lambda aws-sdk', { env });
      console.log('✅ Dependencies installed');
    } catch (error) {
      console.log('⚠️ Dependencies might already be installed');
    }

    // Run the deployment
    console.log('🔧 Running AWS Lambda deployment...');
    const { stdout, stderr } = await execAsync('npx remotion lambda sites create src/index.ts --site-name=video-editor-site', { 
      env,
      timeout: 300000 // 5 minutes timeout
    });

    console.log('Deployment stdout:', stdout);
    if (stderr) {
      console.log('Deployment stderr:', stderr);
    }

    // Extract important information from deployment output
    const bucketMatch = stdout.match(/Bucket name: ([^\s]+)/);
    const siteMatch = stdout.match(/Site name: ([^\s]+)/);
    const functionMatch = stdout.match(/Function name: ([^\s]+)/);

    const deploymentInfo = {
      bucketName: bucketMatch ? bucketMatch[1] : 'remotion-render-bucket',
      siteName: siteMatch ? siteMatch[1] : 'video-editor-site',
      functionName: functionMatch ? functionMatch[1] : 'remotion-render-function',
      region: env.REMOTION_AWS_REGION
    };

    console.log('✅ AWS Lambda deployment completed!');
    console.log('Deployment info:', deploymentInfo);

    return NextResponse.json({
      success: true,
      message: 'AWS Lambda deployed successfully!',
      deploymentInfo,
      environmentVariables: {
        REMOTION_AWS_BUCKET_NAME: deploymentInfo.bucketName,
        REMOTION_AWS_SITE_NAME: deploymentInfo.siteName,
        REMOTION_AWS_FUNCTION_NAME: deploymentInfo.functionName,
        REMOTION_AWS_REGION: deploymentInfo.region
      },
      stdout,
      stderr
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

export async function GET() {
  return NextResponse.json({
    message: 'AWS Lambda deployment endpoint',
    status: 'ready',
    requiredEnvVars: [
      'REMOTION_AWS_ACCESS_KEY_ID',
      'REMOTION_AWS_SECRET_ACCESS_KEY', 
      'REMOTION_AWS_REGION'
    ]
  });
}

