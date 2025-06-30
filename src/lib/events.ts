// Simple event system to replace @designcombo/events
type EventCallback = (data: any) => void;

class EventEmitter {
  private events: Map<string, EventCallback[]> = new Map();

  subscribe(eventName: string, callback: EventCallback) {
    if (!this.events.has(eventName)) {
      this.events.set(eventName, []);
    }
    this.events.get(eventName)!.push(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.events.get(eventName);
      if (callbacks) {
        const index = callbacks.indexOf(callback);
        if (index > -1) {
          callbacks.splice(index, 1);
        }
      }
    };
  }

  emit(eventName: string, data: any) {
    const callbacks = this.events.get(eventName);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }
}

export const eventEmitter = new EventEmitter();

export const dispatch = (eventName: string, data: any) => {
  eventEmitter.emit(eventName, data);
};

// Event constants
export const DRAG_START = 'DRAG_START';
export const DRAG_END = 'DRAG_END';
export const DRAG_PREFIX = 'DRAG_';

// State action constants
export const ADD_TRANSITION = 'ADD_TRANSITION';
export const ADD_ITEMS = 'ADD_ITEMS';
export const ADD_CAPTIONS = 'ADD_CAPTIONS';

