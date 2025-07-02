/**
 * Remotion Root component
 * Defines all available video compositions
 */

import React from "react";
import { Composition } from "remotion";
import { VideoComposition, VideoCompositionProps } from "./VideoComposition";

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="VideoEditor"
				component={VideoComposition}
				durationInFrames={300} // 10 seconds at 30fps
				fps={30}
				width={1920}
				height={1080}
				defaultProps={{
					title: "Sample Video",
					subtitle: "Created with Video Editor",
					backgroundColor: "#000000",
					textColor: "#ffffff"
				} satisfies VideoCompositionProps}
			/>
			
			<Composition
				id="ShortVideo"
				component={VideoComposition}
				durationInFrames={150} // 5 seconds at 30fps
				fps={30}
				width={1080}
				height={1920} // Vertical format for social media
				defaultProps={{
					title: "Short Video",
					subtitle: "Perfect for social media",
					backgroundColor: "#1a1a1a",
					textColor: "#ffffff"
				} satisfies VideoCompositionProps}
			/>
		</>
	);
};

