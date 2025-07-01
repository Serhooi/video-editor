/**
 * AI Subtitles API
 * 
 * Integrates with OpenAI Whisper for speech-to-text transcription
 * and ChatGPT for subtitle formatting and enhancement
 */

interface SubtitleSegment {
  start: number;
  end: number;
  text: string;
  confidence?: number;
}

interface WhisperResponse {
  text: string;
  segments: Array<{
    start: number;
    end: number;
    text: string;
  }>;
}

interface ChatGPTSubtitleRequest {
  transcript: string;
  maxWordsPerSegment?: number;
  style?: 'casual' | 'formal' | 'social-media' | 'educational';
  language?: string;
}

/**
 * Extract audio from video file for Whisper processing
 */
export const extractAudioFromVideo = async (videoFile: File): Promise<File> => {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    video.onloadedmetadata = () => {
      // Create audio context for extraction
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = audioContext.createMediaElementSource(video);
      const destination = audioContext.createMediaStreamDestination();
      
      source.connect(destination);
      
      const mediaRecorder = new MediaRecorder(destination.stream);
      const chunks: BlobPart[] = [];
      
      mediaRecorder.ondataavailable = (event) => {
        chunks.push(event.data);
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(chunks, { type: 'audio/wav' });
        const audioFile = new File([audioBlob], 'audio.wav', { type: 'audio/wav' });
        resolve(audioFile);
      };
      
      mediaRecorder.start();
      video.play();
      
      video.onended = () => {
        mediaRecorder.stop();
      };
    };
    
    video.onerror = () => reject(new Error('Failed to load video'));
    video.src = URL.createObjectURL(videoFile);
  });
};

/**
 * Transcribe audio using OpenAI Whisper API
 */
export const transcribeWithWhisper = async (
  audioFile: File,
  apiKey: string,
  language?: string
): Promise<WhisperResponse> => {
  const formData = new FormData();
  formData.append('file', audioFile);
  formData.append('model', 'whisper-1');
  formData.append('response_format', 'verbose_json');
  formData.append('timestamp_granularities[]', 'segment');
  
  if (language) {
    formData.append('language', language);
  }

  const response = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Whisper API error: ${error.error?.message || 'Unknown error'}`);
  }

  return response.json();
};

/**
 * Enhance and format subtitles using ChatGPT
 */
export const enhanceSubtitlesWithChatGPT = async (
  request: ChatGPTSubtitleRequest,
  apiKey: string
): Promise<SubtitleSegment[]> => {
  const { transcript, maxWordsPerSegment = 8, style = 'casual', language = 'ru' } = request;

  const prompt = `
Ты профессиональный редактор субтитров. Твоя задача - разбить транскрипт на оптимальные сегменты для субтитров.

ТРЕБОВАНИЯ:
- Максимум ${maxWordsPerSegment} слов на сегмент
- Стиль: ${style}
- Язык: ${language}
- Сохраняй естественные паузы и смысловые группы
- Убирай слова-паразиты (эм, ах, ну и т.д.)
- Исправляй грамматические ошибки
- Делай текст читаемым и понятным

ТРАНСКРИПТ:
${transcript}

Верни результат в формате JSON массива:
[
  {
    "text": "Текст субтитра",
    "duration": 3.5
  }
]

Где duration - рекомендуемая длительность показа в секундах (обычно 2-4 секунды).
`;

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content: 'Ты профессиональный редактор субтитров. Отвечай только в формате JSON без дополнительных комментариев.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.3,
      max_tokens: 2000,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`ChatGPT API error: ${error.error?.message || 'Unknown error'}`);
  }

  const result = await response.json();
  const content = result.choices[0].message.content;
  
  try {
    const subtitleData = JSON.parse(content);
    
    // Convert to SubtitleSegment format with timing
    let currentTime = 0;
    return subtitleData.map((item: any, index: number) => {
      const segment: SubtitleSegment = {
        start: currentTime,
        end: currentTime + item.duration,
        text: item.text,
        confidence: 1.0
      };
      currentTime = segment.end + 0.5; // Add 0.5s gap between subtitles
      return segment;
    });
  } catch (error) {
    throw new Error('Failed to parse ChatGPT response');
  }
};

/**
 * Generate automatic subtitles from video file
 */
export const generateAutoSubtitles = async (
  videoFile: File,
  options: {
    openaiApiKey: string;
    language?: string;
    style?: 'casual' | 'formal' | 'social-media' | 'educational';
    maxWordsPerSegment?: number;
  }
): Promise<SubtitleSegment[]> => {
  const { openaiApiKey, language, style, maxWordsPerSegment } = options;

  try {
    // Step 1: Extract audio from video
    console.log('Extracting audio from video...');
    const audioFile = await extractAudioFromVideo(videoFile);

    // Step 2: Transcribe with Whisper
    console.log('Transcribing audio with Whisper...');
    const whisperResult = await transcribeWithWhisper(audioFile, openaiApiKey, language);

    // Step 3: Enhance with ChatGPT
    console.log('Enhancing subtitles with ChatGPT...');
    const enhancedSubtitles = await enhanceSubtitlesWithChatGPT(
      {
        transcript: whisperResult.text,
        maxWordsPerSegment,
        style,
        language,
      },
      openaiApiKey
    );

    return enhancedSubtitles;
  } catch (error) {
    console.error('Auto subtitle generation failed:', error);
    throw error;
  }
};

/**
 * Convert SubtitleSegment array to editor caption format
 */
export const convertToEditorCaptions = (
  subtitles: SubtitleSegment[],
  fps: number = 30
): any[] => {
  return subtitles.map((subtitle, index) => ({
    id: `caption-${index}`,
    start: Math.round(subtitle.start * fps), // Convert to frames
    end: Math.round(subtitle.end * fps),
    text: subtitle.text,
    style: {
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#FFFFFF',
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      textAlign: 'center',
      padding: '8px 16px',
      borderRadius: '4px',
    },
    position: {
      x: '50%',
      y: '85%',
    },
  }));
};

/**
 * Save subtitles as SRT file
 */
export const exportToSRT = (subtitles: SubtitleSegment[]): string => {
  return subtitles
    .map((subtitle, index) => {
      const startTime = formatSRTTime(subtitle.start);
      const endTime = formatSRTTime(subtitle.end);
      
      return `${index + 1}\n${startTime} --> ${endTime}\n${subtitle.text}\n`;
    })
    .join('\n');
};

/**
 * Format time for SRT format (HH:MM:SS,mmm)
 */
const formatSRTTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const milliseconds = Math.floor((seconds % 1) * 1000);
  
  return `${hours.toString().padStart(2, '0')}:${minutes
    .toString()
    .padStart(2, '0')}:${secs.toString().padStart(2, '0')},${milliseconds
    .toString()
    .padStart(3, '0')}`;
};

