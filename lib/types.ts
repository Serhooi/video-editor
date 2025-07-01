// Simple API types for lambda functions
export interface ProgressRequest {
  id: string;
  bucketName?: string;
  region?: string;
  functionName?: string;
}

export interface RenderRequest {
  id: string;
  inputProps: any;
  bucketName?: string;
  composition?: string;
  codec?: string;
  crf?: number;
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

