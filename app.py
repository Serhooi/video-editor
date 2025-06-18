"""
AgentFlow AI Clips v14.0 - МОДУЛЬНАЯ АРХИТЕКТУРА
Разделение видео и субтитров для редактирования на фронтенде

НОВАЯ АРХИТЕКТУРА:
1. /api/videos/analyze - анализ и транскрибация
2. /api/clips/cut - нарезка ЧИСТОГО видео (без субтитров)
3. /api/subtitles/generate - создание данных субтитров
4. /api/clips/render - финальный рендер с субтитрами (опционально)

ПРЕИМУЩЕСТВА:
- Фронтенд может редактировать субтитры
- Гибкость в стилизации
- Возможность превью
- Быстрая итерация
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import json
import asyncio
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiofiles
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
app = FastAPI(title="AgentFlow AI Clips", version="14.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI клиент
client = None
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
        logger.info("✅ OpenAI client initialized")
    else:
        logger.warning("⚠️ OpenAI API key not found")
except Exception as e:
    logger.error(f"❌ OpenAI client initialization failed: {e}")

# Директории
UPLOAD_DIR = Path("uploads")
CLIPS_DIR = Path("clips")
AUDIO_DIR = Path("audio")
SUBTITLES_DIR = Path("subtitles")

for dir_path in [UPLOAD_DIR, CLIPS_DIR, AUDIO_DIR, SUBTITLES_DIR]:
    dir_path.mkdir(exist_ok=True)

# Хранилище задач
tasks = {}
clip_tasks = {}
subtitle_tasks = {}

def get_subtitle_styles():
    """Возвращает доступные стили субтитров"""
    return {
        "beasty": {
            "name": "Beasty",
            "description": "Bold white text with black outline",
            "fontsize": 80,
            "fontcolor": "#FFFFFF",
            "bordercolor": "#000000",
            "borderwidth": 4,
            "background": "rgba(0,0,0,0.5)",
            "position": "bottom"
        },
        "karaoke": {
            "name": "Karaoke",
            "description": "Yellow text with red outline",
            "fontsize": 75,
            "fontcolor": "#FFFF00",
            "bordercolor": "#FF0000",
            "borderwidth": 3,
            "background": "rgba(0,0,0,0.7)",
            "position": "bottom"
        },
        "deep_diver": {
            "name": "Deep Diver",
            "description": "Cyan text with navy outline",
            "fontsize": 70,
            "fontcolor": "#00FFFF",
            "bordercolor": "#000080",
            "borderwidth": 3,
            "background": "rgba(0,0,139,0.6)",
            "position": "bottom"
        },
        "youshael": {
            "name": "Youshael",
            "description": "White text with purple outline",
            "fontsize": 85,
            "fontcolor": "#FFFFFF",
            "bordercolor": "#800080",
            "borderwidth": 5,
            "background": "rgba(128,0,128,0.4)",
            "position": "bottom"
        }
    }

def split_text_into_lines(text: str, max_chars_per_line: int = 25) -> List[str]:
    """Разбивает текст на строки для субтитров"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + " " + word) <= max_chars_per_line:
            current_line += (" " + word) if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

def extract_audio_with_ffmpeg(video_path: str, audio_path: str) -> bool:
    """Извлекает аудио из видео через FFmpeg"""
    try:
        logger.info(f"Extracting audio: {video_path} -> {audio_path}")
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            '-y', audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            logger.info("✅ Audio extraction successful")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return False

