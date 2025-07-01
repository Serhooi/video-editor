import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useEditorContext } from "../../../contexts/editor-context";
import { useTimelinePositioning } from "../../../hooks/use-timeline-positioning";
import { useTimeline } from "../../../contexts/timeline-context";
import { CaptionOverlay, OverlayType, Caption } from "../../../types";
import { CaptionSettings } from "./caption-settings";
import { AutoSubtitlesGenerator } from "./auto-subtitles-generator";
import { Upload, X, Wand2, FileText, Bot } from "lucide-react";

/**
 * Interface for word timing data from uploaded files
 * @interface WordData
 */
interface WordData {
  word: string;
  start: number;
  end: number;
  confidence: number;
}

/**
 * Interface for the structure of uploaded caption files
 * @interface WordsFileData
 */
interface WordsFileData {
  words: WordData[];
}

/**
 * Enhanced CaptionsPanel Component with AI Integration
 *
 * @component
 * @description
 * Advanced interface for managing captions in the video editor.
 * Provides functionality for:
 * - AI-powered automatic subtitle generation (Whisper + ChatGPT)
 * - Uploading caption files (.json)
 * - Manual script entry
 * - Caption generation from text
 * - Caption editing and styling
 *
 * Features:
 * - Three input methods: AI Generation, File Upload, Manual Entry
 * - Automatic speech recognition with Whisper AI
 * - Text enhancement with ChatGPT
 * - Multiple language support
 * - Customizable subtitle styles
 * - SRT export functionality
 *
 * @example
 * ```tsx
 * <CaptionsPanelWithAI />
 * ```
 */
