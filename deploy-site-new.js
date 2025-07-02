const { deploySite } = require('@remotion/lambda');

async function deploySiteToS3() {
  try {
    console.log('🚀 Starting S3 site deployment...');
    
    const bucketName = 'remotionlambda-video-editor-1751486531';
    
    const result = await deploySite({
      region: 'us-east-1',
      entryPoint: './remotion/index.ts',
      bucketName: bucketName,
      siteName: 'video-editor-site'
    });
    
    console.log('✅ S3 site deployed successfully!');
    console.log('Serve URL:', result.serveUrl);
    console.log('Bucket Name:', result.bucketName);
    console.log('Site Name:', result.siteName);
    
    return result;
  } catch (error) {
    console.error('❌ S3 site deployment failed:', error);
    throw error;
  }
}

deploySiteToS3()
  .then(result => {
    console.log('\n🎯 REMOTION_SERVE_URL =', result.serveUrl);
    process.exit(0);
  })
  .catch(error => {
    console.error('Site deployment failed:', error.message);
    process.exit(1);
  });