async def transcribe_full_video(audio_path: str, language: str = "en") -> Dict:
    """Полная транскрибация видео с временными метками"""
    if not client:
        raise Exception("OpenAI client not available")
        
    try:
        logger.info(f"Starting transcription: {audio_path}")
        
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json"
            )
        
        segments = []
        words = []
        
        if hasattr(transcription, 'segments') and transcription.segments:
            for segment in transcription.segments:
                if hasattr(segment, 'start'):
                    segments.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip()
                    })
                elif isinstance(segment, dict):
                    segments.append({
                        "start": segment.get('start', 0),
                        "end": segment.get('end', 0),
                        "text": segment.get('text', '').strip()
                    })
        
        if not segments and hasattr(transcription, 'text'):
            full_text = transcription.text
            sentences = full_text.split('. ')
            duration_per_sentence = 5.0
            
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    segments.append({
                        "start": i * duration_per_sentence,
                        "end": (i + 1) * duration_per_sentence,
                        "text": sentence.strip()
                    })
        
        if not words and segments:
            for segment in segments:
                segment_words = segment['text'].split()
                word_duration = (segment['end'] - segment['start']) / len(segment_words) if segment_words else 1.0
                
                for j, word in enumerate(segment_words):
                    words.append({
                        "word": word,
                        "start": segment['start'] + j * word_duration,
                        "end": segment['start'] + (j + 1) * word_duration
                    })
        
        result = {
            "full_text": transcription.text if hasattr(transcription, 'text') else '',
            "segments": segments,
            "words": words,
            "language": transcription.language if hasattr(transcription, 'language') else language
        }
        
        logger.info(f"✅ Transcription completed: {len(segments)} segments, {len(words)} words")
        return result
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise Exception(f"Failed to transcribe video: {str(e)}")

async def analyze_best_moments_with_gpt(transcript: Dict, video_duration: float) -> List[Dict]:
    """ChatGPT анализирует лучшие моменты для клипов"""
    if not client:
        return create_fallback_clips(transcript["segments"], video_duration)
        
    try:
        logger.info("Starting GPT analysis...")
        
        full_text = transcript["full_text"]
        segments = transcript["segments"]
        
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
        
        Return ONLY valid JSON:
        {{
          "clips": [
            {{
              "start_time": 15.2,
              "end_time": 45.8,
              "title": "Mind-Blowing Revelation",
              "description": "Perfect hook with valuable insight",
              "viral_score": 95,
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
        logger.info(f"GPT response: {analysis_text[:200]}...")
        
        try:
            analysis_data = json.loads(analysis_text)
            clips = analysis_data.get("clips", [])
            logger.info(f"✅ GPT analysis completed: {len(clips)} clips found")
            return clips
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return create_fallback_clips(segments, video_duration)
            
    except Exception as e:
        logger.error(f"GPT analysis failed: {e}")
        return create_fallback_clips(transcript["segments"], video_duration)

def create_fallback_clips(segments: List[Dict], video_duration: float) -> List[Dict]:
    """Создает базовые клипы если GPT анализ не сработал"""
    logger.info("Creating fallback clips...")
    clips = []
    
    for i, segment in enumerate(segments[:3]):
        if segment['end'] - segment['start'] >= 10:
            clips.append({
                "start_time": segment['start'],
                "end_time": min(segment['end'] + 10, video_duration),
                "title": f"Highlight {i+1}",
                "description": "Interesting moment from the video",
                "viral_score": 75,
                "transcript_segment": segment['text']
            })
    
    logger.info(f"✅ Created {len(clips)} fallback clips")
    return clips

def cut_clean_video(video_path: str, start_time: float, end_time: float, 
                   output_path: str, aspect_ratio: str = "9:16") -> bool:
    """Нарезает ЧИСТОЕ видео без субтитров"""
    try:
        logger.info(f"Cutting clean video: {start_time}-{end_time}s")
        
        duration = end_time - start_time
        
        if aspect_ratio == "9:16":
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', 'crop=ih*9/16:ih,scale=1080:1920',
                '-c:v', 'libx264', '-preset', 'medium',
                '-c:a', 'aac',
                '-b:v', '4000k',
                '-r', '30',
                '-avoid_negative_ts', 'make_zero',
                '-y', output_path
            ]
        else:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264', '-preset', 'medium',
                '-c:a', 'aac',
                '-avoid_negative_ts', 'make_zero',
                '-y', output_path
            ]
        
        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            logger.info(f"✅ Clean video cut successful: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg cutting error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Clean video cutting failed: {e}")
        return False

@app.get("/")
async def root():
    return {
        "service": "AgentFlow AI Clips",
        "version": "14.0.0",
        "description": "Modular video clipping with editable subtitles",
        "architecture": "Separated video cutting and subtitle generation",
        "subtitle_styles": list(get_subtitle_styles().keys()),
        "workflow": [
            "1. POST /api/videos/analyze - Upload & analyze video",
            "2. POST /api/clips/cut - Cut clean video clips",
            "3. POST /api/subtitles/generate - Generate subtitle data",
            "4. Frontend: Edit subtitles as needed",
            "5. POST /api/clips/render - Final render with subtitles (optional)"
        ]
    }

@app.get("/health")
async def health_check():
    deps = {
        "ffmpeg": False,
        "openai": client is not None
    }
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        deps["ffmpeg"] = result.returncode == 0
    except:
        pass
    
    return {
        "status": "healthy",
        "version": "14.0.0",
        "dependencies": deps,
        "features": {
            "modular_architecture": True,
            "editable_subtitles": True,
            "clean_video_cutting": True,
            "subtitle_styles": len(get_subtitle_styles())
        }
    }

@app.get("/api/subtitle-styles")
async def get_available_subtitle_styles():
    """Получение доступных стилей субтитров"""
    return {"styles": get_subtitle_styles()}

# 1. АНАЛИЗ ВИДЕО (как раньше)
@app.post("/api/videos/analyze")
async def analyze_video(file: UploadFile = File(...), language: str = Form("en")):
    """Загрузка и анализ видео"""
    try:
        logger.info(f"Analyzing video: {file.filename}")
        
        task_id = str(uuid.uuid4())
        
        file_extension = file.filename.split('.')[-1]
        video_filename = f"{task_id}_{file.filename}"
        video_path = UPLOAD_DIR / video_filename
        
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Video saved: {video_path}")
        
        tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "file_path": str(video_path),
            "language": language
        }
        
        asyncio.create_task(process_video_analysis(task_id, str(video_path), language))
        
        return {"task_id": task_id, "status": "processing"}
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_video_analysis(task_id: str, video_path: str, language: str):
    """Фоновая обработка анализа видео"""
    try:
        logger.info(f"Processing video analysis for task {task_id}")
        
        tasks[task_id]["progress"] = 10
        
        audio_path = AUDIO_DIR / f"{task_id}.wav"
        
        if not extract_audio_with_ffmpeg(video_path, str(audio_path)):
            raise Exception("Failed to extract audio")
        
        tasks[task_id]["progress"] = 30
        
        transcript = await transcribe_full_video(str(audio_path), language)
        tasks[task_id]["transcript"] = transcript
        tasks[task_id]["progress"] = 70
        
        try:
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path], capture_output=True, text=True, timeout=30)
            video_duration = float(result.stdout.strip())
        except:
            video_duration = 60.0
        
        best_moments = await analyze_best_moments_with_gpt(transcript, video_duration)
        tasks[task_id]["best_moments"] = best_moments
        tasks[task_id]["video_duration"] = video_duration
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        
        logger.info(f"✅ Analysis completed for task {task_id}")
        
        if audio_path.exists():
            audio_path.unlink()
            
    except Exception as e:
        logger.error(f"Analysis failed for task {task_id}: {e}")
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)

