import { useState, useEffect } from "react";
import { eventEmitter, DRAG_START, DRAG_END } from "@/lib/events";

export const useIsDraggingOverTimeline = () => {
  const [isDraggingOverTimeline, setIsDraggingOverTimeline] = useState(false);

  useEffect(() => {
    const unsubscribeStart = eventEmitter.subscribe(DRAG_START, () => {
      setIsDraggingOverTimeline(true);
    });

    const unsubscribeEnd = eventEmitter.subscribe(DRAG_END, () => {
      setIsDraggingOverTimeline(false);
    });

    return () => {
      unsubscribeStart();
      unsubscribeEnd();
    };
  }, []);

  return isDraggingOverTimeline;
};

