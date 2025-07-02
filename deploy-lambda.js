const { deployFunction } = require('@remotion/lambda');

async function deployLambdaFunction() {
  try {
    console.log('🚀 Starting Lambda function deployment...');
    
    const result = await deployFunction({
      region: 'us-east-1',
      timeoutInSeconds: 120,
      memorySizeInMb: 2048,
      createCloudWatchLogGroup: true,
      architecture: 'arm64'
    });
    
    console.log('✅ Lambda function deployed successfully!');
    console.log('Function Name:', result.functionName);
    console.log('Function ARN:', result.functionArn);
    
    return result;
  } catch (error) {
    console.error('❌ Lambda deployment failed:', error);
    throw error;
  }
}

deployLambdaFunction()
  .then(result => {
    console.log('\n🎯 REMOTION_LAMBDA_FUNCTION_NAME =', result.functionName);
    process.exit(0);
  })
  .catch(error => {
    console.error('Deployment failed:', error.message);
    process.exit(1);
  });
