/**
 * Video render progress API endpoint
 * Tracks AWS Lambda render progress and returns results
 */

import { NextRequest, NextResponse } from "next/server";
import { getRenderProgress } from "@remotion/lambda/client";

const REGION = process.env.REMOTION_AWS_REGION || "us-east-1";
const BUCKET_NAME = process.env.REMOTION_AWS_BUCKET_NAME;

export async function GET(request: NextRequest) {
	try {
		const { searchParams } = new URL(request.url);
		const renderId = searchParams.get("renderId");

		if (!renderId) {
			return NextResponse.json({
				type: "error",
				error: "Missing renderId parameter"
			}, { status: 400 });
		}

		console.log(`📊 Checking progress for render: ${renderId}`);

		// Get render progress from AWS Lambda
		const progress = await getRenderProgress({
			renderId,
			bucketName: BUCKET_NAME!,
			region: REGION
		});

		console.log(`📈 Render progress:`, progress);

		// Handle different render states
		switch (progress.type) {
			case "success":
				console.log(`✅ Render completed: ${progress.outputFile}`);
				return NextResponse.json({
					type: "success",
					status: "completed",
					progress: 100,
					videoUrl: progress.outputFile,
					outputFile: progress.outputFile,
					renderTime: progress.renderMetadata?.totalRenderTime || 0
				});

			case "progress":
				const progressPercent = Math.round(progress.progress * 100);
				console.log(`⏳ Render in progress: ${progressPercent}%`);
				return NextResponse.json({
					type: "progress",
					status: "rendering",
					progress: progressPercent,
					message: `Rendering video... ${progressPercent}%`
				});

			case "error":
				console.error(`❌ Render failed:`, progress.errors);
				return NextResponse.json({
					type: "error",
					status: "failed",
					error: progress.errors.join(", "),
					message: "Render failed. Please try again."
				}, { status: 500 });

			default:
				console.log(`🔄 Render status: ${progress.type}`);
				return NextResponse.json({
					type: "progress",
					status: "processing",
					progress: 0,
					message: "Initializing render..."
				});
		}

	} catch (error) {
		console.error("❌ Progress check failed:", error);
		
		// Handle specific AWS errors
		if (error instanceof Error) {
			if (error.message.includes("RenderNotFound")) {
				return NextResponse.json({
					type: "error",
					error: "Render not found. It may have expired or been deleted."
				}, { status: 404 });
			}
			
			if (error.message.includes("AccessDenied")) {
				return NextResponse.json({
					type: "error",
					error: "AWS access denied. Please check your credentials."
				}, { status: 403 });
			}
		}

		return NextResponse.json({
			type: "error",
			error: error instanceof Error ? error.message : "Unknown progress error"
		}, { status: 500 });
	}
}

// Handle OPTIONS for CORS
export async function OPTIONS() {
	return new NextResponse(null, {
		status: 200,
		headers: {
			"Access-Control-Allow-Origin": "*",
			"Access-Control-Allow-Methods": "GET, OPTIONS",
			"Access-Control-Allow-Headers": "Content-Type",
		},
	});
}

