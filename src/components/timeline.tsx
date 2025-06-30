import React, { useState } from 'react';
import { dispatch, DRAG_START, DRAG_END } from '@/lib/events';

interface TimelineProps {
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({ className = '' }) => {
  const [droppedItems, setDroppedItems] = useState<any[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    try {
      const data = e.dataTransfer.getData('application/json');
      if (data) {
        const item = JSON.parse(data);
        setDroppedItems(prev => [...prev, { ...item, id: Date.now() }]);
        console.log('Item dropped on timeline:', item);
        dispatch(DRAG_END, {});
      }
    } catch (error) {
      console.error('Error parsing dropped data:', error);
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dispatch(DRAG_START, {});
  };

  return (
    <div
      className={`min-h-[200px] border-2 border-dashed ${
        isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50'
      } rounded-lg p-4 transition-colors ${className}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onDragEnter={handleDragEnter}
    >
      <div className="text-center text-gray-500 mb-4">
        <h3 className="text-lg font-medium">Timeline</h3>
        <p className="text-sm">Drag transitions and music here</p>
      </div>
      
      {droppedItems.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-700">Added Items:</h4>
          {droppedItems.map((item, index) => (
            <div key={index} className="flex items-center gap-2 p-2 bg-white rounded border">
              {item.preview && (
                <img src={item.preview} alt="" className="w-8 h-8 object-cover rounded" />
              )}
              <span className="text-sm">
                {item.name || item.kind || item.metadata?.fileName || 'Unknown Item'}
              </span>
              {item.type && (
                <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                  {item.type}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

