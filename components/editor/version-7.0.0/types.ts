/**
 * TypeScript types for React Video Editor Pro v7.0.0
 */

// Base types
export type UUID = string;
export type Timestamp = number;
export type Duration = number; // in seconds
export type Position = number; // in seconds

// Media types
export interface MediaFile {
  id: UUID;
  name: string;
  url: string;
  type: 'video' | 'audio' | 'image';
  mimeType: string;
  size: number;
  duration?: Duration;
  width?: number;
  height?: number;
  thumbnail?: string;
  createdAt: Timestamp;
}

// Timeline types
export interface TimelineItem {
  id: UUID;
  type: 'video' | 'audio' | 'text' | 'image' | 'effect';
  startTime: Position;
  duration: Duration;
  trackIndex: number;
  zIndex: number;
  locked: boolean;
  muted: boolean;
  visible: boolean;
  data: any; // Specific data for each item type
}

export interface VideoTimelineItem extends TimelineItem {
  type: 'video';
  data: {
    mediaFileId: UUID;
    volume: number;
    speed: number;
    filters: VideoFilter[];
    crop?: CropSettings;
    transform?: TransformSettings;
  };
}

export interface AudioTimelineItem extends TimelineItem {
  type: 'audio';
  data: {
    mediaFileId: UUID;
    volume: number;
    fadeIn: Duration;
    fadeOut: Duration;
    effects: AudioEffect[];
  };
}

export interface TextTimelineItem extends TimelineItem {
  type: 'text';
  data: {
    text: string;
    style: TextStyle;
    animation?: TextAnimation;
    position: Position2D;
  };
}

export interface ImageTimelineItem extends TimelineItem {
  type: 'image';
  data: {
    mediaFileId: UUID;
    opacity: number;
    filters: ImageFilter[];
    transform?: TransformSettings;
    animation?: ImageAnimation;
  };
}

// Style types
export interface TextStyle {
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold' | '100' | '200' | '300' | '400' | '500' | '600' | '700' | '800' | '900';
  color: string;
  backgroundColor?: string;
  textAlign: 'left' | 'center' | 'right';
  textDecoration?: 'none' | 'underline' | 'line-through';
  textShadow?: string;
  letterSpacing?: number;
  lineHeight?: number;
}

export interface Position2D {
  x: number;
  y: number;
}

export interface Size2D {
  width: number;
  height: number;
}

