"""
AgentFlow AI Clips v11.0 - ИСПРАВЛЕННАЯ ВЕРСИЯ
Полноценная автоматическая нарезка видео с улучшенной обработкой ошибок

ИСПРАВЛЕНИЯ v11.0:
- Улучшенное логирование всех операций
- Альтернативный подход через FFmpeg для нарезки
- Проверка зависимостей при старте
- Детальная обработка ошибок
- Fallback методы для каждого этапа
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
from openai import OpenAI

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
app = FastAPI(title="AgentFlow AI Clips", version="11.0.0")

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

def check_dependencies():
    """Проверка установленных зависимостей"""
    dependencies = {
        "ffmpeg": False,
        "moviepy": False,
        "openai": False
    }
    
    # Проверка FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        dependencies["ffmpeg"] = result.returncode == 0
        logger.info(f"FFmpeg: {'✅ Available' if dependencies['ffmpeg'] else '❌ Not found'}")
    except:
        logger.warning("FFmpeg not found")
    
    # Проверка MoviePy
    try:
        import moviepy
        dependencies["moviepy"] = True
        logger.info("MoviePy: ✅ Available")
    except ImportError:
        logger.warning("MoviePy not found")
    
    # Проверка OpenAI
    try:
        dependencies["openai"] = bool(os.getenv("OPENAI_API_KEY"))
        logger.info(f"OpenAI API Key: {'✅ Available' if dependencies['openai'] else '❌ Missing'}")
    except:
        logger.warning("OpenAI client error")
    
    return dependencies

@app.on_event("startup")
async def startup_event():
    """Проверка зависимостей при запуске"""
    logger.info("🚀 Starting AgentFlow AI Clips v11.0")
    deps = check_dependencies()
    logger.info(f"Dependencies check: {deps}")

@app.get("/")
async def root():
    deps = check_dependencies()
    return {
        "service": "AgentFlow AI Clips",
        "version": "11.0.0",
        "description": "Automatic video clipping with improved error handling",
        "dependencies": deps,
        "features": [
            "1. Upload video",
            "2. Whisper AI transcription", 
            "3. ChatGPT analysis of best moments",
            "4. Automatic video cutting with FFmpeg fallback",
            "5. Professional subtitle overlay",
            "6. Download ready clips"
        ]
    }

@app.get("/health")
async def health_check():
    deps = check_dependencies()
    return {
        "status": "healthy",
        "version": "11.0.0",
        "dependencies": deps,
        "features": {
            "whisper_transcription": deps["openai"],
            "gpt4_analysis": deps["openai"],
            "automatic_cutting": deps["ffmpeg"] or deps["moviepy"],
            "subtitle_overlay": True,
            "error_logging": True
        }
    }

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
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Audio extraction successful")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return False

def extract_audio_with_moviepy(video_path: str, audio_path: str) -> bool:
    """Fallback: извлекает аудио через MoviePy"""
    try:
        logger.info("Trying MoviePy for audio extraction...")
        from moviepy.editor import VideoFileClip
        
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        audio.close()
        
        logger.info("✅ MoviePy audio extraction successful")
        return True
        
    except Exception as e:
        logger.error(f"MoviePy audio extraction failed: {e}")
        return False

async def transcribe_full_video(audio_path: str, language: str = "en") -> Dict:
    """Полная транскрибация видео с временными метками"""
    try:
        logger.info(f"Starting transcription: {audio_path}")
        
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        
        # Обработка результата
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
                        "start": segment['start'],
                        "end": segment['end'],
                        "text": segment['text'].strip()
                    })
        
        if hasattr(transcription, 'words') and transcription.words:
            for word in transcription.words:
                if hasattr(word, 'start'):
                    words.append({
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end
                    })
                elif isinstance(word, dict):
                    words.append({
                        "word": word['word'].strip(),
                        "start": word['start'],
                        "end": word['end']
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
        if segment['end'] - segment['start'] >= 15:
            clips.append({
                "start_time": segment['start'],
                "end_time": min(segment['end'] + 10, video_duration),
                "title": f"Highlight {i+1}",
                "description": "Interesting moment from the video",
                "viral_score": 75,
                "caption_style": "beasty",
                "transcript_segment": segment['text']
            })
    
    logger.info(f"✅ Created {len(clips)} fallback clips")
    return clips

def cut_video_with_ffmpeg(video_path: str, start_time: float, end_time: float, 
                         transcript_segment: str, caption_style: str, 
                         output_path: str, aspect_ratio: str = "9:16") -> bool:
    """Нарезает видео и добавляет субтитры через FFmpeg"""
    try:
        logger.info(f"Cutting video with FFmpeg: {start_time}-{end_time}s")
        
        # Создаем временный файл субтитров
        srt_path = output_path.replace('.mp4', '.srt')
        
        # Создаем SRT файл
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write("1\n")
            f.write(f"00:00:00,000 --> {int((end_time-start_time)*1000//60000):02d}:{int((end_time-start_time)*1000//1000%60):02d},{int((end_time-start_time)*1000%1000):03d}\n")
            f.write(f"{transcript_segment}\n")
        
        # Стили субтитров для FFmpeg
        styles = {
            "beasty": "FontSize=24,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2",
            "karaoke": "FontSize=26,PrimaryColour=&H00ffff,OutlineColour=&H0000ff,Outline=2",
            "deep_diver": "FontSize=22,PrimaryColour=&Hffff80,OutlineColour=&H800080,Outline=2",
            "youshael": "FontSize=28,PrimaryColour=&H00d7ff,OutlineColour=&H000000,Outline=3"
        }
        
        style = styles.get(caption_style, styles["beasty"])
        
        # FFmpeg команда для нарезки и добавления субтитров
        if aspect_ratio == "9:16":
            # Кроп в 9:16 и добавление субтитров
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-vf', f'crop=ih*9/16:ih,scale=1080:1920,subtitles={srt_path}:force_style=\'{style}\'',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:v', '8000k',
                '-r', '30',
                '-y', output_path
            ]
        else:
            # Обычная нарезка с субтитрами
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time),
                '-t', str(end_time - start_time),
                '-vf', f'subtitles={srt_path}:force_style=\'{style}\'',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-y', output_path
            ]
        
        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Удаляем временный SRT файл
        if os.path.exists(srt_path):
            os.remove(srt_path)
        
        if result.returncode == 0:
            logger.info(f"✅ Video cut successful: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg cutting error: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Video cutting failed: {e}")
        return False

def cut_video_with_moviepy(video_path: str, start_time: float, end_time: float, 
                          transcript_segment: str, caption_style: str, 
                          output_path: str, aspect_ratio: str = "9:16") -> bool:
    """Fallback: нарезает видео через MoviePy"""
    try:
        logger.info("Trying MoviePy for video cutting...")
        from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
        
        # Загружаем и обрезаем видео
        video = VideoFileClip(video_path).subclip(start_time, end_time)
        
        # Кроп в 9:16 если нужно
        if aspect_ratio == "9:16":
            target_aspect = 9 / 16
            current_aspect = video.w / video.h
            
            if current_aspect > target_aspect:
                new_width = int(video.h * target_aspect)
                x_center = video.w / 2
                x1 = int(x_center - new_width / 2)
                x2 = int(x_center + new_width / 2)
                video = video.crop(x1=x1, x2=x2)
            
            video = video.resize((1080, 1920))
        
        # Стили субтитров
        caption_styles = {
            "beasty": {"fontsize": 80, "color": "white", "stroke_color": "black", "stroke_width": 4},
            "karaoke": {"fontsize": 85, "color": "yellow", "stroke_color": "red", "stroke_width": 3},
            "deep_diver": {"fontsize": 75, "color": "lightblue", "stroke_color": "darkblue", "stroke_width": 3},
            "youshael": {"fontsize": 90, "color": "gold", "stroke_color": "black", "stroke_width": 5}
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
            size=(video.w * 0.9, None),
            align="center"
        ).set_position(("center", 0.8), relative=True).set_duration(video.duration)
        
        # Композитное видео
        final_video = CompositeVideoClip([video, subtitle])
        
        # Сохраняем
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            fps=30,
            verbose=False,
            logger=None
        )
        
        # Очищаем память
        video.close()
        subtitle.close()
        final_video.close()
        
        logger.info(f"✅ MoviePy cutting successful: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"MoviePy cutting failed: {e}")
        return False

@app.post("/api/videos/analyze")
async def analyze_video(file: UploadFile = File(...), language: str = Form("en")):
    """Загрузка и анализ видео"""
    try:
        logger.info(f"Analyzing video: {file.filename}")
        
        # Создаем уникальный ID задачи
        task_id = str(uuid.uuid4())
        
        # Сохраняем файл
        file_extension = file.filename.split('.')[-1]
        video_filename = f"{task_id}_{file.filename}"
        video_path = UPLOAD_DIR / video_filename
        
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"Video saved: {video_path}")
        
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
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_video_analysis(task_id: str, video_path: str, language: str):
    """Фоновая обработка анализа видео"""
    try:
        logger.info(f"Processing video analysis for task {task_id}")
        
        # Обновляем прогресс
        tasks[task_id]["progress"] = 10
        
        # Извлекаем аудио (пробуем FFmpeg, потом MoviePy)
        audio_path = AUDIO_DIR / f"{task_id}.wav"
        
        if not extract_audio_with_ffmpeg(video_path, str(audio_path)):
            logger.info("FFmpeg failed, trying MoviePy...")
            if not extract_audio_with_moviepy(video_path, str(audio_path)):
                raise Exception("Failed to extract audio with both methods")
        
        tasks[task_id]["progress"] = 30
        
        # Транскрибируем
        transcript = await transcribe_full_video(str(audio_path), language)
        tasks[task_id]["transcript"] = transcript
        tasks[task_id]["progress"] = 70
        
        # Получаем длительность видео
        try:
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path], capture_output=True, text=True)
            video_duration = float(result.stdout.strip())
        except:
            # Fallback через MoviePy
            from moviepy.editor import VideoFileClip
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
        
        logger.info(f"✅ Analysis completed for task {task_id}")
        
        # Удаляем временный аудио файл
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

@app.post("/api/clips/generate/{task_id}")
async def generate_clips(task_id: str, caption_style: str = Form("beasty")):
    """Генерация клипов с субтитрами"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video analysis not completed")
    
    logger.info(f"Generating clips for task {task_id}")
    
    # Создаем задачу генерации
    generation_task_id = str(uuid.uuid4())
    generation_tasks[generation_task_id] = {
        "status": "processing",
        "progress": 0,
        "created_at": datetime.now().isoformat(),
        "clips": [],
        "logs": []
    }
    
    # Запускаем генерацию в фоне
    asyncio.create_task(process_clips_generation(
        generation_task_id, task_id, caption_style
    ))
    
    return {"generation_task_id": generation_task_id, "status": "processing"}

