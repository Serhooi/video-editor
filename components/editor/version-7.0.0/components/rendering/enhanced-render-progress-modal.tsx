import React, { useEffect, useState } from 'react';
import { X, Download, AlertCircle, CheckCircle, Clock, Zap, Film } from 'lucide-react';

interface EnhancedRenderProgressModalProps {
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

interface RenderStats {
  timeElapsed: number;
  attempts: number;
  estimatedTimeRemaining: number;
  averageFrameTime: number;
}

export const EnhancedRenderProgressModal: React.FC<EnhancedRenderProgressModalProps> = ({
  isOpen,
  onClose,
  renderId,
  bucketName,
  onComplete,
  onError
}) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [stats, setStats] = useState<RenderStats>({
    timeElapsed: 0,
    attempts: 0,
    estimatedTimeRemaining: 0,
    averageFrameTime: 0
  });
  const [isPolling, setIsPolling] = useState(false);
  const [renderComplete, setRenderComplete] = useState(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && renderId && !isPolling) {
      startPolling();
    }
  }, [isOpen, renderId]);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isOpen && isPolling) {
      timer = setInterval(() => {
        setStats(prev => ({
          ...prev,
          timeElapsed: prev.timeElapsed + 1
        }));
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isOpen, isPolling]);

  const startPolling = async () => {
    setIsPolling(true);
    setStats(prev => ({ ...prev, attempts: 0, timeElapsed: 0 }));
    setRenderComplete(false);
    setRenderError(null);
    setDownloadUrl(null);
    
    const maxAttempts = 120; // 10 minutes
    let currentAttempts = 0;
    let startTime = Date.now();

    const poll = async () => {
      try {
        currentAttempts++;
        setStats(prev => ({ ...prev, attempts: currentAttempts }));

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
          
          // Calculate estimated time remaining
          if (progressData.progress && progressData.progress > 0) {
            const elapsed = (Date.now() - startTime) / 1000;
            const estimatedTotal = elapsed / progressData.progress;
            const remaining = Math.max(0, estimatedTotal - elapsed);
            
            setStats(prev => ({
              ...prev,
              estimatedTimeRemaining: remaining,
              averageFrameTime: progressData.framesRendered ? elapsed / progressData.framesRendered : 0
            }));
          }
          
          // Check if render is complete
          if (progressData.type === "done") {
            setIsPolling(false);
            setRenderComplete(true);
            setDownloadUrl(progressData.outputFile || progressData.url || '');
            onComplete(progressData.outputFile || progressData.url || '');
            return;
          }
          
          // Check if render failed
          if (progressData.type === "error") {
            setIsPolling(false);
            setRenderError(progressData.message || "Render failed");
            onError(progressData.message || "Render failed");
            return;
          }
        }

        // Continue polling if not done and under max attempts
        if (currentAttempts < maxAttempts) {
          setTimeout(poll, 5000); // Wait 5 seconds before next check
        } else {
          setIsPolling(false);
          setRenderError("Render timeout - exceeded maximum wait time (10 minutes)");
          onError("Render timeout - exceeded maximum wait time (10 minutes)");
        }
      } catch (error: any) {
        console.error("Progress check error:", error);
        
        // If we're near the end, throw the error
        if (currentAttempts >= maxAttempts - 5) {
          setIsPolling(false);
          setRenderError(error.message || "Progress check failed");
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
    return Math.min(Math.round((stats.attempts / 120) * 100), 95);
  };

  const getStatusText = () => {
    if (renderComplete) return "Render completed successfully!";
    if (renderError) return `Render failed: ${renderError}`;
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

  const getStatusIcon = () => {
    if (renderComplete) return <CheckCircle className="w-6 h-6 text-green-500" />;
    if (renderError) return <AlertCircle className="w-6 h-6 text-red-500" />;
    return <Film className="w-6 h-6 text-blue-500 animate-pulse" />;
  };

  const handleDownload = () => {
    if (downloadUrl) {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'rendered-video.mp4';
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (!isOpen) return null;

  const progressPercentage = getProgressPercentage();

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-auto overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 text-white">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              {getStatusIcon()}
              <div>
                <h3 className="text-lg font-semibold">Video Rendering</h3>
                <p className="text-blue-100 text-sm opacity-90">
                  {renderComplete ? 'Complete' : renderError ? 'Failed' : 'In Progress'}
                </p>
              </div>
            </div>
            {(renderComplete || renderError) && (
              <button
                onClick={onClose}
                className="text-white/80 hover:text-white transition-colors p-1 rounded-full hover:bg-white/20"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Progress Bar */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">Progress</span>
              <span className="text-2xl font-bold text-gray-900">{progressPercentage}%</span>
            </div>
            
            <div className="relative">
              <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ease-out ${
                    renderComplete 
                      ? 'bg-gradient-to-r from-green-500 to-green-600' 
                      : renderError 
                        ? 'bg-gradient-to-r from-red-500 to-red-600'
                        : 'bg-gradient-to-r from-blue-500 to-purple-600'
                  }`}
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
              {isPolling && (
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse rounded-full" />
              )}
            </div>
            
            <p className="text-sm text-gray-600 text-center">
              {getStatusText()}
            </p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="flex items-center justify-center mb-2">
                <Clock className="w-4 h-4 text-gray-500 mr-1" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Time Elapsed</span>
              </div>
              <div className="text-xl font-bold text-gray-900">{formatTime(stats.timeElapsed)}</div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 text-center">
              <div className="flex items-center justify-center mb-2">
                <Zap className="w-4 h-4 text-gray-500 mr-1" />
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Attempts</span>
              </div>
              <div className="text-xl font-bold text-gray-900">{stats.attempts}/120</div>
            </div>
          </div>

          {/* Estimated Time Remaining */}
          {stats.estimatedTimeRemaining > 0 && !renderComplete && !renderError && (
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-1">
                Estimated Time Remaining
              </div>
              <div className="text-lg font-bold text-blue-900">
                {formatTime(Math.round(stats.estimatedTimeRemaining))}
              </div>
            </div>
          )}

          {/* Frame Progress */}
          {progress?.framesRendered && progress?.totalFrames && (
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-medium text-purple-600 uppercase tracking-wide">Frames</span>
                <span className="text-sm font-bold text-purple-900">
                  {progress.framesRendered}/{progress.totalFrames}
                </span>
              </div>
              <div className="w-full bg-purple-200 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.framesRendered / progress.totalFrames) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Render ID */}
          <div className="text-center">
            <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">Render ID</div>
            <div className="text-xs font-mono text-gray-600 bg-gray-100 rounded px-2 py-1 inline-block">
              {renderId}
            </div>
          </div>

          {/* Action Buttons */}
          {renderComplete && downloadUrl && (
            <button
              onClick={handleDownload}
              className="w-full bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold py-3 px-4 rounded-lg hover:from-green-600 hover:to-green-700 transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg"
            >
              <Download className="w-5 h-5" />
              <span>Download Video</span>
            </button>
          )}

          {renderError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center space-x-2 text-red-800">
                <AlertCircle className="w-5 h-5" />
                <span className="font-medium">Render Failed</span>
              </div>
              <p className="text-red-700 text-sm mt-2">{renderError}</p>
            </div>
          )}

          {/* Loading Animation */}
          {isPolling && (
            <div className="flex justify-center">
              <div className="relative">
                <div className="w-8 h-8 border-4 border-blue-200 rounded-full animate-spin"></div>
                <div className="absolute top-0 left-0 w-8 h-8 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnhancedRenderProgressModal;

