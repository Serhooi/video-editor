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
  const [apiKey, setApiKey] = useState('');
  const [language, setLanguage] = useState('ru');
  const [style, setStyle] = useState<'casual' | 'formal' | 'social-media' | 'educational'>('casual');
  const [maxWords, setMaxWords] = useState(8);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedSubtitles, setGeneratedSubtitles] = useState<any[] | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  
  const [steps, setSteps] = useState<GenerationStep[]>([
    { id: 'extract', name: 'Извлечение аудио из видео', status: 'pending', progress: 0 },
    { id: 'transcribe', name: 'Распознавание речи (Whisper AI)', status: 'pending', progress: 0 },
    { id: 'enhance', name: 'Обработка текста (ChatGPT)', status: 'pending', progress: 0 },
    { id: 'format', name: 'Форматирование субтитров', status: 'pending', progress: 0 },
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
      setError('Пожалуйста, выберите видео или аудио файл');
    }
  };

  const handleGenerate = async () => {
    const fileToProcess = uploadedFile || videoFile;
    
    if (!fileToProcess) {
      setError('Пожалуйста, выберите видео файл');
      return;
    }

    if (!apiKey.trim()) {
      setError('Пожалуйста, введите OpenAI API ключ');
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
          Автоматические субтитры с ИИ
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* API Key Input */}
        <div className="space-y-2">
          <Label htmlFor="apiKey">OpenAI API Ключ</Label>
          <Input
            id="apiKey"
            type="password"
            placeholder="sk-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="font-mono"
          />
          <p className="text-sm text-gray-500">
            Получите ключ на{' '}
            <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
              platform.openai.com
            </a>
          </p>
        </div>

        {/* File Upload */}
        {!videoFile && (
          <div className="space-y-2">
            <Label htmlFor="videoFile">Видео файл</Label>
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
                Выбран файл: {uploadedFile.name}
              </p>
            )}
          </div>
        )}

        {/* Settings */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="language">Язык</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Автоопределение</SelectItem>
                <SelectItem value="ru">Русский</SelectItem>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="es">Español</SelectItem>
                <SelectItem value="fr">Français</SelectItem>
                <SelectItem value="de">Deutsch</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="style">Стиль</Label>
            <Select value={style} onValueChange={(value: any) => setStyle(value)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="casual">Разговорный</SelectItem>
                <SelectItem value="formal">Официальный</SelectItem>
                <SelectItem value="social-media">Соцсети</SelectItem>
                <SelectItem value="educational">Обучающий</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="maxWords">Слов в сегменте</Label>
            <Input
              id="maxWords"
              type="number"
              min="3"
              max="15"
              value={maxWords}
              onChange={(e) => setMaxWords(parseInt(e.target.value) || 8)}
            />
          </div>
        </div>

        {/* Generate Button */}
        <Button
          onClick={handleGenerate}
          disabled={isGenerating || !apiKey.trim() || (!videoFile && !uploadedFile)}
          className="w-full"
          size="lg"
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Генерация субтитров...
            </>
          ) : (
            <>
              <Wand2 className="mr-2 h-4 w-4" />
              Сгенерировать субтитры
            </>
          )}
        </Button>

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

