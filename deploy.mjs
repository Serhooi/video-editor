/**
 * AWS Lambda deployment script for Remotion video rendering
 * Run with: npm run deploy
 */

import {
	deployFunction,
	deploySite,
	getOrCreateBucket,
	getFunctions,
	getSites
} from "@remotion/lambda";
import { lambdaConfig, bucketConfig, siteConfig } from "./config.mjs";
import dotenv from "dotenv";

// Load environment variables
dotenv.config({ path: ".env.local" });

const REGION = process.env.REMOTION_AWS_REGION || "us-east-1";
const ACCESS_KEY_ID = process.env.REMOTION_AWS_ACCESS_KEY_ID;
const SECRET_ACCESS_KEY = process.env.REMOTION_AWS_SECRET_ACCESS_KEY;

if (!ACCESS_KEY_ID || !SECRET_ACCESS_KEY) {
	console.error("❌ Missing AWS credentials!");
	console.error("Please set REMOTION_AWS_ACCESS_KEY_ID and REMOTION_AWS_SECRET_ACCESS_KEY");
	process.exit(1);
}

console.log("🚀 Starting AWS Lambda deployment...");

async function deployAll() {
	try {
		// Step 1: Create S3 bucket
		console.log("📦 Creating S3 bucket...");
		const bucket = await getOrCreateBucket({
			region: REGION,
			bucketName: bucketConfig.bucketName
		});
		console.log(`✅ S3 bucket ready: ${bucket.bucketName}`);

		// Step 2: Deploy Lambda function
		console.log("⚡ Deploying Lambda function...");
		const existingFunctions = await getFunctions({
			region: REGION,
			compatibleOnly: false
		});
		
		const existingFunction = existingFunctions.find(
			fn => fn.functionName === lambdaConfig.functionName
		);

		let functionInfo;
		if (existingFunction) {
			console.log("🔄 Updating existing Lambda function...");
			functionInfo = existingFunction;
		} else {
			console.log("🆕 Creating new Lambda function...");
			functionInfo = await deployFunction({
				region: REGION,
				functionName: lambdaConfig.functionName,
				memorySize: lambdaConfig.memorySize,
				timeout: lambdaConfig.timeout,
				diskSizeInMb: lambdaConfig.diskSizeInMb,
				architecture: lambdaConfig.architecture
			});
		}
		console.log(`✅ Lambda function ready: ${functionInfo.functionName}`);

		// Step 3: Deploy Remotion site
		console.log("🌐 Deploying Remotion site...");
		const existingSites = await getSites({
			region: REGION
		});
		
		const existingSite = existingSites.sites.find(
			site => site.id === siteConfig.siteName
		);

		let siteInfo;
		if (existingSite) {
			console.log("🔄 Site already exists, using existing...");
			siteInfo = existingSite;
		} else {
			console.log("🆕 Creating new Remotion site...");
			siteInfo = await deploySite({
				region: REGION,
				bucketName: bucketConfig.bucketName,
				siteName: siteConfig.siteName,
				entryPoint: "./src/index.ts",
				options: {
					onBundleProgress: (progress) => {
						console.log(`📦 Bundling: ${Math.round(progress * 100)}%`);
					},
					onUploadProgress: (progress) => {
						console.log(`⬆️ Uploading: ${Math.round(progress * 100)}%`);
					}
				}
			});
		}
		console.log(`✅ Remotion site ready: ${siteInfo.id}`);

		// Step 4: Display results
		console.log("\n🎉 DEPLOYMENT SUCCESSFUL!");
		console.log("\n📋 Add these environment variables to Vercel:");
		console.log(`REMOTION_AWS_BUCKET_NAME=${bucket.bucketName}`);
		console.log(`REMOTION_AWS_FUNCTION_NAME=${functionInfo.functionName}`);
		console.log(`REMOTION_AWS_SITE_NAME=${siteInfo.id}`);
		console.log(`REMOTION_AWS_REGION=${REGION}`);
		
		console.log("\n🔧 Your AWS Lambda setup is complete!");
		console.log("💡 Don't forget to add these variables to Vercel and redeploy!");

	} catch (error) {
		console.error("❌ Deployment failed:", error);
		process.exit(1);
	}
}

deployAll();