@app.get("/api/videos/{task_id}/status")
async def get_video_status(task_id: str):
    """Получение статуса анализа видео"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return tasks[task_id]

# 2. НАРЕЗКА ЧИСТОГО ВИДЕО
@app.post("/api/clips/cut/{task_id}")
async def cut_clips(task_id: str, aspect_ratio: str = Form("9:16")):
    """Нарезка чистых видео клипов (без субтитров)"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video analysis not completed")
    
    logger.info(f"Cutting clean clips for task {task_id}")
    
    clip_task_id = str(uuid.uuid4())
    clip_tasks[clip_task_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "clips": [],
        "logs": []
    }
    
    asyncio.create_task(process_clip_cutting(clip_task_id, task_id, aspect_ratio))
    
    return {"clip_task_id": clip_task_id, "status": "processing"}

async def process_clip_cutting(clip_task_id: str, task_id: str, aspect_ratio: str):
    """Фоновая нарезка чистых клипов"""
    try:
        logger.info(f"Starting clean clip cutting for {clip_task_id}")
        
        task_data = tasks[task_id]
        video_path = task_data["file_path"]
        best_moments = task_data["best_moments"]
        
        clip_tasks[clip_task_id]["logs"].append(f"Found {len(best_moments)} moments to cut")
        
        clips = []
        total_clips = len(best_moments)
        
        for i, moment in enumerate(best_moments):
            logger.info(f"Cutting clean clip {i+1}/{total_clips}: {moment['title']}")
            
            progress = int((i / total_clips) * 100)
            clip_tasks[clip_task_id]["progress"] = progress
            clip_tasks[clip_task_id]["logs"].append(f"Cutting clip {i+1}: {moment['title']}")
            
            clip_id = str(uuid.uuid4())
            clip_filename = f"clean_clip_{clip_id}.mp4"
            clip_path = CLIPS_DIR / clip_filename
            
            success = cut_clean_video(
                video_path=video_path,
                start_time=moment["start_time"],
                end_time=moment["end_time"],
                output_path=str(clip_path),
                aspect_ratio=aspect_ratio
            )
            
            if success and clip_path.exists():
                clips.append({
                    "clip_id": clip_id,
                    "title": moment["title"],
                    "description": moment["description"],
                    "viral_score": moment["viral_score"],
                    "start_time": moment["start_time"],
                    "end_time": moment["end_time"],
                    "duration": moment["end_time"] - moment["start_time"],
                    "transcript_segment": moment["transcript_segment"],
                    "file_path": str(clip_path),
                    "download_url": f"/api/clips/{clip_id}/download",
                    "aspect_ratio": aspect_ratio,
                    "has_subtitles": False
                })
                clip_tasks[clip_task_id]["logs"].append(f"✅ Clean clip {i+1} created")
                logger.info(f"✅ Clean clip {i+1} created: {clip_path}")
            else:
                clip_tasks[clip_task_id]["logs"].append(f"❌ Failed to create clip {i+1}")
                logger.error(f"❌ Failed to create clip {i+1}")
        
        clip_tasks[clip_task_id]["status"] = "completed"
        clip_tasks[clip_task_id]["progress"] = 100
        clip_tasks[clip_task_id]["clips"] = clips
        clip_tasks[clip_task_id]["logs"].append(f"✅ Cutting completed: {len(clips)} clean clips")
        
        logger.info(f"✅ Clean clip cutting completed: {len(clips)} clips")
        
    except Exception as e:
        logger.error(f"Clip cutting failed: {e}")
        clip_tasks[clip_task_id]["status"] = "error"
        clip_tasks[clip_task_id]["error"] = str(e)
        clip_tasks[clip_task_id]["logs"].append(f"❌ Cutting failed: {str(e)}")

