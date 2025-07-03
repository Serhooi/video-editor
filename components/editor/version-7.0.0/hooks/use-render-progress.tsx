import { useState, useCallback } from 'react';

interface RenderState {
  isRendering: boolean;
  renderId: string | null;
  bucketName: string | null;
  showProgress: boolean;
  error: string | null;
  videoUrl: string | null;
}

export const useRenderProgress = () => {
  const [renderState, setRenderState] = useState<RenderState>({
    isRendering: false,
    renderId: null,
    bucketName: null,
    showProgress: false,
    error: null,
    videoUrl: null,
  });

  const startRender = useCallback((renderId: string, bucketName: string) => {
    setRenderState({
      isRendering: true,
      renderId,
      bucketName,
      showProgress: true,
      error: null,
      videoUrl: null,
    });
  }, []);

  const onRenderComplete = useCallback((videoUrl: string) => {
    setRenderState(prev => ({
      ...prev,
      isRendering: false,
      videoUrl,
      error: null,
    }));
    
    // Show success message or download link
    console.log('🎉 Render completed! Video URL:', videoUrl);
    
    // You can add notification here
    if (videoUrl) {
      // Create download link
      const link = document.createElement('a');
      link.href = videoUrl;
      link.download = 'rendered-video.mp4';
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, []);

  const onRenderError = useCallback((error: string) => {
    setRenderState(prev => ({
      ...prev,
      isRendering: false,
      error,
    }));
    
    console.error('❌ Render failed:', error);
  }, []);

  const closeProgress = useCallback(() => {
    setRenderState(prev => ({
      ...prev,
      showProgress: false,
    }));
  }, []);

  const resetRender = useCallback(() => {
    setRenderState({
      isRendering: false,
      renderId: null,
      bucketName: null,
      showProgress: false,
      error: null,
      videoUrl: null,
    });
  }, []);

  return {
    renderState,
    startRender,
    onRenderComplete,
    onRenderError,
    closeProgress,
    resetRender,
  };
};

export default useRenderProgress;