export interface CropSettings {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TransformSettings {
  scale: number;
  rotation: number;
  position: Position2D;
  anchor: Position2D;
}

// Animation types
export interface Animation {
  type: string;
  duration: Duration;
  easing: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
  delay?: Duration;
  repeat?: number | 'infinite';
}

export interface TextAnimation extends Animation {
  type: 'fade-in' | 'slide-in' | 'zoom-in' | 'typewriter' | 'bounce';
  direction?: 'left' | 'right' | 'top' | 'bottom';
}

export interface ImageAnimation extends Animation {
  type: 'fade-in' | 'slide-in' | 'zoom-in' | 'rotate-in' | 'flip';
  direction?: 'left' | 'right' | 'top' | 'bottom';
}

// Filter and effect types
export interface Filter {
  id: string;
  name: string;
  enabled: boolean;
  parameters: Record<string, any>;
}

export interface VideoFilter extends Filter {
  type: 'brightness' | 'contrast' | 'saturation' | 'hue' | 'blur' | 'sharpen' | 'vintage' | 'black-white';
}

export interface ImageFilter extends Filter {
  type: 'brightness' | 'contrast' | 'saturation' | 'hue' | 'blur' | 'sharpen' | 'vintage' | 'black-white' | 'sepia';
}

export interface AudioEffect extends Filter {
  type: 'reverb' | 'echo' | 'chorus' | 'distortion' | 'equalizer' | 'compressor' | 'noise-reduction';
}

// Project types
export interface VideoProject {
  id: UUID;
  title: string;
  description?: string;
  thumbnail?: string;
  duration: Duration;
  settings: ProjectSettings;
  timeline: TimelineItem[];
  mediaFiles: MediaFile[];
  createdAt: Timestamp;
  updatedAt: Timestamp;
  version: string;
}

export interface ProjectSettings {
  width: number;
  height: number;
  frameRate: number;
  sampleRate: number;
  backgroundColor: string;
  aspectRatio: '16:9' | '9:16' | '4:3' | '1:1' | '21:9';
  quality: 'low' | 'medium' | 'high' | 'ultra';
}

// Rendering types
export interface RenderJob {
  id: UUID;
  projectId: UUID;
  status: RenderStatus;
  progress: number; // 0-100
  settings: RenderSettings;
  outputUrl?: string;
  errorMessage?: string;
  createdAt: Timestamp;
  startedAt?: Timestamp;
  completedAt?: Timestamp;
}

export type RenderStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface RenderSettings {
  format: 'mp4' | 'webm' | 'mov';
  quality: 'low' | 'medium' | 'high' | 'ultra';
  width: number;
  height: number;
  frameRate: number;
  bitrate: number;
  audioQuality: number;
}

// AI Subtitles types
export interface SubtitleSegment {
  id: UUID;
  startTime: Position;
  endTime: Position;
  text: string;
  confidence: number;
  speaker?: string;
}

export interface AISubtitleJob {
  id: UUID;
  projectId: UUID;
  status: AIProcessingStatus;
  progress: number;
  language: string;
  style: SubtitleStyle;
  segments: SubtitleSegment[];
  confidence: number;
  errorMessage?: string;
  createdAt: Timestamp;
  completedAt?: Timestamp;
}

export type AIProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type SubtitleStyle = 'casual' | 'formal' | 'social-media' | 'educational';

export interface AISubtitleOptions {
  language: string;
  style: SubtitleStyle;
  maxWordsPerSegment: number;
  minSegmentDuration: Duration;
  maxSegmentDuration: Duration;
  speakerDetection: boolean;
}

// User and authentication types
export interface User {
  id: UUID;
  email: string;
  name: string;
  avatar?: string;
  subscription: SubscriptionTier;
  usage: UsageStats;
  preferences: UserPreferences;
  createdAt: Timestamp;
}

export type SubscriptionTier = 'free' | 'pro' | 'enterprise';

export interface UsageStats {
  renderMinutes: number;
  storageUsed: number; // in bytes
  aiMinutes: number;
  projectsCount: number;
  lastResetAt: Timestamp;
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto';
  language: string;
  autoSave: boolean;
  autoSaveInterval: number; // in seconds
  defaultProjectSettings: ProjectSettings;
  keyboardShortcuts: Record<string, string>;
}

// API types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}

export interface UploadResponse extends ApiResponse<MediaFile> {
  uploadUrl?: string;
}

// Event types
export interface TimelineEvent {
  type: 'item-added' | 'item-removed' | 'item-moved' | 'item-resized' | 'item-selected';
  itemId: UUID;
  data?: any;
}

export interface PlaybackEvent {
  type: 'play' | 'pause' | 'seek' | 'ended';
  currentTime: Position;
  duration: Duration;
}

export interface ProjectEvent {
  type: 'project-loaded' | 'project-saved' | 'project-changed';
  projectId: UUID;
  data?: any;
}

// Component props types
export interface TimelineProps {
  project: VideoProject;
  currentTime: Position;
  zoom: number;
  selectedItems: UUID[];
  onItemSelect: (itemIds: UUID[]) => void;
  onItemMove: (itemId: UUID, startTime: Position, trackIndex: number) => void;
  onItemResize: (itemId: UUID, duration: Duration) => void;
  onItemDelete: (itemIds: UUID[]) => void;
  onTimeSeek: (time: Position) => void;
}

export interface MediaLibraryProps {
  mediaFiles: MediaFile[];
  onFileSelect: (file: MediaFile) => void;
  onFileUpload: (files: File[]) => void;
  onFileDelete: (fileId: UUID) => void;
}

export interface PlayerProps {
  project: VideoProject;
  currentTime: Position;
  isPlaying: boolean;
  volume: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (time: Position) => void;
  onVolumeChange: (volume: number) => void;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>;

export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

// Error types
export interface VideoEditorError extends Error {
  code: string;
  details?: any;
}

export interface ValidationError extends VideoEditorError {
  field: string;
  value: any;
}

export interface NetworkError extends VideoEditorError {
  status: number;
  response?: any;
}

// Hook types
export interface UseTimelineReturn {
  items: TimelineItem[];
  selectedItems: UUID[];
  currentTime: Position;
  duration: Duration;
  zoom: number;
  addItem: (item: Omit<TimelineItem, 'id'>) => void;
  removeItem: (itemId: UUID) => void;
  updateItem: (itemId: UUID, updates: Partial<TimelineItem>) => void;
  selectItems: (itemIds: UUID[]) => void;
  setCurrentTime: (time: Position) => void;
  setZoom: (zoom: number) => void;
}

export interface UseProjectReturn {
  project: VideoProject | null;
  loading: boolean;
  error: string | null;
  createProject: (title: string, settings?: Partial<ProjectSettings>) => Promise<VideoProject>;
  loadProject: (projectId: UUID) => Promise<void>;
  saveProject: (updates?: Partial<VideoProject>) => Promise<void>;
  deleteProject: (projectId: UUID) => Promise<void>;
}

export interface UseMediaReturn {
  mediaFiles: MediaFile[];
  loading: boolean;
  error: string | null;
  uploadFile: (file: File) => Promise<MediaFile>;
  deleteFile: (fileId: UUID) => Promise<void>;
  getFileUrl: (fileId: UUID) => string;
}

// Configuration types
export interface EditorConfig {
  features: {
    aiSubtitles: boolean;
    videoEffects: boolean;
    audioEffects: boolean;
    collaboration: boolean;
    cloudStorage: boolean;
  };
  limits: {
    maxProjectDuration: Duration;
    maxFileSize: number;
    maxProjects: number;
    maxRenderJobs: number;
  };
  api: {
    baseUrl: string;
    timeout: number;
    retries: number;
  };
  storage: {
    provider: 'local' | 'aws' | 'gcp' | 'azure';
    bucket?: string;
    region?: string;
  };
}


// Lambda API types
export interface RenderRequest {
  id: string;
  inputProps: Record<string, any>;
  composition: string;
  codec?: 'h264' | 'h265' | 'vp8' | 'vp9';
  crf?: number;
  envVariables?: Record<string, string>;
  frameRange?: [number, number];
  framesPerLambda?: number;
  imageFormat?: 'jpeg' | 'png';
  jpegQuality?: number;
  maxRetries?: number;
  privacy?: 'public' | 'private';
  proResProfile?: string;
  scale?: number;
  timeoutInMilliseconds?: number;
  audioBitrate?: string;
  videoBitrate?: string;
  webhook?: {
    url: string;
    secret?: string;
  };
}

export interface ProgressRequest {
  bucketName: string;
  id: string;
  region: string;
  functionName: string;
}

export interface ProgressResponse {
  type: 'error' | 'done' | 'progress';
  message?: string;
  progress?: number;
  outputUrl?: string;
  outputSize?: number;
  renderMetadata?: {
    startedDate: number;
    totalChunks: number;
    estimatedTotalLambdaInvokations: number;
    estimatedRenderLambdaInvokations: number;
    renderId: string;
    bucket: string;
    outputKey?: string;
    outKey?: string;
    timeToFinish?: number;
    costs?: {
      currency: string;
      disclaimer: string;
      estimatedCost: number;
      estimatedDisplayCost: string;
    };
  };
  fatalErrorEncountered?: boolean;
  currentTime?: number;
  renderSize?: number;
}

export interface LambdaRenderResponse {
  type: 'success' | 'error';
  renderId?: string;
  bucketName?: string;
  message?: string;
  error?: string;
}

// Remotion composition types
export interface RemotionComposition {
  id: string;
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  defaultProps?: Record<string, any>;
}

export interface RemotionInputProps {
  title?: string;
  subtitle?: string;
  backgroundColor?: string;
  textColor?: string;
  timeline?: TimelineItem[];
  mediaFiles?: MediaFile[];
  settings?: ProjectSettings;
  [key: string]: any;
}

