"""
AgentFlow AI Clips Platform - ПОЛНОЦЕННЫЙ АВТОМАТИЧЕСКИЙ ПАЙПЛАЙН
Как Opus.pro: анализ → нарезка → субтитры → готовые клипы
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
import json
import os
import shutil
from datetime import datetime
import subprocess
import tempfile
from pathlib import Path
import requests
from openai import OpenAI
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import ffmpeg

app = FastAPI(title="AgentFlow AI Clips Platform", version="8.0.0")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройка OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Глобальные переменные для хранения состояния
analysis_tasks = {}
clip_generation_tasks = {}

# Директории для файлов
UPLOAD_DIR = Path("uploads")
CLIPS_DIR = Path("clips")
AUDIO_DIR = Path("audio")
SUBTITLES_DIR = Path("subtitles")

# Создаем директории
for dir_path in [UPLOAD_DIR, CLIPS_DIR, AUDIO_DIR, SUBTITLES_DIR]:
    dir_path.mkdir(exist_ok=True)

# Стили субтитров
SUBTITLE_STYLES = {
    "beasty": {
        "font": "Arial-Bold",
        "fontsize": 52,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 3,
        "position": "center"
    },
    "karaoke": {
        "font": "Arial-Black",
        "fontsize": 48,
        "color": "yellow",
        "stroke_color": "red",
        "stroke_width": 2,
        "position": "bottom"
    },
    "deep_diver": {
        "font": "Roboto-Bold",
        "fontsize": 44,
        "color": "cyan",
        "stroke_color": "navy",
        "stroke_width": 2,
        "position": "bottom"
    },
    "youshael": {
        "font": "Montserrat-Bold",
        "fontsize": 46,
        "color": "gold",
        "stroke_color": "black",
        "stroke_width": 3,
        "position": "top"
    }
}

@app.get("/")
async def root():
    return {
        "service": "AgentFlow AI Clips Platform",
        "version": "8.0.0",
        "description": "Automatic video clipping with AI analysis",
        "workflow": [
            "1. Upload video",
            "2. Whisper transcription",
            "3. ChatGPT analysis",
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
        "version": "8.0.0",
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
    """Полная транскрибация видео с временными метками"""
    try:
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        
        # Обрабатываем результат
        segments = []
        words = []
        
        if hasattr(transcription, 'segments') and transcription.segments:
            for segment in transcription.segments:
                segments.append({
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": segment['text'].strip()
                })
        
        if hasattr(transcription, 'words') and transcription.words:
            for word in transcription.words:
                words.append({
                    "word": word['word'].strip(),
                    "start": word['start'],
                    "end": word['end']
                })
        
        return {
            "full_text": getattr(transcription, 'text', ''),
            "segments": segments,
            "words": words,
            "language": getattr(transcription, 'language', language)
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
        return create_fallback_clips(transcript.get("segments", []), video_duration)

def create_fallback_clips(segments: List[Dict], video_duration: float) -> List[Dict]:
    """Создает базовые клипы если GPT недоступен"""
    clips = []
    
    # Первый клип (начало)
    if segments and video_duration > 30:
        clips.append({
            "start_time": 0.0,
            "end_time": min(30.0, video_duration),
            "title": "Video Opening",
            "description": "Engaging introduction",
            "viral_score": 85,
            "caption_style": "beasty",
            "transcript_segment": segments[0]["text"] if segments else ""
        })
    
    # Второй клип (середина)
    if video_duration > 90:
        mid_point = video_duration / 2
        clips.append({
            "start_time": max(30.0, mid_point - 15),
            "end_time": min(video_duration, mid_point + 15),
            "title": "Key Moment",
            "description": "Main content highlight",
            "viral_score": 88,
            "caption_style": "deep_diver",
            "transcript_segment": "Key content from video"
        })
    
    return clips

def create_subtitle_file(words: List[Dict], start_time: float, end_time: float, clip_id: str) -> str:
    """Создает SRT файл субтитров для клипа"""
    subtitle_path = SUBTITLES_DIR / f"{clip_id}.srt"
    
    # Фильтруем слова для данного временного отрезка
    clip_words = [
        word for word in words 
        if start_time <= word["start"] <= end_time
    ]
    
    if not clip_words:
        return str(subtitle_path)
    
    # Группируем слова в субтитры (по 3-5 слов)
    subtitles = []
    current_subtitle = []
    words_per_subtitle = 4
    
    for i, word in enumerate(clip_words):
        current_subtitle.append(word)
        
        if len(current_subtitle) >= words_per_subtitle or i == len(clip_words) - 1:
            if current_subtitle:
                start = current_subtitle[0]["start"] - start_time  # Относительное время
                end = current_subtitle[-1]["end"] - start_time
                text = " ".join([w["word"] for w in current_subtitle])
                
                subtitles.append({
                    "start": max(0, start),
                    "end": end,
                    "text": text.strip()
                })
                current_subtitle = []
    
    # Записываем SRT файл
    with open(subtitle_path, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles, 1):
            start_time_str = format_srt_time(sub["start"])
            end_time_str = format_srt_time(sub["end"])
            
            f.write(f"{i}\n")
            f.write(f"{start_time_str} --> {end_time_str}\n")
            f.write(f"{sub['text']}\n\n")
    
    return str(subtitle_path)

def format_srt_time(seconds: float) -> str:
    """Форматирует время для SRT файла"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

