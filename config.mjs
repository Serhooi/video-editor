/**
 * AWS Lambda configuration for Remotion video rendering
 * Based on original react-video-editor-pro setup
 */

export const REGION = "us-east-1";
export const FUNCTION_NAME = "remotion-video-render";
export const MEMORY_SIZE = 3009; // MB - required for video rendering
export const TIMEOUT = 240; // seconds - 4 minutes max render time
export const DISK_SIZE = 2048; // MB - temporary storage for video files

export const SITE_NAME = "video-editor-site";
export const BUCKET_NAME = "remotion-video-renders";

// Lambda function configuration
export const lambdaConfig = {
	functionName: FUNCTION_NAME,
	region: REGION,
	memorySize: MEMORY_SIZE,
	timeout: TIMEOUT,
	diskSizeInMb: DISK_SIZE,
	architecture: "arm64", // Better price/performance
	runtime: "nodejs18.x"
};

// S3 bucket configuration  
export const bucketConfig = {
	bucketName: BUCKET_NAME,
	region: REGION
};

// Remotion site configuration
export const siteConfig = {
	siteName: SITE_NAME,
	region: REGION,
	bucketName: BUCKET_NAME
};

