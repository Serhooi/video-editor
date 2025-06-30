import { ScrollArea } from "@/components/ui/scroll-area";
import { MUSIC } from "../data/music";
import { dispatch, ADD_ITEMS } from "@/lib/events";
import { generateId } from "@/lib/timeline";
import { IAudio } from "@/lib/types";
import React, { useState } from "react";
import { useIsDraggingOverTimeline } from "../hooks/is-dragging-over-timeline";
import Draggable from "@/components/shared/draggable";
import { Music as MusicIcon } from "lucide-react";

export const Music = () => {
  const isDraggingOverTimeline = useIsDraggingOverTimeline();
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  const handleAddMusic = (payload: Partial<IAudio>) => {
    const id = generateId();
    dispatch(ADD_ITEMS, {
      payload: {
        trackItems: [
          {
            id,
            type: "audio",
            display: {
              from: 0,
              to: 30000, // 30 seconds default
            },
            details: {
              src: payload.details?.src,
            },
            metadata: payload.metadata || {},
          },
        ],
      },
    });
    console.log('Music added:', payload);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setUploadedFiles(files);
    
    files.forEach((file) => {
      // Create object URL for preview
      const objectUrl = URL.createObjectURL(file);
      
      // Add music to timeline
      handleAddMusic({
        id: generateId(),
        details: {
          src: objectUrl,
        },
        metadata: {
          fileName: file.name,
          genre: "Uploaded",
        },
      } as unknown as Partial<IAudio>);
    });
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="text-gray-800 flex h-12 flex-none items-center px-4 text-sm font-medium">
        Music
      </div>
      <ScrollArea className="flex-1 h-[calc(100vh-200px)]">
        <div className="px-4 space-y-4">
          {/* File Upload Section */}
          <div className="mb-4">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <MusicIcon className="w-8 h-8 mb-4 text-gray-500" />
                <p className="mb-2 text-sm text-gray-500">
                  <span className="font-semibold">Click to upload</span> or drag and drop
                </p>
                <p className="text-xs text-gray-500">MP3, WAV, OGG, M4A, AAC</p>
              </div>
              <input
                type="file"
                className="hidden"
                accept=".mp3,.wav,.ogg,.m4a,.aac"
                multiple
                onChange={handleFileUpload}
              />
            </label>
          </div>
          
          {/* Music Library */}
          <div className="space-y-2">
            {MUSIC.map((music, index) => {
              return (
                <MusicItem
                  key={index}
                  music={music}
                  shouldDisplayPreview={!isDraggingOverTimeline}
                  handleAddMusic={handleAddMusic}
                />
              );
            })}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
};

const MusicItem = ({
  handleAddMusic,
  music,
  shouldDisplayPreview,
}: {
  handleAddMusic: (payload: Partial<IAudio>) => void;
  music: Partial<IAudio>;
  shouldDisplayPreview: boolean;
}) => {
  return (
    <Draggable
      data={music}
      renderCustomPreview={
        <div className="flex items-center gap-2 bg-white p-2 rounded shadow-lg">
          <MusicIcon className="w-4 h-4" />
          <span className="text-sm">{music.metadata?.fileName || "Music"}</span>
        </div>
      }
      shouldDisplayPreview={shouldDisplayPreview}
    >
      <div
        onClick={() =>
          handleAddMusic({
            id: generateId(),
            details: {
              src: music.details!.src,
            },
            metadata: music.metadata,
          } as unknown as IAudio)
        }
        className="flex items-center gap-3 p-3 rounded-md bg-white hover:bg-gray-50 cursor-pointer transition-colors border border-gray-200"
      >
        <div className="flex-shrink-0">
          <MusicIcon className="w-6 h-6 text-blue-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {music.metadata?.fileName || "Music Track"}
          </p>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>{music.metadata?.duration || "Unknown"}</span>
            {music.metadata?.genre && (
              <>
                <span>•</span>
                <span>{music.metadata.genre}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </Draggable>
  );
};

