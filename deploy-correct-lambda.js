const { deployFunction } = require('@remotion/lambda');

async function deployCorrectLambda() {
  try {
    console.log('Deploying correct Remotion Lambda function...');
    
    const result = await deployFunction({
      region: 'us-east-1',
      memorySizeInMb: 2048,
      diskSizeInMb: 2048,
      timeoutInSeconds: 120,
      createCloudWatchLogGroup: true,
      architecture: 'x86_64'
    });
    
    console.log('✅ Lambda function deployed successfully!');
    console.log('Function name:', result.functionName);
    console.log('Function ARN:', result.functionArn);
    
    return result;
  } catch (error) {
    console.error('❌ Error deploying Lambda function:', error);
    throw error;
  }
}

deployCorrectLambda()
  .then(result => {
    console.log('\n🎉 SUCCESS! Use this function name in Vercel:');
    console.log('REMOTION_LAMBDA_FUNCTION_NAME =', result.functionName);
  })
  .catch(error => {
    console.error('💥 FAILED:', error.message);
    process.exit(1);
  });
