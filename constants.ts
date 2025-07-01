/**
 * Constants for React Video Editor Pro v7.0.0
 */

// Video rendering constants
export const VIDEO_CONSTANTS = {
  // Supported video formats
  SUPPORTED_VIDEO_FORMATS: [
    'video/mp4',
    'video/webm',
    'video/quicktime',
    'video/x-msvideo', // .avi
  ],
  
  // Supported audio formats
  SUPPORTED_AUDIO_FORMATS: [
    'audio/mp3',
    'audio/wav',
    'audio/ogg',
    'audio/aac',
    'audio/m4a',
  ],
  
  // Supported image formats
  SUPPORTED_IMAGE_FORMATS: [
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif',
    'image/webp',
    'image/svg+xml',
  ],
  
  // Video quality presets
  QUALITY_PRESETS: {
    LOW: { width: 640, height: 360, bitrate: 500 },
    MEDIUM: { width: 1280, height: 720, bitrate: 1500 },
    HIGH: { width: 1920, height: 1080, bitrate: 3000 },
    ULTRA: { width: 3840, height: 2160, bitrate: 8000 },
  },
  
  // Frame rates
  FRAME_RATES: [24, 25, 30, 50, 60],
  
  // Max file sizes (in bytes)
  MAX_FILE_SIZES: {
    VIDEO: 500 * 1024 * 1024, // 500MB
    AUDIO: 50 * 1024 * 1024,  // 50MB
    IMAGE: 10 * 1024 * 1024,  // 10MB
  },
  
  // Video duration limits (in seconds)
  MAX_DURATION: 600, // 10 minutes
  MIN_DURATION: 1,   // 1 second
};

// Timeline constants
export const TIMELINE_CONSTANTS = {
  // Zoom levels
  ZOOM_LEVELS: [0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 5],
  DEFAULT_ZOOM: 1,
  
  // Grid settings
  GRID_SIZE: 10,
  SNAP_THRESHOLD: 5,
  
  // Track heights
  TRACK_HEIGHTS: {
    VIDEO: 80,
    AUDIO: 60,
    TEXT: 40,
    IMAGE: 60,
  },
  
  // Timeline settings
  PIXELS_PER_SECOND: 100,
  MIN_CLIP_DURATION: 0.1, // 100ms
  
  // Playhead
  PLAYHEAD_WIDTH: 2,
  PLAYHEAD_COLOR: '#ff0000',
};

// Rendering constants
export const RENDER_CONSTANTS = {
  // Render statuses
  STATUS: {
    PENDING: 'pending',
    PROCESSING: 'processing',
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELLED: 'cancelled',
  },
  
  // Render priorities
  PRIORITY: {
    LOW: 1,
    NORMAL: 2,
    HIGH: 3,
    URGENT: 4,
  },
  
  // Render formats
  OUTPUT_FORMATS: {
    MP4: 'mp4',
    WEBM: 'webm',
    MOV: 'mov',
  },
  
  // Progress update intervals
  PROGRESS_UPDATE_INTERVAL: 1000, // 1 second
  
  // Timeout settings
  RENDER_TIMEOUT: 30 * 60 * 1000, // 30 minutes
  PROGRESS_TIMEOUT: 5 * 60 * 1000, // 5 minutes
};

// AI Subtitles constants
export const AI_CONSTANTS = {
  // Supported languages for Whisper
  SUPPORTED_LANGUAGES: {
    'auto': 'Auto-detect',
    'en': 'English',
    'ru': 'Russian',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
  },
  
  // Subtitle styles
  SUBTITLE_STYLES: {
    CASUAL: 'casual',
    FORMAL: 'formal',
    SOCIAL_MEDIA: 'social-media',
    EDUCATIONAL: 'educational',
  },
  
  // Whisper model settings
  WHISPER_MODELS: {
    TINY: 'whisper-1',
    BASE: 'whisper-1',
    SMALL: 'whisper-1',
    MEDIUM: 'whisper-1',
    LARGE: 'whisper-1',
  },
  
  // Processing limits
  MAX_AUDIO_DURATION: 25 * 60, // 25 minutes (Whisper limit)
  MAX_WORDS_PER_SEGMENT: 12,
  MIN_WORDS_PER_SEGMENT: 3,
  
  // Confidence thresholds
  MIN_CONFIDENCE: 0.7,
  HIGH_CONFIDENCE: 0.9,
};

// UI Constants
export const UI_CONSTANTS = {
  // Animation durations
  ANIMATION_DURATION: {
    FAST: 150,
    NORMAL: 300,
    SLOW: 500,
  },
  
  // Breakpoints
  BREAKPOINTS: {
    SM: 640,
    MD: 768,
    LG: 1024,
    XL: 1280,
    '2XL': 1536,
  },
  
  // Z-index layers
  Z_INDEX: {
    DROPDOWN: 1000,
    MODAL: 1050,
    TOOLTIP: 1100,
    NOTIFICATION: 1200,
  },
  
  // Colors
  COLORS: {
    PRIMARY: '#3b82f6',
    SECONDARY: '#64748b',
    SUCCESS: '#10b981',
    WARNING: '#f59e0b',
    ERROR: '#ef4444',
    INFO: '#06b6d4',
  },
};

