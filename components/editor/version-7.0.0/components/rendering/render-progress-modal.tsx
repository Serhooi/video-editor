import React, { useEffect, useState } from 'react';

interface RenderProgressModalProps {
  isOpen: boolean;
  onClose: () => void;
  renderId: string;
  bucketName: string;
  onComplete: (videoUrl: string) => void;
  onError: (error: string) => void;
}

interface ProgressData {
  type: 'progress' | 'done' | 'error';
  progress?: number;
  outputFile?: string;
  url?: string;
  message?: string;
  framesRendered?: number;
  totalFrames?: number;
}

export const RenderProgressModal: React.FC<RenderProgressModalProps> = ({
  isOpen,
  onClose,
  renderId,
  bucketName,
  onComplete,
  onError
}) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [isPolling, setIsPolling] = useState(false);
  const [timeElapsed, setTimeElapsed] = useState(0);

  useEffect(() => {
    if (isOpen && renderId && !isPolling) {
      startPolling();
    }
  }, [isOpen, renderId]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isOpen && isPolling) {
      timer = setInterval(() => {
        setTimeElapsed(prev => prev + 1);
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isOpen, isPolling]);

  const startPolling = async () => {
    setIsPolling(true);
    setAttempts(0);
    setTimeElapsed(0);
    
    const maxAttempts = 120; // 10 minutes
    let currentAttempts = 0;

    const poll = async () => {
      try {
        currentAttempts++;
        setAttempts(currentAttempts);

        const response = await fetch("/api/lambda/progress", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            renderId: renderId,
            bucketName: bucketName,
          }),
        });

        if (!response.ok) {
          throw new Error(`Progress check failed: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success && result.progress) {
          const progressData = result.progress;
          setProgress(progressData);
          
          // Check if render is complete
          if (progressData.type === "done") {
            setIsPolling(false);
            onComplete(progressData.outputFile || progressData.url || '');
            return;
          }
          
          // Check if render failed
          if (progressData.type === "error") {
            setIsPolling(false);
            onError(progressData.message || "Render failed");
            return;
          }
        }

        // Continue polling if not done and under max attempts
        if (currentAttempts < maxAttempts) {
          setTimeout(poll, 5000); // Wait 5 seconds before next check
        } else {
          setIsPolling(false);
          onError("Render timeout - exceeded maximum wait time (10 minutes)");
        }
      } catch (error: any) {
        console.error("Progress check error:", error);
        
        // If we're near the end, throw the error
        if (currentAttempts >= maxAttempts - 5) {
          setIsPolling(false);
          onError(error.message || "Progress check failed");
          return;
        }
        
        // Otherwise, wait and try again
        setTimeout(poll, 5000);
      }
    };

    poll();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getProgressPercentage = () => {
    if (!progress) return 0;
    
    if (progress.progress !== undefined) {
      return Math.round(progress.progress * 100);
    }
    
    if (progress.framesRendered && progress.totalFrames) {
      return Math.round((progress.framesRendered / progress.totalFrames) * 100);
    }
    
    // Estimate based on attempts (rough approximation)
    return Math.min(Math.round((attempts / 120) * 100), 95);
  };

  const getStatusText = () => {
    if (!progress) return "Initializing render...";
    
    switch (progress.type) {
      case 'progress':
        if (progress.framesRendered && progress.totalFrames) {
          return `Rendering frames ${progress.framesRendered}/${progress.totalFrames}`;
        }
        return "Rendering in progress...";
      case 'done':
        return "Render completed successfully!";
      case 'error':
        return `Render failed: ${progress.message}`;
      default:
        return "Processing...";
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-md mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Video Rendering
          </h3>
          {!isPolling && (
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>

        <div className="space-y-4">
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${getProgressPercentage()}%` }}
            />
          </div>

          {/* Progress Text */}
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">
              {getProgressPercentage()}%
            </div>
            <div className="text-sm text-gray-600">
              {getStatusText()}
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="text-center">
              <div className="font-semibold text-gray-900">Time Elapsed</div>
              <div className="text-gray-600">{formatTime(timeElapsed)}</div>
            </div>
            <div className="text-center">
              <div className="font-semibold text-gray-900">Attempts</div>
              <div className="text-gray-600">{attempts}/120</div>
            </div>
          </div>

          {/* Render ID */}
          <div className="text-xs text-gray-500 text-center">
            Render ID: {renderId}
          </div>

          {/* Loading Animation */}
          {isPolling && (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default RenderProgressModal;