@app.get("/api/clips/cut/{clip_task_id}/status")
async def get_clip_cutting_status(clip_task_id: str):
    """Получение статуса нарезки клипов"""
    if clip_task_id not in clip_tasks:
        raise HTTPException(status_code=404, detail="Clip task not found")
    
    return clip_tasks[clip_task_id]

# 3. ГЕНЕРАЦИЯ ДАННЫХ СУБТИТРОВ
@app.post("/api/subtitles/generate/{task_id}")
async def generate_subtitle_data(task_id: str, style: str = Form("beasty")):
    """Генерация данных субтитров для редактирования на фронтенде"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video analysis not completed")
    
    logger.info(f"Generating subtitle data for task {task_id}")
    
    subtitle_task_id = str(uuid.uuid4())
    subtitle_tasks[subtitle_task_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "subtitles": [],
        "style": style
    }
    
    asyncio.create_task(process_subtitle_generation(subtitle_task_id, task_id, style))
    
    return {"subtitle_task_id": subtitle_task_id, "status": "processing"}

async def process_subtitle_generation(subtitle_task_id: str, task_id: str, style: str):
    """Фоновая генерация данных субтитров"""
    try:
        logger.info(f"Generating subtitle data for {subtitle_task_id}")
        
        task_data = tasks[task_id]
        best_moments = task_data["best_moments"]
        
        subtitles = []
        
        for i, moment in enumerate(best_moments):
            # Разбиваем текст на строки
            lines = split_text_into_lines(moment["transcript_segment"])
            
            # Создаем данные субтитров для каждого клипа
            clip_duration = moment["end_time"] - moment["start_time"]
            
            subtitle_data = {
                "clip_index": i,
                "title": moment["title"],
                "start_time": moment["start_time"],
                "end_time": moment["end_time"],
                "duration": clip_duration,
                "original_text": moment["transcript_segment"],
                "lines": lines,
                "style": style,
                "style_config": get_subtitle_styles()[style],
                "timing": {
                    "start": 0,  # Относительно начала клипа
                    "end": clip_duration,
                    "words_per_second": len(moment["transcript_segment"].split()) / clip_duration
                },
                "editable": True
            }
            
            subtitles.append(subtitle_data)
        
        subtitle_tasks[subtitle_task_id]["status"] = "completed"
        subtitle_tasks[subtitle_task_id]["progress"] = 100
        subtitle_tasks[subtitle_task_id]["subtitles"] = subtitles
        
        logger.info(f"✅ Subtitle data generation completed: {len(subtitles)} subtitle sets")
        
    except Exception as e:
        logger.error(f"Subtitle generation failed: {e}")
        subtitle_tasks[subtitle_task_id]["status"] = "error"
        subtitle_tasks[subtitle_task_id]["error"] = str(e)

@app.get("/api/subtitles/{subtitle_task_id}/status")
async def get_subtitle_status(subtitle_task_id: str):
    """Получение статуса генерации субтитров"""
    if subtitle_task_id not in subtitle_tasks:
        raise HTTPException(status_code=404, detail="Subtitle task not found")
    
    return subtitle_tasks[subtitle_task_id]

# 4. СКАЧИВАНИЕ КЛИПОВ
@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивание клипа"""
    # Ищем в чистых клипах
    clip_path = CLIPS_DIR / f"clean_clip_{clip_id}.mp4"
    
    if not clip_path.exists():
        # Ищем в рендеренных клипах
        clip_path = CLIPS_DIR / f"rendered_clip_{clip_id}.mp4"
    
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