// API Constants
export const API_CONSTANTS = {
  // Rate limiting
  RATE_LIMITS: {
    RENDER: { requests: 5, window: 60 * 1000 }, // 5 requests per minute
    UPLOAD: { requests: 10, window: 60 * 1000 }, // 10 uploads per minute
    AI_SUBTITLES: { requests: 3, window: 60 * 1000 }, // 3 AI requests per minute
  },
  
  // Request timeouts
  TIMEOUTS: {
    UPLOAD: 5 * 60 * 1000, // 5 minutes
    RENDER: 30 * 60 * 1000, // 30 minutes
    AI_PROCESSING: 10 * 60 * 1000, // 10 minutes
  },
  
  // Response codes
  HTTP_STATUS: {
    OK: 200,
    CREATED: 201,
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    CONFLICT: 409,
    UNPROCESSABLE_ENTITY: 422,
    TOO_MANY_REQUESTS: 429,
    INTERNAL_SERVER_ERROR: 500,
    SERVICE_UNAVAILABLE: 503,
  },
};

// Storage constants
export const STORAGE_CONSTANTS = {
  // Local storage keys
  KEYS: {
    PROJECT_DATA: 'video_editor_project',
    USER_PREFERENCES: 'video_editor_preferences',
    RECENT_PROJECTS: 'video_editor_recent',
    AUTOSAVE_DATA: 'video_editor_autosave',
  },
  
  // Cache settings
  CACHE_DURATION: {
    SHORT: 5 * 60 * 1000, // 5 minutes
    MEDIUM: 30 * 60 * 1000, // 30 minutes
    LONG: 24 * 60 * 60 * 1000, // 24 hours
  },
  
  // Storage limits
  MAX_STORAGE_SIZE: 50 * 1024 * 1024, // 50MB for IndexedDB
  MAX_PROJECTS: 100,
};

// Feature flags
export const FEATURE_FLAGS = {
  AI_SUBTITLES: true,
  VIDEO_EFFECTS: true,
  AUDIO_EFFECTS: true,
  COLLABORATION: false,
  CLOUD_STORAGE: false,
  LIVE_STREAMING: false,
  ADVANCED_ANALYTICS: false,
};

// Version info
export const VERSION_INFO = {
  VERSION: '7.0.0',
  BUILD_DATE: '2024-01-01',
  API_VERSION: 'v1',
  MINIMUM_BROWSER_VERSION: {
    CHROME: 90,
    FIREFOX: 88,
    SAFARI: 14,
    EDGE: 90,
  },
};

// Error messages
export const ERROR_MESSAGES = {
  GENERIC: 'An unexpected error occurred',
  NETWORK: 'Network connection error',
  FILE_TOO_LARGE: 'File size exceeds the maximum limit',
  UNSUPPORTED_FORMAT: 'File format is not supported',
  INVALID_DURATION: 'Video duration is invalid',
  RENDER_FAILED: 'Video rendering failed',
  AI_PROCESSING_FAILED: 'AI processing failed',
  QUOTA_EXCEEDED: 'Usage quota exceeded',
  UNAUTHORIZED: 'You are not authorized to perform this action',
  PROJECT_NOT_FOUND: 'Project not found',
  INVALID_PROJECT_DATA: 'Invalid project data',
};

// Success messages
export const SUCCESS_MESSAGES = {
  PROJECT_SAVED: 'Project saved successfully',
  PROJECT_CREATED: 'Project created successfully',
  PROJECT_DELETED: 'Project deleted successfully',
  FILE_UPLOADED: 'File uploaded successfully',
  RENDER_STARTED: 'Video rendering started',
  RENDER_COMPLETED: 'Video rendered successfully',
  AI_SUBTITLES_GENERATED: 'AI subtitles generated successfully',
  SETTINGS_UPDATED: 'Settings updated successfully',
};


// Lambda constants for Remotion rendering
export const LAMBDA_FUNCTION_NAME = process.env.REMOTION_LAMBDA_FUNCTION_NAME || 'remotion-render';
export const REGION = (process.env.REMOTION_AWS_REGION || 'us-east-1') as any;
export const SITE_NAME = process.env.REMOTION_SITE_NAME || 'video-editor-site';

// Lambda configuration
export const LAMBDA_CONFIG = {
  FUNCTION_NAME: LAMBDA_FUNCTION_NAME,
  FRAMES_PER_LAMBDA: 100,
  MAX_RETRIES: 2,
  CODEC: 'h264' as const,
  TIMEOUT: 900, // 15 minutes
  MEMORY_SIZE: 3008, // MB
} as const;

