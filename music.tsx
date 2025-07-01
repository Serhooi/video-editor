import { ScrollArea } from "@/components/ui/scroll-area";
import { FileUploader } from "@/components/ui/file-uploader";
import { MUSIC } from "../data/music";
import { dispatch } from "@designcombo/events";
import { ADD_ITEMS } from "@designcombo/state";
import { generateId } from "@designcombo/timeline";
import { IAudio } from "@designcombo/types";
import React, { useState } from "react";
import { useIsDraggingOverTimeline } from "../hooks/is-dragging-over-timeline";
import Draggable from "@/components/shared/draggable";
import { Icons } from "@/components/shared/icons";

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
  };

  const handleFileUpload = (files: File[]) => {
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
      <div className="text-text-primary flex h-12 flex-none items-center px-4 text-sm font-medium">
        Music
      </div>
      <ScrollArea className="flex-1 h-[calc(100vh-200px)]">
        <div className="px-4 space-y-4">
          {/* File Upload Section */}
          <div className="mb-4">
            <FileUploader
              value={uploadedFiles}
              onValueChange={handleFileUpload}
              accept={{
                "audio/*": [".mp3", ".wav", ".ogg", ".m4a", ".aac"],
              }}
              maxSize={50 * 1024 * 1024} // 50MB for music
              maxFileCount={10}
              multiple={true}
              className="h-32"
            />
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
        <div className="flex items-center gap-2 bg-background p-2 rounded">
          <Icons.audio className="w-4 h-4" />
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
        className="flex items-center gap-3 p-3 rounded-md bg-background hover:bg-muted cursor-pointer transition-colors"
      >
        <div className="flex-shrink-0">
          <Icons.audio className="w-6 h-6 text-blue-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">
            {music.metadata?.fileName || "Music Track"}
          </p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
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

