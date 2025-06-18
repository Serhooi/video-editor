"""
AgentFlow AI Clips v9.0 - ИСПРАВЛЕННАЯ ВЕРСИЯ
Полноценная автоматическая нарезка видео с субтитрами как в Opus.pro

ИСПРАВЛЕНИЯ:
- Фикс ошибки 'TranscriptionSegment' object is not subscriptable
- Правильная обработка результатов Whisper API
- Улучшенная обработка ошибок
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import ffmpeg
from openai import OpenAI

# Инициализация
app = FastAPI(title="AgentFlow AI Clips", version="9.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI клиент
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Директории
UPLOAD_DIR = Path("uploads")
CLIPS_DIR = Path("clips")
AUDIO_DIR = Path("audio")

for dir_path in [UPLOAD_DIR, CLIPS_DIR, AUDIO_DIR]:
    dir_path.mkdir(exist_ok=True)

# Хранилище задач
tasks = {}
generation_tasks = {}

@app.get("/")
async def root():
    return {
        "service": "AgentFlow AI Clips",
        "version": "9.0.0",
        "description": "Automatic video clipping with AI analysis and subtitles",
        "features": [
            "1. Upload video",
            "2. Whisper AI transcription", 
            "3. ChatGPT analysis of best moments",
            "4. Automatic video cutting",
            "5. Subtitle overlay",
            "6. Download ready clips"
        ],
        "endpoints": {
            "analyze": "/api/videos/analyze",
            "status": "/api/videos/{task_id}/status",
            "generate_clips": "/api/clips/generate/{task_id}",
            "download": "/api/clips/{clip_id}/download"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "9.0.0",
        "features": {
            "whisper_transcription": True,
            "gpt4_analysis": True,
            "automatic_cutting": True,
            "subtitle_overlay": True,
            "multiple_formats": True
        }
    }

def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Извлекает аудио из видео"""
    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        audio.close()
        return True
    except Exception as e:
        print(f"Audio extraction error: {e}")
        return False

