import { ScrollArea } from "@/components/ui/scroll-area";
import { TRANSITIONS } from "../data/transitions";
import { dispatch, ADD_TRANSITION } from "@/lib/events";
import React from "react";
import { useIsDraggingOverTimeline } from "../hooks/is-dragging-over-timeline";
import Draggable from "@/components/shared/draggable";

export const Transitions = () => {
  const isDraggingOverTimeline = useIsDraggingOverTimeline();

  const handleAddTransition = (transition: any) => {
    dispatch(ADD_TRANSITION, {
      payload: transition,
      options: {
        resourceId: "main",
      },
    });
    console.log('Transition added:', transition);
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="text-gray-800 flex h-12 flex-none items-center px-4 text-sm font-medium">
        Transitions
      </div>
      <ScrollArea className="flex-1 h-[calc(100vh-200px)]">
        <div className="grid grid-cols-2 gap-3 px-4 pb-4">
          {TRANSITIONS.map((transition) => {
            return (
              <TransitionItem
                key={transition.id}
                transition={transition}
                shouldDisplayPreview={!isDraggingOverTimeline}
                handleAddTransition={handleAddTransition}
              />
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
};

const TransitionItem = ({
  handleAddTransition,
  transition,
  shouldDisplayPreview,
}: {
  handleAddTransition: (transition: any) => void;
  transition: any;
  shouldDisplayPreview: boolean;
}) => {
  return (
    <Draggable
      data={transition}
      renderCustomPreview={
        <div className="flex items-center gap-2 bg-white p-2 rounded border shadow-lg">
          <img
            src={transition.preview}
            alt={transition.name || transition.kind}
            className="w-8 h-8 object-cover rounded"
          />
          <span className="text-sm font-medium">
            {transition.name || transition.kind}
          </span>
        </div>
      }
      shouldDisplayPreview={shouldDisplayPreview}
    >
      <div
        className="group relative cursor-pointer overflow-hidden rounded-lg border border-gray-200 bg-white hover:border-gray-300 transition-colors"
        onClick={() => handleAddTransition(transition)}
      >
        <div className="aspect-video w-full">
          <img
            src={transition.preview}
            alt={transition.name || transition.kind}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        </div>
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
          <div className="text-xs font-medium text-white">
            {transition.name || transition.kind}
          </div>
          <div className="text-xs text-white/70">
            {transition.duration}s
          </div>
        </div>
      </div>
    </Draggable>
  );
};

