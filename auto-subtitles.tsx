import React, { useState, useRef } from 'react';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CaptionsIcon, Upload, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { generateCaptions } from "../utils/captions";

interface SubtitleSegment {
  start: number;
  end: number;
  text: string;
}

export const AutoSubtitles = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [subtitles, setSubtitles] = useState<SubtitleSegment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check if file is audio or video
    const isAudioVideo = file.type.startsWith('audio/') || file.type.startsWith('video/');
    if (!isAudioVideo) {
      setError('Please upload an audio or video file');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setSuccess(false);

    try {
      // Create FormData for Whisper API
      const formData = new FormData();
      formData.append('file', file);
      formData.append('model', 'whisper-1');
      formData.append('response_format', 'verbose_json');
      formData.append('timestamp_granularities[]', 'word');

      // Call OpenAI Whisper API
      const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.REACT_APP_OPENAI_API_KEY || 'your-api-key-here'}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Whisper API error: ${response.status}`);
      }

      const result = await response.json();
      
      // Process Whisper response to create subtitles
      const segments: SubtitleSegment[] = [];
      
      if (result.words && result.words.length > 0) {
        // Group words into segments (sentences or phrases)
        let currentSegment = '';
        let segmentStart = result.words[0].start;
        let segmentEnd = result.words[0].end;
        
        for (let i = 0; i < result.words.length; i++) {
          const word = result.words[i];
          currentSegment += (currentSegment ? ' ' : '') + word.word;
          segmentEnd = word.end;
          
          // End segment on punctuation or every 10 words
          const shouldEndSegment = 
            word.word.match(/[.!?]$/) || 
            (i > 0 && (i + 1) % 10 === 0) ||
            i === result.words.length - 1;
            
          if (shouldEndSegment) {
            segments.push({
              start: segmentStart,
              end: segmentEnd,
              text: currentSegment.trim()
            });
            
            if (i < result.words.length - 1) {
              segmentStart = result.words[i + 1]?.start || segmentEnd;
              currentSegment = '';
            }
          }
        }
      } else if (result.segments) {
        // Fallback to segments if words are not available
        result.segments.forEach((segment: any) => {
          segments.push({
            start: segment.start,
            end: segment.end,
            text: segment.text.trim()
          });
        });
      }

      setSubtitles(segments);
      setSuccess(true);
      
      // Generate captions for the timeline
      if (segments.length > 0) {
        const captionsInput = {
          sourceUrl: URL.createObjectURL(file),
          results: {
            main: {
              words: result.words || []
            }
          }
        };
        
        const fontInfo = {
          fontFamily: 'Arial',
          fontUrl: '',
          fontSize: 24
        };
        
        const options = {
          containerWidth: 800,
          linesPerCaption: 2,
          parentId: 'auto-generated',
          displayFrom: 0
        };
        
        // This would integrate with the timeline
        // const captions = generateCaptions(captionsInput, fontInfo, options);
        console.log('Generated subtitles:', segments);
      }
      
    } catch (err) {
      console.error('Subtitle generation error:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate subtitles');
    } finally {
      setIsProcessing(false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border/80 p-4">
        <div className="flex items-center gap-2">
          <CaptionsIcon size={20} />
          <h2 className="text-lg font-semibold">Auto Subtitles</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Generate subtitles automatically using AI
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Upload Section */}
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,video/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          
          {!isProcessing ? (
            <div>
              <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Upload Audio or Video
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                Upload an audio or video file to generate subtitles automatically
              </p>
              <Button 
                onClick={() => fileInputRef.current?.click()}
                className="bg-blue-600 hover:bg-blue-700"
              >
                Choose File
              </Button>
            </div>
          ) : (
            <div>
              <Loader2 className="mx-auto h-12 w-12 text-blue-600 animate-spin mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Generating Subtitles...
              </h3>
              <p className="text-sm text-gray-500">
                Processing your file with AI. This may take a few minutes.
              </p>
            </div>
          )}
        </div>

        {/* Status Messages */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <span className="text-sm text-green-700">
              Subtitles generated successfully! ({subtitles.length} segments)
            </span>
          </div>
        )}

        {/* Subtitles Preview */}
        {subtitles.length > 0 && (
          <div>
            <h3 className="text-md font-medium mb-3">Generated Subtitles:</h3>
            <ScrollArea className="h-64 border rounded-lg">
              <div className="p-3 space-y-2">
                {subtitles.map((subtitle, index) => (
                  <div key={index} className="border-b border-gray-100 pb-2 last:border-b-0">
                    <div className="text-xs text-gray-500 mb-1">
                      {formatTime(subtitle.start)} → {formatTime(subtitle.end)}
                    </div>
                    <div className="text-sm text-gray-900">
                      {subtitle.text}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
            
            <div className="mt-3 flex gap-2">
              <Button 
                size="sm" 
                className="bg-green-600 hover:bg-green-700"
                onClick={() => {
                  // Add subtitles to timeline
                  console.log('Adding subtitles to timeline:', subtitles);
                }}
              >
                Add to Timeline
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={() => {
                  // Download SRT file
                  const srtContent = subtitles.map((sub, index) => 
                    `${index + 1}\n${formatTime(sub.start).replace('.', ',')} --> ${formatTime(sub.end).replace('.', ',')}\n${sub.text}\n`
                  ).join('\n');
                  
                  const blob = new Blob([srtContent], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'subtitles.srt';
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                Download SRT
              </Button>
            </div>
          </div>
        )}

        {/* Instructions */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-900 mb-2">How it works:</h4>
          <ul className="text-xs text-blue-700 space-y-1">
            <li>• Upload an audio or video file</li>
            <li>• AI will automatically transcribe the speech</li>
            <li>• Subtitles are generated with precise timing</li>
            <li>• Add them to your timeline or download as SRT</li>
          </ul>
          <p className="text-xs text-blue-600 mt-2">
            <strong>Note:</strong> You need to set REACT_APP_OPENAI_API_KEY in your environment variables.
          </p>
        </div>
      </div>
    </div>
  );
};