export const CaptionsPanel: React.FC = () => {
  const [script, setScript] = useState("");
  const [isBannerVisible, setIsBannerVisible] = useState(true);
  const [activeTab, setActiveTab] = useState("ai");
  
  const {
    addOverlay,
    overlays,
    selectedOverlayId,
    durationInFrames,
    changeOverlay,
    currentFrame,
  } = useEditorContext();

  const { findNextAvailablePosition } = useTimelinePositioning();
  const { visibleRows } = useTimeline();
  const [localOverlay, setLocalOverlay] = useState<CaptionOverlay | null>(null);

  React.useEffect(() => {
    if (selectedOverlayId === null) {
      return;
    }

    const selectedOverlay = overlays.find(
      (overlay) => overlay.id === selectedOverlayId
    );

    if (selectedOverlay?.type === OverlayType.CAPTION) {
      setLocalOverlay(selectedOverlay as CaptionOverlay);
    }
  }, [selectedOverlayId, overlays]);

  /**
   * Handle AI-generated subtitles
   */
  const handleAISubtitles = (aiCaptions: any[]) => {
    // Convert AI captions to editor format
    const processedCaptions: Caption[] = aiCaptions.map((aiCaption) => ({
      text: aiCaption.text,
      startMs: (aiCaption.start / 30) * 1000, // Convert frames to ms
      endMs: (aiCaption.end / 30) * 1000,
      timestampMs: null,
      confidence: 0.95,
      words: aiCaption.text.split(' ').map((word: string, index: number) => {
        const wordDuration = ((aiCaption.end - aiCaption.start) / 30 * 1000) / aiCaption.text.split(' ').length;
        return {
          word,
          startMs: (aiCaption.start / 30) * 1000 + (index * wordDuration),
          endMs: (aiCaption.start / 30) * 1000 + ((index + 1) * wordDuration),
          confidence: 0.95,
        };
      }),
    }));

    // Calculate total duration
    const totalDurationMs = processedCaptions[processedCaptions.length - 1]?.endMs || 0;
    const calculatedDurationInFrames = Math.ceil((totalDurationMs / 1000) * 30);

    const position = findNextAvailablePosition(
      overlays,
      visibleRows,
      durationInFrames
    );

    const newCaptionOverlay: CaptionOverlay = {
      id: Date.now(),
      type: OverlayType.CAPTION,
      from: position.from,
      durationInFrames: calculatedDurationInFrames,
      captions: processedCaptions,
      left: 230,
      top: 414,
      width: 833,
      height: 269,
      rotation: 0,
      isDragging: false,
      row: position.row,
    };

    addOverlay(newCaptionOverlay);
  };

  const generateCaptions = () => {
    const sentences = script
      .split(/[.!?]+/)
      .map((sentence) => sentence.trim())
      .filter((sentence) => sentence.length > 0);

    let currentStartTime = 0;
    const wordsPerMinute = 160;
    const msPerWord = (60 * 1000) / wordsPerMinute;

    const processedCaptions: Caption[] = sentences.map((sentence) => {
      const words = sentence.split(/\s+/);
      const sentenceStartTime = currentStartTime;

      const processedWords = words.map((word, index) => ({
        word,
        startMs: sentenceStartTime + index * msPerWord,
        endMs: sentenceStartTime + (index + 1) * msPerWord,
        confidence: 0.99,
      }));

      const caption: Caption = {
        text: sentence,
        startMs: sentenceStartTime,
        endMs: sentenceStartTime + words.length * msPerWord,
        timestampMs: null,
        confidence: 0.99,
        words: processedWords,
      };

      currentStartTime = caption.endMs + 500;
      return caption;
    });

    const totalDurationMs = currentStartTime;
    const calculatedDurationInFrames = Math.ceil((totalDurationMs / 1000) * 30);

    const position = findNextAvailablePosition(
      overlays,
      visibleRows,
      durationInFrames
    );

    const newCaptionOverlay: CaptionOverlay = {
      id: Date.now(),
      type: OverlayType.CAPTION,
      from: position.from,
      durationInFrames: calculatedDurationInFrames,
      captions: processedCaptions,
      left: 230,
      top: 414,
      width: 833,
      height: 269,
      rotation: 0,
      isDragging: false,
      row: position.row,
    };

    addOverlay(newCaptionOverlay);
    setScript("");
  };

  const handleUpdateOverlay = (updatedOverlay: CaptionOverlay) => {
    setLocalOverlay(updatedOverlay);
    changeOverlay(updatedOverlay.id, updatedOverlay);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const jsonData = JSON.parse(
          e.target?.result as string
        ) as WordsFileData;

        // Group words into chunks of 5
        const processedCaptions: Caption[] = [];
        for (let i = 0; i < jsonData.words.length; i += 5) {
          const wordChunk = jsonData.words.slice(i, i + 5);
          const startMs = wordChunk[0].start * 1000;
          const endMs = wordChunk[wordChunk.length - 1].end * 1000;

          const captionText = wordChunk.map((w) => w.word).join(" ");

          processedCaptions.push({
            text: captionText,
            startMs,
            endMs,
            timestampMs: null,
            confidence:
              wordChunk.reduce((acc, w) => acc + w.confidence, 0) /
              wordChunk.length,
            words: wordChunk.map((w) => ({
              word: w.word,
              startMs: w.start * 1000,
              endMs: w.end * 1000,
              confidence: w.confidence,
            })),
          });
        }

        const totalDurationMs =
          processedCaptions[processedCaptions.length - 1].endMs;
        const calculatedDurationInFrames = Math.ceil(
          (totalDurationMs / 1000) * 30
        );

        const position = findNextAvailablePosition(
          overlays,
          visibleRows,
          durationInFrames
        );

        const newCaptionOverlay: CaptionOverlay = {
          id: Date.now(),
          type: OverlayType.CAPTION,
          from: position.from,
          durationInFrames: calculatedDurationInFrames,
          captions: processedCaptions,
          left: 230,
          top: 414,
          width: 833,
          height: 269,
          rotation: 0,
          isDragging: false,
          row: position.row,
        };

        addOverlay(newCaptionOverlay);
      } catch (error) {
        // If it's not JSON, treat it as plain text
        const text = e.target?.result;
        if (typeof text === "string") {
          setScript(text);
          setActiveTab("manual"); // Switch to manual tab
        }
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="flex flex-col gap-6 p-4 bg-white dark:bg-gray-900/40">
      {!localOverlay ? (
        <>
          <div className="space-y-4">
            <div className="flex flex-col gap-2">
              {isBannerVisible && (
                <div
                  className="relative rounded-lg bg-gradient-to-r from-blue-50/80 to-blue-50/40 dark:from-blue-900/10 dark:to-blue-800/5 
                  border border-blue-300/80 dark:border-blue-800/20 p-3 shadow-[0_1px_3px_0_rgb(0,0,0,0.05)]"
                >
                  <button
                    onClick={() => setIsBannerVisible(false)}
                    className="absolute top-1.5 right-1.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 
                      dark:hover:text-gray-300 transition-colors p-1.5 hover:bg-gray-100/70 dark:hover:bg-gray-800/70 rounded-md"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                  <div className="space-y-1.5">
                    <h3 className="text-xs font-medium text-gray-800 dark:text-gray-200 flex items-center gap-2">
                      <Bot className="h-3.5 w-3.5" />
                      AI-Powered Subtitles Available!
                    </h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400 pr-4">
                      Automatically generate subtitles from your video using Whisper AI and ChatGPT for perfect timing and formatting.
                    </p>
                  </div>
                </div>
              )}
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="ai" className="flex items-center gap-2">
                  <Wand2 className="h-4 w-4" />
                  AI Generation
                </TabsTrigger>
                <TabsTrigger value="upload" className="flex items-center gap-2">
                  <Upload className="h-4 w-4" />
                  File Upload
                </TabsTrigger>
                <TabsTrigger value="manual" className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Manual Entry
                </TabsTrigger>
              </TabsList>

              <TabsContent value="ai" className="space-y-4 mt-4">
                <AutoSubtitlesGenerator 
                  onSubtitlesGenerated={handleAISubtitles}
                />
              </TabsContent>

              <TabsContent value="upload" className="space-y-4 mt-4">
                <div className="flex flex-col gap-2">
                  <Button
                    variant="outline"
                    className="w-full border-dashed border-2 border-gray-200 dark:border-gray-700 
                    hover:border-blue-500/50 bg-gray-50/50 dark:bg-gray-800/50 
                    hover:bg-gray-100 dark:hover:bg-gray-800 h-32 
                    flex flex-col items-center justify-center gap-3 text-sm group transition-all duration-200"
                    onClick={() =>
                      document.getElementById("file-upload")?.click()
                    }
                  >
                    <Upload className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:text-blue-500 transition-colors" />
                    <div className="flex flex-col items-center space-y-1">
                      <span className="text-gray-600 dark:text-gray-300 group-hover:text-gray-800 dark:group-hover:text-gray-200 font-medium">
                        Upload Script File
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-500 text-center px-2">
                        Supported: .json, .srt, .vtt, .txt
                      </span>
                    </div>
                  </Button>
                  <input
                    id="file-upload"
                    type="file"
                    accept=".txt,.srt,.vtt,.json"
                    className="hidden"
                    onChange={handleFileUpload}
                  />
                </div>
              </TabsContent>

              <TabsContent value="manual" className="space-y-4 mt-4">
                <div className="space-y-4">
                  <Textarea
                    value={script}
                    onChange={(e) => setScript(e.target.value)}
                    placeholder="Type or paste your script here..."
                    className="min-h-[200px] bg-white dark:bg-gray-800/50 
                    border-gray-200 dark:border-gray-700 
                    text-gray-900 dark:text-gray-200 
                    placeholder:text-gray-400 dark:placeholder:text-gray-500 
                    focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 
                    transition-all rounded-lg"
                  />
                  
                  <div className="flex gap-3">
                    <Button
                      onClick={generateCaptions}
                      className="flex-1 text-white dark:text-black
                      disabled:bg-gray-200 disabled:text-gray-500 disabled:dark:bg-gray-800 
                      disabled:dark:text-gray-600 disabled:opacity-100 disabled:cursor-not-allowed 
                      transition-colors"
                      disabled={!script.trim()}
                    >
                      Generate Captions
                    </Button>
                    {script && (
                      <Button
                        variant="ghost"
                        className="text-sm text-gray-600 dark:text-gray-400 
                        hover:text-gray-700 dark:hover:text-gray-300 
                        hover:bg-gray-100/80 dark:hover:bg-gray-800/80 
                        transition-colors"
                        onClick={() => setScript("")}
                      >
                        Clear
                      </Button>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </>
      ) : (
        <CaptionSettings
          currentFrame={currentFrame}
          localOverlay={localOverlay}
          setLocalOverlay={handleUpdateOverlay}
          startFrame={localOverlay.from}
          captions={localOverlay.captions}
        />
      )}
    </div>
  );
};

