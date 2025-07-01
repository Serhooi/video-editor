import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Wand2, Download, Upload, CheckCircle, AlertCircle } from 'lucide-react';
import { generateAutoSubtitles, exportToSRT, convertToEditorCaptions } from '../../../../../../lib/ai-subtitles';

interface AutoSubtitlesGeneratorProps {
  onSubtitlesGenerated: (captions: any[]) => void;
  videoFile?: File;
}

interface GenerationStep {
  id: string;
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
}

export const AutoSubtitlesGenerator: React.FC<AutoSubtitlesGeneratorProps> = ({
  onSubtitlesGenerated,
  videoFile
}) => {
  // Используем API ключ из переменных окружения
  const apiKey = process.env.NEXT_PUBLIC_OPENAI_API_KEY || '';
  const [language, setLanguage] = useState('ru');
  const [style, setStyle] = useState<'casual' | 'formal' | 'social-media' | 'educational'>('casual');
  const [maxWords, setMaxWords] = useState(8);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedSubtitles, setGeneratedSubtitles] = useState<any[] | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  
  const [steps, setSteps] = useState<GenerationStep[]>([
    { id: 'extract', name: 'Extracting audio from video', status: 'pending', progress: 0 },
    { id: 'transcribe', name: 'Speech recognition (Whisper AI)', status: 'pending', progress: 0 },
    { id: 'enhance', name: 'Text processing (ChatGPT)', status: 'pending', progress: 0 },
    { id: 'format', name: 'Formatting subtitles', status: 'pending', progress: 0 },
  ]);

  const updateStep = (stepId: string, status: GenerationStep['status'], progress: number = 0) => {
    setSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, status, progress } : step
    ));
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && (file.type.startsWith('video/') || file.type.startsWith('audio/'))) {
      setUploadedFile(file);
      setError(null);
    } else {
      setError('Please select a video or audio file');
    }
  };

  const handleGenerate = async () => {
    const fileToProcess = uploadedFile || videoFile;
    
    if (!fileToProcess) {
      setError('Please select a video file');
      return;
    }

    if (!apiKey.trim()) {
      setError('API key not configured. Please contact administrator.');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setGeneratedSubtitles(null);

    // Reset steps
    setSteps(prev => prev.map(step => ({ ...step, status: 'pending', progress: 0 })));

    try {
      // Step 1: Extract audio
      updateStep('extract', 'processing', 25);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate processing
      updateStep('extract', 'completed', 100);

      // Step 2: Transcribe
      updateStep('transcribe', 'processing', 0);
      
      // Step 3: Enhance
      updateStep('enhance', 'processing', 0);
      
      // Step 4: Format
      updateStep('format', 'processing', 0);

      const subtitles = await generateAutoSubtitles(fileToProcess, {
        openaiApiKey: apiKey,
        language: language === 'auto' ? undefined : language,
        style,
        maxWordsPerSegment: maxWords,
      });

      updateStep('transcribe', 'completed', 100);
      updateStep('enhance', 'completed', 100);
      updateStep('format', 'processing', 50);

      // Convert to editor format
      const editorCaptions = convertToEditorCaptions(subtitles);
      setGeneratedSubtitles(editorCaptions);
      
      updateStep('format', 'completed', 100);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Произошла ошибка при генерации субтитров';
      setError(errorMessage);
      
      // Mark current step as error
      const currentStep = steps.find(step => step.status === 'processing');
      if (currentStep) {
        updateStep(currentStep.id, 'error', 0);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApplySubtitles = () => {
    if (generatedSubtitles) {
      onSubtitlesGenerated(generatedSubtitles);
    }
  };

  const handleDownloadSRT = () => {
    if (generatedSubtitles) {
      // Convert back to subtitle format for SRT export
      const subtitleSegments = generatedSubtitles.map(caption => ({
        start: caption.start / 30, // Convert frames to seconds (assuming 30fps)
        end: caption.end / 30,
        text: caption.text,
      }));
      
      const srtContent = exportToSRT(subtitleSegments);
      const blob = new Blob([srtContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'subtitles.srt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const getStepIcon = (status: GenerationStep['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <div className="h-4 w-4 rounded-full border-2 border-gray-300" />;
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wand2 className="h-5 w-5" />
          AI-Powered Subtitles
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* File Upload */}
        {!videoFile && (
          <div className="space-y-2">
            <Label htmlFor="videoFile">Video File</Label>
            <div className="flex items-center gap-2">
              <Input
                id="videoFile"
                type="file"
                accept="video/*,audio/*"
                onChange={handleFileUpload}
                className="flex-1"
              />
              <Upload className="h-4 w-4 text-gray-400" />
            </div>
            {uploadedFile && (
              <p className="text-sm text-green-600">
                Selected file: {uploadedFile.name}
              </p>
            )}
          </div>
        )}

        {/* Settings */}
        {/* Simple Generate Button */}
        <div className="space-y-4">
          <div className="text-center">
            <h3 className="text-lg font-medium text-foreground mb-2">
              Generate Subtitles Automatically
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              AI will automatically transcribe your video and create perfectly timed subtitles
            </p>
          </div>
          
          <Button
            onClick={handleGenerate}
            disabled={isGenerating || !apiKey.trim() || (!videoFile && !uploadedFile)}
            className="w-full h-12 text-base font-medium"
            size="lg"
          >
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Generating Subtitles...
              </>
            ) : (
              <>
                <Wand2 className="mr-2 h-5 w-5" />
                Generate AI Subtitles
              </>
            )}
          </Button>
        </div>
        {/* Progress Steps */}
        {isGenerating && (
          <div className="space-y-3">
            {steps.map((step) => (
              <div key={step.id} className="flex items-center gap-3">
                {getStepIcon(step.status)}
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{step.name}</span>
                    {step.status === 'processing' && (
                      <span className="text-xs text-gray-500">{step.progress}%</span>
                    )}
                  </div>
                  {step.status === 'processing' && (
                    <Progress value={step.progress} className="h-1 mt-1" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Results */}
        {generatedSubtitles && (
          <div className="space-y-4">
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                Субтитры успешно сгенерированы! Найдено {generatedSubtitles.length} сегментов.
              </AlertDescription>
            </Alert>

            {/* Preview */}
            <div className="space-y-2">
              <Label>Предварительный просмотр:</Label>
              <Textarea
                value={generatedSubtitles.map(caption => caption.text).join('\n')}
                readOnly
                className="h-32 text-sm"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <Button onClick={handleApplySubtitles} className="flex-1">
                <CheckCircle className="mr-2 h-4 w-4" />
                Применить к видео
              </Button>
              <Button onClick={handleDownloadSRT} variant="outline">
                <Download className="mr-2 h-4 w-4" />
                Скачать SRT
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

