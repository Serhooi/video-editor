# АНАЛИЗ ОРИГИНАЛЬНОГО DRAG & DROP КОДА

## useIsDraggingOverTimeline Hook

```typescript
import { useState, useEffect } from "react";
import { filter, subject } from "@designcombo/events";
import { DRAG_END, DRAG_PREFIX, DRAG_START } from "@designcombo/timeline";

export const useIsDraggingOverTimeline = () => {
  const [isDraggingOverTimeline, setIsDraggingOverTimeline] = useState(false);

  useEffect(() => {
    const dragEvents = subject.pipe(
      filter(({ key }) => key.startsWith(DRAG_PREFIX)),
    );

    const dragEventsSubscription = dragEvents.subscribe((obj) => {
      if (obj.key === DRAG_START) {
        setIsDraggingOverTimeline(true);
      } else if (obj.key === DRAG_END) {
        setIsDraggingOverTimeline(false);
      }
    });

    return () => dragEventsSubscription.unsubscribe();
  }, []);

  return isDraggingOverTimeline;
};
```

## Ключевые моменты:
1. Использует @designcombo/events для отслеживания drag событий
2. Отслеживает DRAG_START и DRAG_END события
3. Управляет состоянием isDraggingOverTimeline
4. Использует DRAG_PREFIX для фильтрации событий

