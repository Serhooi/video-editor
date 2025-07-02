/**
 * Video render API endpoint using AWS Lambda
 * Handles video rendering requests via Remotion Lambda
 */

import { NextRequest, NextResponse } from "next/server";
import { renderMediaOnLambda } from "@remotion/lambda/client";

const REGION = process.env.REMOTION_AWS_REGION || "us-east-1";
const FUNCTION_NAME = process.env.REMOTION_AWS_FUNCTION_NAME;
const SITE_NAME = process.env.REMOTION_AWS_SITE_NAME;
const BUCKET_NAME = process.env.REMOTION_AWS_BUCKET_NAME;

export async function POST(request: NextRequest) {
	try {
		console.log("🎬 Starting video render request...");

		// Validate AWS configuration
		if (!FUNCTION_NAME || !SITE_NAME || !BUCKET_NAME) {
			console.error("❌ Missing AWS Lambda configuration");
			return NextResponse.json({
				type: "error",
				error: "AWS Lambda not configured. Please check environment variables."
			}, { status: 500 });
		}

		// Parse request body
		const body = await request.json();
		console.log("📋 Render request:", body);

		// Extract render parameters
		const {
			composition = "VideoEditor",
			title = "Sample Video",
			subtitle = "Created with Video Editor",
			backgroundColor = "#000000",
			textColor = "#ffffff",
			backgroundImage,
			logo
		} = body;

		// Generate unique render ID
		const renderId = `render-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
		
		console.log(`🚀 Starting Lambda render with ID: ${renderId}`);

		// Start render on AWS Lambda
		const renderResponse = await renderMediaOnLambda({
			region: REGION,
			functionName: FUNCTION_NAME,
			serveUrl: SITE_NAME,
			composition,
			inputProps: {
				title,
				subtitle,
				backgroundColor,
				textColor,
				backgroundImage,
				logo
			},
			codec: "h264",
			imageFormat: "jpeg",
			maxRetries: 1,
			privacy: "public",
			outName: `${renderId}.mp4`,
			timeoutInMilliseconds: 120000, // 2 minutes timeout
			downloadBehavior: {
				type: "download",
				fileName: `video-${renderId}.mp4`
			}
		});

		console.log("✅ Lambda render started:", renderResponse.renderId);

		// Return render ID for progress tracking
		return NextResponse.json({
			type: "success",
			renderId: renderResponse.renderId,
			bucketName: renderResponse.bucketName,
			message: "Render started successfully"
		});

	} catch (error) {
		console.error("❌ Render failed:", error);
		
		// Handle specific AWS errors
		if (error instanceof Error) {
			if (error.message.includes("AccessDenied")) {
				return NextResponse.json({
					type: "error",
					error: "AWS access denied. Please check your credentials."
				}, { status: 403 });
			}
			
			if (error.message.includes("FunctionNotFound")) {
				return NextResponse.json({
					type: "error",
					error: "Lambda function not found. Please deploy the function first."
				}, { status: 404 });
			}
		}

		return NextResponse.json({
			type: "error",
			error: error instanceof Error ? error.message : "Unknown render error"
		}, { status: 500 });
	}
}

// Handle OPTIONS for CORS
export async function OPTIONS() {
	return new NextResponse(null, {
		status: 200,
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Methods": "POST, OPTIONS",
			"Access-Control-Allow-Headers": "Content-Type",
		},
	});
}

