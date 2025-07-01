import React, { useState, cloneElement, type ReactElement } from 'react';
import { createPortal } from 'react-dom';

interface DraggableProps {
  children: ReactElement;
  shouldDisplayPreview?: boolean;
  renderCustomPreview?: ReactElement;
  data?: Record<string, any> | (() => Record<string, any>);
}

const Draggable: React.FC<DraggableProps> = ({
  children,
  renderCustomPreview,
  data,
  shouldDisplayPreview = true,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const handleDragStart = (e: React.DragEvent<HTMLElement>) => {
    if (!data) {
      return;
    }
    const dataObj = typeof data === 'function' ? data() : data;
    setIsDragging(true);
    
    // Set a transparent drag image
    const dragImage = new Image();
    dragImage.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; // transparent 1x1 pixel
    e.dataTransfer.setDragImage(dragImage, 0, 0);
    
    // Set data in multiple formats to ensure compatibility
    const jsonData = JSON.stringify(dataObj);
    e.dataTransfer.setData('application/json', jsonData);
    e.dataTransfer.setData('text/plain', jsonData);
    
    // For custom format
    try {
      e.dataTransfer.setData('application/designcombo', jsonData);
    } catch (error) {
      console.warn('Could not set custom data format', error);
    }
    
    e.dataTransfer.effectAllowed = 'move';

    setPosition({
      x: e.clientX,
      y: e.clientY,
    });
    
    // Log the data being dragged for debugging
    console.log('Drag started with data:', dataObj);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent<HTMLElement>) => {
    e.preventDefault(); // Important: allows drop
    if (isDragging) {
      setPosition({
        x: e.clientX,
        y: e.clientY,
      });
    }
  };

  // Add dragover event listener to document
  React.useEffect(() => {
    const handleDocumentDragOver = (e: DragEvent) => {
      e.preventDefault();
      if (isDragging) {
        setPosition({
          x: e.clientX,
          y: e.clientY,
        });
      }
    };

    if (isDragging) {
      document.addEventListener('dragover', handleDocumentDragOver);
    }

    return () => {
      document.removeEventListener('dragover', handleDocumentDragOver);
    };
  }, [isDragging]);

  const childWithProps = cloneElement(children, {
    draggable: true,
    onDragStart: handleDragStart,
    onDragEnd: handleDragEnd,
    onDragOver: handleDragOver,
    style: {
      ...children.props.style,
      cursor: 'grab',
    },
  });

  return (
    <>
      {childWithProps}
      {isDragging && shouldDisplayPreview && renderCustomPreview
        ? createPortal(
            <div
              style={{
                position: 'fixed',
                left: position.x,
                top: position.y,
                pointerEvents: 'none',
                zIndex: 9999,
                transform: 'translate(-50%, -50%)', // Center the preview
              }}
            >
              {renderCustomPreview}
            </div>,
            document.body
          )
        : null}
    </>
  );
};

export default Draggable;