# 5. ФИНАЛЬНЫЙ РЕНДЕР С СУБТИТРАМИ (опционально)
@app.post("/api/clips/render")
async def render_clip_with_subtitles(
    clip_id: str = Form(...),
    subtitle_data: str = Form(...)  # JSON строка с данными субтитров
):
    """Финальный рендер клипа с отредактированными субтитрами"""
    try:
        # Парсим данные субтитров
        subtitle_info = json.loads(subtitle_data)
        
        # Находим исходный чистый клип
        clean_clip_path = CLIPS_DIR / f"clean_clip_{clip_id}.mp4"
        
        if not clean_clip_path.exists():
            raise HTTPException(status_code=404, detail="Clean clip not found")
        
        # Создаем файл субтитров
        subtitle_file_id = str(uuid.uuid4())
        subtitle_path = SUBTITLES_DIR / f"custom_{subtitle_file_id}.ass"
        
        # Создаем ASS файл с пользовательскими субтитрами
        create_custom_subtitle_file(subtitle_info, str(subtitle_path))
        
        # Рендерим финальный клип
        rendered_clip_id = str(uuid.uuid4())
        rendered_clip_path = CLIPS_DIR / f"rendered_clip_{rendered_clip_id}.mp4"
        
        cmd = [
            'ffmpeg', '-i', str(clean_clip_path),
            '-vf', f'ass={subtitle_path}',
            '-c:v', 'libx264', '-preset', 'medium',
            '-c:a', 'aac',
            '-y', str(rendered_clip_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        # Удаляем временный файл субтитров
        if subtitle_path.exists():
            subtitle_path.unlink()
        
        if result.returncode == 0 and rendered_clip_path.exists():
            return {
                "rendered_clip_id": rendered_clip_id,
                "download_url": f"/api/clips/{rendered_clip_id}/download",
                "status": "completed"
            }
        else:
            raise HTTPException(status_code=500, detail="Rendering failed")
            
    except Exception as e:
        logger.error(f"Rendering failed: {e}")
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")

def create_custom_subtitle_file(subtitle_info: dict, subtitle_path: str):
    """Создает файл субтитров из пользовательских данных"""
    try:
        style_config = subtitle_info.get("style_config", get_subtitle_styles()["beasty"])
        lines = subtitle_info.get("lines", [])
        duration = subtitle_info.get("duration", 10)
        
        formatted_text = "\\N".join(lines)
        
        ass_content = f"""[Script Info]
Title: Custom Subtitles
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{style_config.get('fontsize', 80)},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4,2,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:{duration:05.2f},Default,,0,0,0,,{formatted_text}
"""
        
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        logger.info(f"✅ Custom subtitle file created: {subtitle_path}")
        
    except Exception as e:
        logger.error(f"Failed to create custom subtitle file: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