async def transcribe_full_video(audio_path: str, language: str = "en") -> Dict:
    """Полная транскрибация видео с временными метками - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        
        # ИСПРАВЛЕНИЕ: Правильная обработка результата
        segments = []
        words = []
        
        # Обрабатываем сегменты
        if hasattr(transcription, 'segments') and transcription.segments:
            for segment in transcription.segments:
                # Проверяем тип объекта
                if hasattr(segment, 'start'):
                    # Объект с атрибутами
                    segments.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip()
                    })
                elif isinstance(segment, dict):
                    # Словарь
                    segments.append({
                        "start": segment['start'],
                        "end": segment['end'],
                        "text": segment['text'].strip()
                    })
        
        # Обрабатываем слова
        if hasattr(transcription, 'words') and transcription.words:
            for word in transcription.words:
                if hasattr(word, 'start'):
                    # Объект с атрибутами
                    words.append({
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end
                    })
                elif isinstance(word, dict):
                    # Словарь
                    words.append({
                        "word": word['word'].strip(),
                        "start": word['start'],
                        "end": word['end']
                    })
        
        return {
            "full_text": transcription.text if hasattr(transcription, 'text') else '',
            "segments": segments,
            "words": words,
            "language": transcription.language if hasattr(transcription, 'language') else language
        }
        
    except Exception as e:
        print(f"Transcription error: {e}")
        raise Exception(f"Failed to transcribe video: {str(e)}")

async def analyze_best_moments_with_gpt(transcript: Dict, video_duration: float) -> List[Dict]:
    """ChatGPT анализирует лучшие моменты для клипов"""
    try:
        full_text = transcript["full_text"]
        segments = transcript["segments"]
        
        # Создаем детальный промпт для анализа
        segments_text = "\n".join([
            f"{seg['start']:.1f}s-{seg['end']:.1f}s: {seg['text']}"
            for seg in segments
        ])
        
        prompt = f"""
        Analyze this video transcript and find the BEST moments for viral social media clips.
        
        FULL TRANSCRIPT WITH TIMESTAMPS:
        {segments_text}
        
        VIDEO DURATION: {video_duration:.1f} seconds
        
        Find 2-4 engaging segments that would work as standalone clips (15-90 seconds each).
        
        CRITERIA:
        - Strong hooks (attention-grabbing openings)
        - Complete thoughts/stories
        - High value content
        - Emotional moments
        - Clear speech without long pauses
        
        For each clip, provide:
        1. EXACT start and end times (based on transcript timestamps)
        2. Engaging title for social media
        3. Why this moment is viral-worthy
        4. Best caption style
        
        Return ONLY valid JSON:
        {{
          "clips": [
            {{
              "start_time": 15.2,
              "end_time": 45.8,
              "title": "Mind-Blowing Revelation",
              "description": "Perfect hook with valuable insight",
              "viral_score": 95,
              "caption_style": "beasty",
              "transcript_segment": "exact text from this timeframe"
            }}
          ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert video content analyzer specializing in viral social media clips. Always return valid JSON with precise timestamps."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        analysis_text = response.choices[0].message.content
        
        try:
            analysis_data = json.loads(analysis_text)
            return analysis_data.get("clips", [])
        except json.JSONDecodeError:
            # Fallback: создаем базовые клипы
            return create_fallback_clips(segments, video_duration)
            
    except Exception as e:
        print(f"GPT analysis error: {e}")
        return create_fallback_clips(transcript["segments"], video_duration)

def create_fallback_clips(segments: List[Dict], video_duration: float) -> List[Dict]:
    """Создает базовые клипы если GPT анализ не сработал"""
    clips = []
    
    # Берем первые несколько сегментов
    for i, segment in enumerate(segments[:3]):
        if segment['end'] - segment['start'] >= 15:  # Минимум 15 секунд
            clips.append({
                "start_time": segment['start'],
                "end_time": min(segment['end'] + 10, video_duration),
                "title": f"Highlight {i+1}",
                "description": "Interesting moment from the video",
                "viral_score": 75,
                "caption_style": "beasty",
                "transcript_segment": segment['text']
            })
    
    return clips

def cut_video_with_subtitles(video_path: str, start_time: float, end_time: float, 
                           transcript_segment: str, caption_style: str, 
                           output_path: str, aspect_ratio: str = "9:16") -> bool:
    """Нарезает видео и добавляет субтитры"""
    try:
        # Загружаем видео
        video = VideoFileClip(video_path).subclip(start_time, end_time)
        
        # Изменяем соотношение сторон для 9:16
        if aspect_ratio == "9:16":
            # Обрезаем по центру для вертикального формата
            target_width = int(video.h * 9 / 16)
            if target_width <= video.w:
                # Обрезаем ширину
                x_center = video.w / 2
                x1 = int(x_center - target_width / 2)
                x2 = int(x_center + target_width / 2)
                video = video.crop(x1=x1, x2=x2)
            else:
                # Добавляем черные полосы
                video = video.resize(height=int(target_width * 16 / 9))
        
        # Стили субтитров
        caption_styles = {
            "beasty": {"fontsize": 60, "color": "white", "stroke_color": "black", "stroke_width": 3},
            "karaoke": {"fontsize": 65, "color": "yellow", "stroke_color": "red", "stroke_width": 2},
            "deep_diver": {"fontsize": 55, "color": "lightblue", "stroke_color": "darkblue", "stroke_width": 2},
            "youshael": {"fontsize": 70, "color": "gold", "stroke_color": "black", "stroke_width": 4}
        }
        
        style = caption_styles.get(caption_style, caption_styles["beasty"])
        
        # Создаем субтитры
        subtitle = TextClip(
            transcript_segment,
            fontsize=style["fontsize"],
            color=style["color"],
            stroke_color=style["stroke_color"],
            stroke_width=style["stroke_width"],
            font="Arial-Bold",
            method="caption",
            size=(video.w * 0.8, None)
        ).set_position(("center", "bottom")).set_duration(video.duration)
        
        # Композитное видео
        final_video = CompositeVideoClip([video, subtitle])
        
        # Сохраняем
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        # Очищаем память
        video.close()
        subtitle.close()
        final_video.close()
        
        return True
        
    except Exception as e:
        print(f"Video cutting error: {e}")
        return False

@app.post("/api/videos/analyze")
async def analyze_video(file: UploadFile = File(...), language: str = Form("en")):
    """Загрузка и анализ видео"""
    try:
        # Создаем уникальный ID задачи
        task_id = str(uuid.uuid4())
        
        # Сохраняем файл
        file_extension = file.filename.split('.')[-1]
        video_filename = f"{task_id}_{file.filename}"
        video_path = UPLOAD_DIR / video_filename
        
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Инициализируем задачу
        tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "file_path": str(video_path),
            "language": language
        }
        
        # Запускаем анализ в фоне
        asyncio.create_task(process_video_analysis(task_id, str(video_path), language))
        
        return {"task_id": task_id, "status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_video_analysis(task_id: str, video_path: str, language: str):
    """Фоновая обработка анализа видео"""
    try:
        # Обновляем прогресс
        tasks[task_id]["progress"] = 10
        
        # Извлекаем аудио
        audio_path = AUDIO_DIR / f"{task_id}.wav"
        if not extract_audio_from_video(video_path, str(audio_path)):
            raise Exception("Failed to extract audio")
        
        tasks[task_id]["progress"] = 30
        
        # Транскрибируем
        transcript = await transcribe_full_video(str(audio_path), language)
        tasks[task_id]["transcript"] = transcript
        tasks[task_id]["progress"] = 70
        
        # Получаем длительность видео
        video = VideoFileClip(video_path)
        video_duration = video.duration
        video.close()
        
        # Анализируем лучшие моменты
        best_moments = await analyze_best_moments_with_gpt(transcript, video_duration)
        tasks[task_id]["best_moments"] = best_moments
        tasks[task_id]["video_duration"] = video_duration
        
        # Завершаем
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        
        # Удаляем временный аудио файл
        if audio_path.exists():
            audio_path.unlink()
            
    except Exception as e:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)

@app.get("/api/videos/{task_id}/status")
async def get_video_status(task_id: str):
    """Получение статуса анализа видео"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return tasks[task_id]

@app.post("/api/clips/generate/{task_id}")
async def generate_clips(task_id: str, caption_style: str = Form("beasty")):
    """Генерация клипов с субтитрами"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video analysis not completed")
    
    # Создаем задачу генерации
    generation_task_id = str(uuid.uuid4())
    generation_tasks[generation_task_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "clips": []
    }
    
    # Запускаем генерацию в фоне
    asyncio.create_task(process_clips_generation(
        generation_task_id, task_id, caption_style
    ))
    
    return {"generation_task_id": generation_task_id, "status": "processing"}

async def process_clips_generation(generation_task_id: str, task_id: str, caption_style: str):
    """Фоновая генерация клипов"""
    try:
        task_data = tasks[task_id]
        video_path = task_data["file_path"]
        best_moments = task_data["best_moments"]
        
        clips = []
        total_clips = len(best_moments)
        
        for i, moment in enumerate(best_moments):
            # Обновляем прогресс
            progress = int((i / total_clips) * 100)
            generation_tasks[generation_task_id]["progress"] = progress
            
            # Создаем клип
            clip_id = str(uuid.uuid4())
            clip_filename = f"clip_{clip_id}.mp4"
            clip_path = CLIPS_DIR / clip_filename
            
            success = cut_video_with_subtitles(
                video_path=video_path,
                start_time=moment["start_time"],
                end_time=moment["end_time"],
                transcript_segment=moment["transcript_segment"],
                caption_style=caption_style,
                output_path=str(clip_path),
                aspect_ratio="9:16"
            )
            
            if success:
                clips.append({
                    "clip_id": clip_id,
                    "title": moment["title"],
                    "description": moment["description"],
                    "viral_score": moment["viral_score"],
                    "duration": moment["end_time"] - moment["start_time"],
                    "file_path": str(clip_path),
                    "download_url": f"/api/clips/{clip_id}/download"
                })
        
        # Завершаем генерацию
        generation_tasks[generation_task_id]["status"] = "completed"
        generation_tasks[generation_task_id]["progress"] = 100
        generation_tasks[generation_task_id]["clips"] = clips
        
    except Exception as e:
        generation_tasks[generation_task_id]["status"] = "error"
        generation_tasks[generation_task_id]["error"] = str(e)

@app.get("/api/clips/generation/{generation_task_id}/status")
async def get_generation_status(generation_task_id: str):
    """Получение статуса генерации клипов"""
    if generation_task_id not in generation_tasks:
        raise HTTPException(status_code=404, detail="Generation task not found")
    
    return generation_tasks[generation_task_id]

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивание готового клипа"""
    clip_path = CLIPS_DIR / f"clip_{clip_id}.mp4"
    
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

