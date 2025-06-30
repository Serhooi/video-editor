/**
 * API Response helpers for Lambda functions
 */

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Create a successful API response
 */
export const createSuccessResponse = <T>(data: T, message?: string): ApiResponse<T> => {
  return {
    success: true,
    data,
    message,
  };
};

/**
 * Create an error API response
 */
export const createErrorResponse = (error: string, data?: any): ApiResponse => {
  return {
    success: false,
    error,
    data,
  };
};

/**
 * Create a validation error response
 */
export const createValidationErrorResponse = (errors: string[]): ApiResponse => {
  return {
    success: false,
    error: 'Validation failed',
    data: { errors },
  };
};

/**
 * Create a not found response
 */
export const createNotFoundResponse = (resource: string): ApiResponse => {
  return {
    success: false,
    error: `${resource} not found`,
  };
};

/**
 * Create an unauthorized response
 */
export const createUnauthorizedResponse = (): ApiResponse => {
  return {
    success: false,
    error: 'Unauthorized access',
  };
};

/**
 * Create a server error response
 */
export const createServerErrorResponse = (error?: string): ApiResponse => {
  return {
    success: false,
    error: error || 'Internal server error',
  };
};

/**
 * Wrap async function with error handling
 */
export const withErrorHandling = <T extends any[], R>(
  fn: (...args: T) => Promise<R>
) => {
  return async (...args: T): Promise<ApiResponse<R>> => {
    try {
      const result = await fn(...args);
      return createSuccessResponse(result);
    } catch (error) {
      console.error('API Error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return createServerErrorResponse(errorMessage);
    }
  };
};

/**
 * Validate required fields in request body
 */
export const validateRequiredFields = (
  body: Record<string, any>,
  requiredFields: string[]
): string[] => {
  const errors: string[] = [];
  
  for (const field of requiredFields) {
    if (!body[field] || (typeof body[field] === 'string' && !body[field].trim())) {
      errors.push(`Field '${field}' is required`);
    }
  }
  
  return errors;
};

/**
 * Parse JSON safely
 */
export const parseJsonSafely = <T>(jsonString: string): T | null => {
  try {
    return JSON.parse(jsonString) as T;
  } catch {
    return null;
  }
};

/**
 * Format file size in human readable format
 */
export const formatFileSize = (bytes: number): string => {
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 Bytes';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Generate unique filename
 */
export const generateUniqueFilename = (originalName: string): string => {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  const extension = originalName.split('.').pop();
  const nameWithoutExt = originalName.replace(/\.[^/.]+$/, '');
  
  return `${nameWithoutExt}-${timestamp}-${random}.${extension}`;
};

/**
 * Check if file type is allowed
 */
export const isAllowedFileType = (mimeType: string, allowedTypes: string[]): boolean => {
  return allowedTypes.some(type => {
    if (type.endsWith('/*')) {
      return mimeType.startsWith(type.slice(0, -1));
    }
    return mimeType === type;
  });
};

/**
 * Rate limiting helper
 */
export const createRateLimiter = (maxRequests: number, windowMs: number) => {
  const requests = new Map<string, number[]>();
  
  return (identifier: string): boolean => {
    const now = Date.now();
    const windowStart = now - windowMs;
    
    if (!requests.has(identifier)) {
      requests.set(identifier, []);
    }
    
    const userRequests = requests.get(identifier)!;
    
    // Remove old requests outside the window
    const validRequests = userRequests.filter(time => time > windowStart);
    
    if (validRequests.length >= maxRequests) {
      return false; // Rate limit exceeded
    }
    
    validRequests.push(now);
    requests.set(identifier, validRequests);
    
    return true; // Request allowed
  };
};

