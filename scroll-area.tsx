import React from 'react';

interface ScrollAreaProps {
  children: React.ReactNode;
  className?: string;
}

export const ScrollArea: React.FC<ScrollAreaProps> = ({ children, className = '' }) => {
  return (
    <div className={`overflow-auto ${className}`}>
      {children}
    </div>
  );
};

