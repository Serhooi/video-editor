// Types for the video editor
export interface IAudio {
  id: string;
  type: 'audio';
  details: {
    src: string;
  };
  metadata: {
    fileName?: string;
    duration?: string;
    genre?: string;
  };
}

export interface ITransition {
  id: string;
  name: string;
  kind: string;
  duration: number;
  preview: string;
}

export interface IMenuItem {
  id: string;
  name: string;
  icon: string;
}