async def process_clips_generation(generation_task_id: str, task_id: str, caption_style: str):
    """Фоновая генерация клипов с улучшенным логированием"""
    try:
        logger.info(f"Starting clips generation for {generation_task_id}")
        
        task_data = tasks[task_id]
        video_path = task_data["file_path"]
        best_moments = task_data["best_moments"]
        
        generation_tasks[generation_task_id]["logs"].append(f"Found {len(best_moments)} moments to process")
        
        clips = []
        total_clips = len(best_moments)
        
        for i, moment in enumerate(best_moments):
            logger.info(f"Processing clip {i+1}/{total_clips}: {moment['title']}")
            
            # Обновляем прогресс
            progress = int((i / total_clips) * 100)
            generation_tasks[generation_task_id]["progress"] = progress
            generation_tasks[generation_task_id]["logs"].append(f"Processing clip {i+1}: {moment['title']}")
            
            # Создаем клип
            clip_id = str(uuid.uuid4())
            clip_filename = f"clip_{clip_id}.mp4"
            clip_path = CLIPS_DIR / clip_filename
            
            # Пробуем FFmpeg, потом MoviePy
            success = cut_video_with_ffmpeg(
                video_path=video_path,
                start_time=moment["start_time"],
                end_time=moment["end_time"],
                transcript_segment=moment["transcript_segment"],
                caption_style=caption_style,
                output_path=str(clip_path),
                aspect_ratio="9:16"
            )
            
            if not success:
                logger.info("FFmpeg failed, trying MoviePy...")
                generation_tasks[generation_task_id]["logs"].append(f"FFmpeg failed for clip {i+1}, trying MoviePy...")
                success = cut_video_with_moviepy(
                    video_path=video_path,
                    start_time=moment["start_time"],
                    end_time=moment["end_time"],
                    transcript_segment=moment["transcript_segment"],
                    caption_style=caption_style,
                    output_path=str(clip_path),
                    aspect_ratio="9:16"
                )
            
            if success and clip_path.exists():
                clips.append({
                    "clip_id": clip_id,
                    "title": moment["title"],
                    "description": moment["description"],
                    "viral_score": moment["viral_score"],
                    "duration": moment["end_time"] - moment["start_time"],
                    "file_path": str(clip_path),
                    "download_url": f"/api/clips/{clip_id}/download"
                })
                generation_tasks[generation_task_id]["logs"].append(f"✅ Clip {i+1} created successfully")
                logger.info(f"✅ Clip {i+1} created: {clip_path}")
            else:
                generation_tasks[generation_task_id]["logs"].append(f"❌ Failed to create clip {i+1}")
                logger.error(f"❌ Failed to create clip {i+1}")
        
        # Завершаем генерацию
        generation_tasks[generation_task_id]["status"] = "completed"
        generation_tasks[generation_task_id]["progress"] = 100
        generation_tasks[generation_task_id]["clips"] = clips
        generation_tasks[generation_task_id]["logs"].append(f"✅ Generation completed: {len(clips)} clips created")
        
        logger.info(f"✅ Generation completed: {len(clips)} clips created")
        
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        generation_tasks[generation_task_id]["status"] = "error"
        generation_tasks[generation_task_id]["error"] = str(e)
        generation_tasks[generation_task_id]["logs"].append(f"❌ Generation failed: {str(e)}")

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

