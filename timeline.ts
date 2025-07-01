// Timeline utilities
export const generateId = () => {
  return Math.random().toString(36).substr(2, 9);
};

// Timeline constants
export const DRAG_PREFIX = 'DRAG_';
export const DRAG_START = 'DRAG_START';
export const DRAG_END = 'DRAG_END';