async def cut_video_with_subtitles(
    video_path: str, 
    start_time: float, 
    end_time: float, 
    subtitle_path: str,
    output_path: str,
    style: str = "beasty"
) -> bool:
    """Нарезает видео и добавляет субтитры с помощью FFmpeg"""
    try:
        style_config = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES["beasty"])
        
        # FFmpeg команда для нарезки и добавления субтитров
        (
            ffmpeg
            .input(video_path, ss=start_time, t=end_time - start_time)
            .filter('subtitles', subtitle_path, 
                   force_style=f"FontName={style_config['font']},"
                              f"FontSize={style_config['fontsize']},"
                              f"PrimaryColour=&H{style_config['color'][1:]},"
                              f"OutlineColour=&H{style_config['stroke_color'][1:]},"
                              f"Outline={style_config['stroke_width']}")
            .output(output_path, vcodec='libx264', acodec='aac')
            .overwrite_output()
            .run(quiet=True)
        )
        
        return True
        
    except Exception as e:
        print(f"Video cutting error: {e}")
        # Fallback: простая нарезка без субтитров
        try:
            (
                ffmpeg
                .input(video_path, ss=start_time, t=end_time - start_time)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except:
            return False

@app.post("/api/videos/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """Загружает и анализирует видео"""
    task_id = str(uuid.uuid4())
    
    # Сохраняем файл
    file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Инициализируем задачу
    analysis_tasks[task_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "file_path": str(file_path),
        "language": language
    }
    
    # Запускаем анализ в фоне
    background_tasks.add_task(process_full_video_analysis, task_id)
    
    return {"task_id": task_id, "status": "processing"}

async def process_full_video_analysis(task_id: str):
    """ПОЛНЫЙ анализ видео: транскрибация + анализ лучших моментов"""
    try:
        task = analysis_tasks[task_id]
        video_path = task["file_path"]
        
        # 1. Получаем информацию о видео
        analysis_tasks[task_id]["status"] = "Analyzing video properties"
        analysis_tasks[task_id]["progress"] = 10
        
        video = VideoFileClip(video_path)
        video_duration = video.duration
        video.close()
        
        # 2. Извлекаем аудио
        analysis_tasks[task_id]["status"] = "Extracting audio"
        analysis_tasks[task_id]["progress"] = 20
        
        audio_path = str(AUDIO_DIR / f"{task_id}.wav")
        if not extract_audio_from_video(video_path, audio_path):
            raise Exception("Failed to extract audio")
        
        # 3. ПОЛНАЯ транскрибация через Whisper
        analysis_tasks[task_id]["status"] = "Transcribing with Whisper AI"
        analysis_tasks[task_id]["progress"] = 50
        
        transcript = await transcribe_full_video(audio_path, task["language"])
        
        # 4. Анализ лучших моментов через ChatGPT
        analysis_tasks[task_id]["status"] = "Analyzing best moments with ChatGPT"
        analysis_tasks[task_id]["progress"] = 80
        
        best_clips = await analyze_best_moments_with_gpt(transcript, video_duration)
        
        # 5. Сохраняем результат
        result = {
            "video_duration": video_duration,
            "transcript": transcript,
            "best_clips": best_clips,
            "total_clips": len(best_clips)
        }
        
        analysis_tasks[task_id]["status"] = "completed"
        analysis_tasks[task_id]["progress"] = 100
        analysis_tasks[task_id]["result"] = result
        
        # Удаляем временный аудио файл
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
    except Exception as e:
        analysis_tasks[task_id]["status"] = "error"
        analysis_tasks[task_id]["error"] = str(e)

@app.get("/api/videos/{task_id}/status")
async def get_analysis_status(task_id: str):
    """Получает статус анализа видео"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return analysis_tasks[task_id]

@app.post("/api/clips/generate/{task_id}")
async def generate_clips(
    task_id: str,
    background_tasks: BackgroundTasks,
    caption_style: str = Form("beasty")
):
    """Генерирует реальные видео клипы с субтитрами"""
    if task_id not in analysis_tasks:
        raise HTTPException(status_code=404, detail="Analysis task not found")
    
    analysis_task = analysis_tasks[task_id]
    if analysis_task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed")
    
    generation_task_id = str(uuid.uuid4())
    
    # Инициализируем задачу генерации
    clip_generation_tasks[generation_task_id] = {
        "status": "processing",
        "progress": 0,
        "analysis_task_id": task_id,
        "caption_style": caption_style,
        "created_at": datetime.now().isoformat(),
        "clips": []
    }
    
    # Запускаем генерацию в фоне
    background_tasks.add_task(generate_video_clips, generation_task_id)
    
    return {"generation_task_id": generation_task_id, "status": "processing"}

async def generate_video_clips(generation_task_id: str):
    """РЕАЛЬНАЯ генерация видео клипов с субтитрами"""
    try:
        gen_task = clip_generation_tasks[generation_task_id]
        analysis_task_id = gen_task["analysis_task_id"]
        analysis_result = analysis_tasks[analysis_task_id]["result"]
        video_path = analysis_tasks[analysis_task_id]["file_path"]
        
        best_clips = analysis_result["best_clips"]
        transcript = analysis_result["transcript"]
        words = transcript["words"]
        
        generated_clips = []
        
        for i, clip_data in enumerate(best_clips):
            try:
                clip_generation_tasks[generation_task_id]["status"] = f"Generating clip {i+1}/{len(best_clips)}"
                clip_generation_tasks[generation_task_id]["progress"] = int((i / len(best_clips)) * 90)
                
                clip_id = f"{generation_task_id}_clip_{i+1}"
                start_time = clip_data["start_time"]
                end_time = clip_data["end_time"]
                
                # 1. Создаем субтитры для клипа
                subtitle_path = create_subtitle_file(words, start_time, end_time, clip_id)
                
                # 2. Нарезаем видео с субтитрами
                output_path = str(CLIPS_DIR / f"{clip_id}.mp4")
                
                success = await cut_video_with_subtitles(
                    video_path=video_path,
                    start_time=start_time,
                    end_time=end_time,
                    subtitle_path=subtitle_path,
                    output_path=output_path,
                    style=gen_task["caption_style"]
                )
                
                if success:
                    generated_clips.append({
                        "clip_id": clip_id,
                        "title": clip_data["title"],
                        "description": clip_data["description"],
                        "duration": end_time - start_time,
                        "viral_score": clip_data["viral_score"],
                        "file_path": output_path,
                        "download_url": f"/api/clips/{clip_id}/download"
                    })
                
            except Exception as e:
                print(f"Error generating clip {i+1}: {e}")
                continue
        
        # Завершаем генерацию
        clip_generation_tasks[generation_task_id]["status"] = "completed"
        clip_generation_tasks[generation_task_id]["progress"] = 100
        clip_generation_tasks[generation_task_id]["clips"] = generated_clips
        
    except Exception as e:
        clip_generation_tasks[generation_task_id]["status"] = "error"
        clip_generation_tasks[generation_task_id]["error"] = str(e)

@app.get("/api/clips/generation/{generation_task_id}/status")
async def get_generation_status(generation_task_id: str):
    """Получает статус генерации клипов"""
    if generation_task_id not in clip_generation_tasks:
        raise HTTPException(status_code=404, detail="Generation task not found")
    
    return clip_generation_tasks[generation_task_id]

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивает готовый клип"""
    clip_path = CLIPS_DIR / f"{clip_id}.mp4"
    
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=f"{clip_id}.mp4"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

