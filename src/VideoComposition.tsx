/**
 * Main Video Composition for Remotion rendering
 * Handles text, images, and animations
 */

import React from "react";
import {
	AbsoluteFill,
	interpolate,
	spring,
	useCurrentFrame,
	useVideoConfig,
	Img,
	staticFile
} from "remotion";

export interface VideoCompositionProps {
	title: string;
	subtitle?: string;
	backgroundColor: string;
	textColor: string;
	backgroundImage?: string;
	logo?: string;
}

export const VideoComposition: React.FC<VideoCompositionProps> = ({
	title,
	subtitle,
	backgroundColor,
	textColor,
	backgroundImage,
	logo
}) => {
	const frame = useCurrentFrame();
	const { fps, durationInFrames, width, height } = useVideoConfig();

	// Animation for title entrance
	const titleProgress = spring({
		frame: frame - 10,
		fps,
		config: {
			damping: 100,
			stiffness: 200,
			mass: 0.5
		}
	});

	// Animation for subtitle entrance
	const subtitleProgress = spring({
		frame: frame - 30,
		fps,
		config: {
			damping: 100,
			stiffness: 200,
			mass: 0.5
		}
	});

	// Scale animation for the entire composition
	const scale = interpolate(
		frame,
		[0, 30, durationInFrames - 30, durationInFrames],
		[0.8, 1, 1, 1.1],
		{
			extrapolateLeft: "clamp",
			extrapolateRight: "clamp"
		}
	);

	// Opacity animation for fade in/out
	const opacity = interpolate(
		frame,
		[0, 30, durationInFrames - 30, durationInFrames],
		[0, 1, 1, 0],
		{
			extrapolateLeft: "clamp",
			extrapolateRight: "clamp"
		}
	);

	return (
		<AbsoluteFill
			style={{
				backgroundColor,
				transform: `scale(${scale})`,
				opacity
			}}
		>
			{/* Background Image */}
			{backgroundImage && (
				<AbsoluteFill>
					<Img
						src={backgroundImage}
						style={{
							width: "100%",
							height: "100%",
							objectFit: "cover",
							opacity: 0.3
						}}
					/>
				</AbsoluteFill>
			)}

			{/* Logo */}
			{logo && (
				<div
					style={{
						position: "absolute",
						top: 50,
						left: 50,
						zIndex: 10
					}}
				>
					<Img
						src={logo}
						style={{
							width: 100,
							height: 100,
							objectFit: "contain"
						}}
					/>
				</div>
			)}

			{/* Main Content */}
			<AbsoluteFill
				style={{
					display: "flex",
					flexDirection: "column",
					justifyContent: "center",
					alignItems: "center",
					padding: 100,
					textAlign: "center"
				}}
			>
				{/* Title */}
				<div
					style={{
						fontSize: Math.min(width / 15, 120),
						fontWeight: "bold",
						color: textColor,
						marginBottom: 40,
						transform: `translateY(${(1 - titleProgress) * 100}px)`,
						opacity: titleProgress,
						textShadow: "2px 2px 4px rgba(0,0,0,0.5)",
						fontFamily: "Arial, sans-serif",
						lineHeight: 1.2,
						maxWidth: "90%",
						wordWrap: "break-word"
					}}
				>
					{title}
				</div>

				{/* Subtitle */}
				{subtitle && (
					<div
						style={{
							fontSize: Math.min(width / 25, 60),
							color: textColor,
							opacity: subtitleProgress * 0.8,
							transform: `translateY(${(1 - subtitleProgress) * 50}px)`,
							textShadow: "1px 1px 2px rgba(0,0,0,0.5)",
							fontFamily: "Arial, sans-serif",
							maxWidth: "80%",
							wordWrap: "break-word"
						}}
					>
						{subtitle}
					</div>
				)}

				{/* Animated decoration */}
				<div
					style={{
						position: "absolute",
						bottom: 100,
						left: "50%",
						transform: "translateX(-50%)",
						width: interpolate(frame, [60, 120], [0, 200]),
						height: 4,
						backgroundColor: textColor,
						opacity: 0.6,
						borderRadius: 2
					}}
				/>
			</AbsoluteFill>

			{/* Demo watermark */}
			<div
				style={{
					position: "absolute",
					bottom: 20,
					right: 20,
					fontSize: 24,
					color: textColor,
					opacity: 0.5,
					fontFamily: "Arial, sans-serif"
				}}
			>
				Video Editor Pro
			</div>
		</AbsoluteFill>
	);
};

