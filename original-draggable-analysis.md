# Анализ оригинального Draggable компонента

## Ключевые особенности:

1. **Интерфейс DraggableProps:**
   - children: ReactElement
   - shouldDisplayPreview?: boolean
   - renderCustomPreview?: ReactElement
   - data?: Record<string, any> | (() => Record<string, any>)

2. **Состояние:**
   - isDragging: boolean
   - position: { x: number, y: number }

3. **Обработчики событий:**
   - handleDragStart: устанавливает данные в dataTransfer
   - handleDragEnd: сбрасывает состояние
   - handleDragOver: обновляет позицию

4. **Ключевые моменты:**
   - Использует createPortal для отображения preview
   - Скрывает стандартный preview с помощью setDragImage(new Image(), 0, 0)
   - Устанавливает данные в dataTransfer как JSON
   - Обновляет позицию через document.addEventListener('dragover')

## Проблемы в моей реализации:
1. Возможно, неправильная установка данных в dataTransfer
2. Отсутствие правильной обработки событий timeline
3. Неправильная интеграция с системой событий

## Решение:
Нужно обновить мой Draggable компонент, чтобы он точно соответствовал оригиналу.

