import React, { useState, useEffect } from 'react';
import { dispatch, DRAG_START, DRAG_END } from './events';

interface TimelineItem {
  id: string;
  type: string;
  name?: string;
  kind?: string;
  duration?: number;
  x: number;
  y: number;
}

const Timeline: React.FC = () => {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!isDragOver) {
      setIsDragOver(true);
      dispatch(DRAG_START, {});
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    dispatch(DRAG_END, {});
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    dispatch(DRAG_END, {});

    try {
      // Get all data transfer types
      const types = Array.from(e.dataTransfer.types);
      console.log('Available data types:', types);

      // Try to find JSON data
      let droppedData = null;
      for (const type of types) {
        try {
          const data = e.dataTransfer.getData(type);
          console.log(`Data for type "${type}":`, data);
          
          // Try to parse as JSON
          if (data) {
            try {
              droppedData = JSON.parse(data);
              console.log('Parsed JSON data:', droppedData);
              break;
            } catch {
              // Not JSON, continue
            }
          }
        } catch (error) {
          console.log(`Error getting data for type "${type}":`, error);
        }
      }

      if (droppedData) {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const newItem: TimelineItem = {
          ...droppedData,
          x,
          y,
        };

        setItems(prev => [...prev, newItem]);
        console.log('Added item to timeline:', newItem);
        
        // Handle specific item types
        if (droppedData.type === 'transition') {
          console.log('Adding transition to timeline:', droppedData);
          // You can dispatch an event here if needed
        } else if (droppedData.type === 'audio') {
          console.log('Adding audio to timeline:', droppedData);
          // You can dispatch an event here if needed
        }
      } else {
        console.log('No valid data found in drop event');
      }
    } catch (error) {
      console.error('Error handling drop:', error);
    }
  };

  // Clean up drag state when component unmounts
  useEffect(() => {
    return () => {
      if (isDragOver) {
        dispatch(DRAG_END, {});
      }
    };
  }, [isDragOver]);

  return (
    <div className="flex-1 p-4">
      <h2 className="text-xl font-bold mb-4">Timeline</h2>
      <div
        className={`min-h-[300px] border-2 border-dashed rounded-lg p-4 relative ${
          isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {items.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            Drag transitions and music here
          </div>
        ) : (
          items.map((item, index) => (
            <div
              key={index}
              className="absolute bg-blue-100 border border-blue-300 rounded px-2 py-1 text-sm"
              style={{ left: item.x, top: item.y }}
            >
              {item.type === 'transition' ? (
                <span>🎬 {item.kind} ({item.duration}s)</span>
              ) : item.type === 'audio' ? (
                <span>🎵 {item.name || item.metadata?.fileName || "Audio"}</span>
              ) : (
                <span>{item.type}: {item.id}</span>
              )}
            </div>
          ))
        )}
      </div>
      
      {items.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold mb-2">Timeline Items:</h3>
          <ul className="space-y-1">
            {items.map((item, index) => (
              <li key={index} className="text-sm bg-gray-100 p-2 rounded">
                {JSON.stringify(item, null, 2)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default Timeline;

