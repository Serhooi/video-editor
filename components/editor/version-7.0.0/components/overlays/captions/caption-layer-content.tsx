import React from "react";
import { useCurrentFrame } from "remotion";
import { Caption, Overlay } from "../../../types";
import { defaultCaptionStyles } from "./caption-settings";

/**
 * Props for the CaptionLayerContent component
 * @interface CaptionLayerContentProps
 * @property {Overlay} overlay - The overlay object containing timing and style information
 */
interface CaptionLayerContentProps {
  overlay: Overlay;
}

/**
 * CaptionLayerContent Component
 *
 * @component
 * @description
 * Renders animated captions in the video editor with word-by-word highlighting.
 * Features include:
 * - Word-by-word timing and animation
 * - Customizable text styles and animations
 * - Smooth transitions between words
 * - Dynamic highlighting based on current frame
 *
 * The component calculates timing for each word and applies appropriate
 * styling and animations based on the current playback position.
 *
 * @example
 * ```tsx
 * <CaptionLayerContent
 *   overlay={{
 *     captions: [...],
 *     styles: {...},
 *     // other overlay properties
 *   }}
 * />
 * ```
 */
export const CaptionLayerContent: React.FC<CaptionLayerContentProps> = ({
  overlay,
}) => {
  const frame = useCurrentFrame();
  const frameMs = (frame / 30) * 1000;
  const styles = defaultCaptionStyles;

  /**
   * Finds the current caption based on the frame timestamp
   */
  const currentCaption = overlay.captions?.find(
    (caption) => frameMs >= caption.startTime && frameMs <= caption.endTime
  );

  if (!currentCaption) return null;

  /**
   * Renders individual words with highlight animations
   * @param caption - The current caption object containing words and timing
   */
  const renderWords = (caption: Caption) => {
    return caption?.words?.map((word, index) => {
      const isHighlighted = frameMs >= word.startMs && frameMs <= word.endMs;
      const progress = isHighlighted
        ? Math.min((frameMs - word.startMs) / 300, 1)
        : 0;

      const highlightStyle =
        styles.highlightStyle || defaultCaptionStyles.highlightStyle;

      return (
        <span
          key={`${word.text}-${index}`}
          className="inline-block transition-all duration-200"
          style={{
            color: isHighlighted ? highlightStyle?.color : styles.color,
            backgroundColor: isHighlighted
              ? highlightStyle?.backgroundColor
              : "transparent",
            opacity: isHighlighted ? 1 : 0.85,
            transform: isHighlighted
              ? `scale(${
                  1 +
                  (highlightStyle?.scale
                    ? (highlightStyle.scale - 1) * progress
                    : 0.08)
                })`
              : "scale(1)",
            fontWeight: isHighlighted
              ? highlightStyle?.fontWeight || 600
              : styles.fontWeight || 400,
            textShadow: isHighlighted
              ? highlightStyle?.textShadow
              : styles.textShadow,
            padding: highlightStyle?.padding || "4px 8px",
            borderRadius: highlightStyle?.borderRadius || "4px",
            margin: "0 2px",
          }}
        >
          {word.text}
        </span>
      );
    });
  };

  return (
    <div
      className="absolute inset-0 flex items-center justify-center p-6"
      style={{
        ...styles,
        width: "100%",
        height: "100%",
        overflow: "hidden",
      }}
    >
      <div
        className="leading-relaxed tracking-wide max-w-full"
        style={{
          whiteSpace: "pre-wrap",
          width: "100%",
          maxWidth: "90%",
          textAlign: "center",
          wordBreak: "break-word",
          overflowWrap: "break-word",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          gap: "4px",
          padding: "8px",
          boxSizing: "border-box",
        }}
      >
        {renderWords(currentCaption)}
      </div>
    </div>
  );
};
