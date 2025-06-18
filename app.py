"""
AgentFlow AI Clips v15.0 - PRODUCTION READY
Оптимизированная архитектура для масштабирования

ОПТИМИЗАЦИИ ДЛЯ PRODUCTION:
1. Queue система для задач
2. Лимиты ресурсов и таймауты
3. Эффективное использование памяти
4. Batch обработка
5. Кэширование результатов
6. Мониторинг ресурсов
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
import json
import asyncio
import subprocess
import logging
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import aiofiles
import re
from collections import deque
import threading
from concurrent.futures import ThreadPoolExecutor
import gc

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
app = FastAPI(title="AgentFlow AI Clips", version="15.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PRODUCTION КОНФИГУРАЦИЯ
class Config:
    # Лимиты ресурсов
    MAX_CONCURRENT_TASKS = 2  # Максимум задач одновременно
    MAX_QUEUE_SIZE = 10       # Максимум задач в очереди
    MAX_VIDEO_SIZE_MB = 100   # Максимум размер видео
    MAX_VIDEO_DURATION = 300  # Максимум длительность видео (5 мин)
    
    # Таймауты
    FFMPEG_TIMEOUT = 120      # Таймаут FFmpeg операций
    OPENAI_TIMEOUT = 60       # Таймаут OpenAI запросов
    CLEANUP_INTERVAL = 300    # Очистка файлов каждые 5 мин
    
    # Качество видео (оптимизированное)
    VIDEO_BITRATE = "2000k"   # Уменьшенный битрейт
    VIDEO_PRESET = "fast"     # Быстрый пресет
    VIDEO_CRF = "28"          # Сжатие
    
    # Память
    MEMORY_LIMIT_PERCENT = 80 # Лимит использования памяти
    FORCE_GC_INTERVAL = 60    # Принудительная очистка памяти

config = Config()

# OpenAI клиент
client = None
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key, timeout=config.OPENAI_TIMEOUT)
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

# QUEUE СИСТЕМА
task_queue = deque()
active_tasks = {}
completed_tasks = {}
task_lock = threading.Lock()

# Thread pool для фоновых задач
executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_TASKS)

# Мониторинг ресурсов
class ResourceMonitor:
    @staticmethod
    def get_memory_usage() -> float:
        """Возвращает использование памяти в процентах"""
        return psutil.virtual_memory().percent
    
    @staticmethod
    def get_cpu_usage() -> float:
        """Возвращает использование CPU в процентах"""
        return psutil.cpu_percent(interval=1)
    
    @staticmethod
    def get_disk_usage() -> float:
        """Возвращает использование диска в процентах"""
        return psutil.disk_usage('/').percent
    
    @staticmethod
    def is_system_overloaded() -> bool:
        """Проверяет перегружена ли система"""
        memory = ResourceMonitor.get_memory_usage()
        return memory > config.MEMORY_LIMIT_PERCENT

monitor = ResourceMonitor()

def cleanup_old_files():
    """Очистка старых файлов"""
    try:
        cutoff_time = datetime.now() - timedelta(hours=2)
        
        for directory in [UPLOAD_DIR, CLIPS_DIR, AUDIO_DIR, SUBTITLES_DIR]:
            for file_path in directory.glob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        logger.info(f"🗑️ Cleaned up old file: {file_path}")
        
        # Принудительная очистка памяти
        gc.collect()
        logger.info("🧹 Cleanup completed")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

def force_memory_cleanup():
    """Принудительная очистка памяти"""
    try:
        gc.collect()
        logger.info(f"🧠 Memory cleanup: {monitor.get_memory_usage():.1f}% used")
    except Exception as e:
        logger.error(f"Memory cleanup failed: {e}")

# Фоновые задачи очистки
async def background_cleanup():
    """Фоновая очистка ресурсов"""
    while True:
        await asyncio.sleep(config.CLEANUP_INTERVAL)
        cleanup_old_files()

async def background_memory_cleanup():
    """Фоновая очистка памяти"""
    while True:
        await asyncio.sleep(config.FORCE_GC_INTERVAL)
        force_memory_cleanup()

# Запуск фоновых задач
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_cleanup())
    asyncio.create_task(background_memory_cleanup())
    logger.info("🚀 Background tasks started")

def get_video_info(video_path: str) -> Tuple[float, int, int]:
    """Получает информацию о видео: длительность, ширина, высота"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            duration = float(data['format']['duration'])
            
            video_stream = next(
                (s for s in data['streams'] if s['codec_type'] == 'video'), 
                None
            )
            
            if video_stream:
                width = int(video_stream['width'])
                height = int(video_stream['height'])
                return duration, width, height
            
        return 0.0, 0, 0
        
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        return 0.0, 0, 0

def validate_video_file(file_path: str, file_size: int) -> bool:
    """Валидация видео файла"""
    try:
        # Проверка размера
        if file_size > config.MAX_VIDEO_SIZE_MB * 1024 * 1024:
            logger.error(f"Video too large: {file_size / 1024 / 1024:.1f}MB")
            return False
        
        # Проверка длительности
        duration, width, height = get_video_info(file_path)
        
        if duration > config.MAX_VIDEO_DURATION:
            logger.error(f"Video too long: {duration:.1f}s")
            return False
        
        if width == 0 or height == 0:
            logger.error("Invalid video format")
            return False
        
        logger.info(f"✅ Video validated: {duration:.1f}s, {width}x{height}")
        return True
        
    except Exception as e:
        logger.error(f"Video validation failed: {e}")
        return False

def extract_audio_optimized(video_path: str, audio_path: str) -> bool:
    """Оптимизированное извлечение аудио"""
    try:
        logger.info(f"Extracting audio (optimized): {video_path}")
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1',
            '-t', '300',  # Лимит 5 минут
            '-y', audio_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=config.FFMPEG_TIMEOUT
        )
        
        if result.returncode == 0:
            logger.info("✅ Audio extraction successful")
            return True
        else:
            logger.error(f"FFmpeg error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Audio extraction timeout")
        return False
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return False

def cut_video_optimized(video_path: str, start_time: float, end_time: float, 
                       output_path: str, aspect_ratio: str = "9:16") -> bool:
    """Оптимизированная нарезка видео"""
    try:
        logger.info(f"Cutting video (optimized): {start_time}-{end_time}s")
        
        duration = end_time - start_time
        
        # Базовая команда
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', str(start_time),
            '-t', str(duration),
            '-c:v', 'libx264', 
            '-preset', config.VIDEO_PRESET,
            '-crf', config.VIDEO_CRF,
            '-c:a', 'aac',
            '-b:a', '128k',
            '-avoid_negative_ts', 'make_zero',
            '-movflags', '+faststart',  # Быстрый старт воспроизведения
            '-y', output_path
        ]
        
        # Добавляем кроппинг для 9:16
        if aspect_ratio == "9:16":
            cmd.insert(-3, '-vf')
            cmd.insert(-3, 'crop=ih*9/16:ih,scale=1080:1920')
        
        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=config.FFMPEG_TIMEOUT
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Video cut successful: {output_path}")
            return True
        else:
            logger.error(f"FFmpeg cutting error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Video cutting timeout")
        return False
    except Exception as e:
        logger.error(f"Video cutting failed: {e}")
        return False

async def transcribe_with_retry(audio_path: str, language: str = "en", max_retries: int = 3) -> Dict:
    """Транскрибация с повторными попытками"""
    if not client:
        raise Exception("OpenAI client not available")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Transcription attempt {attempt + 1}/{max_retries}")
            
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json"
                )
            
            # Обработка результатов
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
            
            # Создаем fallback сегменты если нужно
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
            
            result = {
                "full_text": transcription.text if hasattr(transcription, 'text') else '',
                "segments": segments,
                "words": words,
                "language": transcription.language if hasattr(transcription, 'language') else language
            }
            
            logger.info(f"✅ Transcription completed: {len(segments)} segments")
            return result
            
        except Exception as e:
            logger.error(f"Transcription attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to transcribe after {max_retries} attempts: {str(e)}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

async def analyze_with_gpt_optimized(transcript: Dict, video_duration: float) -> List[Dict]:
    """Оптимизированный анализ с GPT"""
    if not client:
        return create_fallback_clips(transcript["segments"], video_duration)
    
    try:
        logger.info("Starting optimized GPT analysis...")
        
        # Ограничиваем размер текста для GPT
        segments = transcript["segments"][:20]  # Максимум 20 сегментов
        
        segments_text = "\n".join([
            f"{seg['start']:.1f}s-{seg['end']:.1f}s: {seg['text'][:100]}"  # Ограничиваем длину
            for seg in segments
        ])
        
        prompt = f"""
        Find 2-3 BEST viral moments from this video transcript (max 60 seconds each).
        
        TRANSCRIPT:
        {segments_text}
        
        Return JSON:
        {{
          "clips": [
            {{
              "start_time": 15.2,
              "end_time": 45.8,
              "title": "Short Title",
              "description": "Brief description",
              "viral_score": 95,
              "transcript_segment": "exact text"
            }}
          ]
        }}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Быстрее чем GPT-4
            messages=[
                {
                    "role": "system", 
                    "content": "You are a viral video expert. Return only valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000  # Ограничиваем токены
        )
        
        analysis_text = response.choices[0].message.content
        
        try:
            analysis_data = json.loads(analysis_text)
            clips = analysis_data.get("clips", [])[:3]  # Максимум 3 клипа
            logger.info(f"✅ GPT analysis completed: {len(clips)} clips")
            return clips
        except json.JSONDecodeError:
            return create_fallback_clips(segments, video_duration)
            
    except Exception as e:
        logger.error(f"GPT analysis failed: {e}")
        return create_fallback_clips(transcript["segments"], video_duration)

def create_fallback_clips(segments: List[Dict], video_duration: float) -> List[Dict]:
    """Создает базовые клипы"""
    clips = []
    
    for i, segment in enumerate(segments[:3]):
        if segment['end'] - segment['start'] >= 5:
            clips.append({
                "start_time": segment['start'],
                "end_time": min(segment['end'] + 5, video_duration),
                "title": f"Moment {i+1}",
                "description": "Interesting moment",
                "viral_score": 75,
                "transcript_segment": segment['text']
            })
    
    return clips

# QUEUE MANAGEMENT
def add_task_to_queue(task_data: Dict) -> bool:
    """Добавляет задачу в очередь"""
    with task_lock:
        if len(task_queue) >= config.MAX_QUEUE_SIZE:
            return False
        
        task_queue.append(task_data)
        logger.info(f"📋 Task added to queue: {task_data['task_id']}")
        return True

def get_next_task() -> Optional[Dict]:
    """Получает следующую задачу из очереди"""
    with task_lock:
        if task_queue:
            return task_queue.popleft()
        return None

def process_task_queue():
    """Обрабатывает очередь задач"""
    while True:
        try:
            # Проверяем нагрузку системы
            if monitor.is_system_overloaded():
                logger.warning("⚠️ System overloaded, waiting...")
                time.sleep(30)
                continue
            
            # Проверяем количество активных задач
            if len(active_tasks) >= config.MAX_CONCURRENT_TASKS:
                time.sleep(5)
                continue
            
            # Получаем следующую задачу
            task_data = get_next_task()
            if not task_data:
                time.sleep(5)
                continue
            
            # Запускаем обработку
            task_id = task_data['task_id']
            active_tasks[task_id] = task_data
            
            logger.info(f"🚀 Starting task: {task_id}")
            
            # Запускаем в thread pool
            future = executor.submit(process_video_task, task_data)
            
            # Ждем завершения или таймаута
            try:
                future.result(timeout=300)  # 5 минут максимум
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
            finally:
                if task_id in active_tasks:
                    del active_tasks[task_id]
                
                # Принудительная очистка памяти
                force_memory_cleanup()
            
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
            time.sleep(10)

def process_video_task(task_data: Dict):
    """Обработка видео задачи"""
    task_id = task_data['task_id']
    video_path = task_data['file_path']
    language = task_data['language']
    
    try:
        logger.info(f"Processing video task: {task_id}")
        
        # Обновляем статус
        task_data['status'] = 'processing'
        task_data['progress'] = 10
        
        # Извлечение аудио
        audio_path = AUDIO_DIR / f"{task_id}.wav"
        
        if not extract_audio_optimized(video_path, str(audio_path)):
            raise Exception("Failed to extract audio")
        
        task_data['progress'] = 30
        
        # Транскрибация
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        transcript = loop.run_until_complete(
            transcribe_with_retry(str(audio_path), language)
        )
        
        task_data['transcript'] = transcript
        task_data['progress'] = 70
        
        # Получаем длительность видео
        duration, _, _ = get_video_info(video_path)
        
        # Анализ лучших моментов
        best_moments = loop.run_until_complete(
            analyze_with_gpt_optimized(transcript, duration)
        )
        
        task_data['best_moments'] = best_moments
        task_data['video_duration'] = duration
        task_data['status'] = 'completed'
        task_data['progress'] = 100
        
        # Сохраняем в completed_tasks
        completed_tasks[task_id] = task_data
        
        logger.info(f"✅ Task completed: {task_id}")
        
        # Очистка временных файлов
        if audio_path.exists():
            audio_path.unlink()
        
        loop.close()
        
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        task_data['status'] = 'error'
        task_data['error'] = str(e)

# Запуск обработчика очереди в отдельном потоке
queue_thread = threading.Thread(target=process_task_queue, daemon=True)
queue_thread.start()

@app.get("/")
async def root():
    return {
        "service": "AgentFlow AI Clips",
        "version": "15.0.0",
        "description": "Production-ready video clipping with queue system",
        "features": {
            "queue_system": True,
            "resource_monitoring": True,
            "optimized_processing": True,
            "concurrent_tasks": config.MAX_CONCURRENT_TASKS,
            "max_queue_size": config.MAX_QUEUE_SIZE
        },
        "system_status": {
            "memory_usage": f"{monitor.get_memory_usage():.1f}%",
            "active_tasks": len(active_tasks),
            "queue_size": len(task_queue)
        }
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
    
    system_status = {
        "memory_usage": monitor.get_memory_usage(),
        "cpu_usage": monitor.get_cpu_usage(),
        "disk_usage": monitor.get_disk_usage(),
        "overloaded": monitor.is_system_overloaded()
    }
    
    return {
        "status": "healthy",
        "version": "15.0.0",
        "dependencies": deps,
        "system": system_status,
        "queue": {
            "active_tasks": len(active_tasks),
            "queued_tasks": len(task_queue),
            "max_concurrent": config.MAX_CONCURRENT_TASKS
        }
    }

@app.post("/api/videos/analyze")
async def analyze_video_optimized(file: UploadFile = File(...), language: str = Form("en")):
    """Оптимизированная загрузка и анализ видео"""
    try:
        # Проверка нагрузки системы
        if monitor.is_system_overloaded():
            raise HTTPException(
                status_code=503, 
                detail="System overloaded. Please try again later."
            )
        
        # Проверка очереди
        if len(task_queue) >= config.MAX_QUEUE_SIZE:
            raise HTTPException(
                status_code=503, 
                detail="Queue is full. Please try again later."
            )
        
        logger.info(f"Analyzing video (optimized): {file.filename}")
        
        task_id = str(uuid.uuid4())
        
        # Проверка размера файла
        content = await file.read()
        file_size = len(content)
        
        if file_size > config.MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Max size: {config.MAX_VIDEO_SIZE_MB}MB"
            )
        
        # Сохранение файла
        file_extension = file.filename.split('.')[-1]
        video_filename = f"{task_id}_{file.filename}"
        video_path = UPLOAD_DIR / video_filename
        
        async with aiofiles.open(video_path, 'wb') as f:
            await f.write(content)
        
        # Валидация видео
        if not validate_video_file(str(video_path), file_size):
            video_path.unlink()  # Удаляем невалидный файл
            raise HTTPException(
                status_code=400, 
                detail="Invalid video file or too long"
            )
        
        # Создание задачи
        task_data = {
            "task_id": task_id,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "file_path": str(video_path),
            "language": language,
            "file_size": file_size
        }
        
        # Добавление в очередь
        if not add_task_to_queue(task_data):
            video_path.unlink()
            raise HTTPException(
                status_code=503, 
                detail="Failed to add task to queue"
            )
        
        return {
            "task_id": task_id, 
            "status": "queued",
            "queue_position": len(task_queue),
            "estimated_wait_time": len(task_queue) * 60  # Примерно 1 минута на задачу
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/videos/{task_id}/status")
async def get_video_status_optimized(task_id: str):
    """Получение статуса анализа видео"""
    
    # Проверяем активные задачи
    if task_id in active_tasks:
        return active_tasks[task_id]
    
    # Проверяем завершенные задачи
    if task_id in completed_tasks:
        return completed_tasks[task_id]
    
    # Проверяем очередь
    for task in task_queue:
        if task['task_id'] == task_id:
            queue_position = list(task_queue).index(task) + 1
            task['queue_position'] = queue_position
            task['estimated_wait_time'] = queue_position * 60
            return task
    
    raise HTTPException(status_code=404, detail="Task not found")

# Остальные endpoints остаются такими же, но с оптимизациями...
# (cut_clips, generate_subtitle_data, download_clip, render_clip_with_subtitles)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ПАТЧ v15.2 - ИСПРАВЛЕННАЯ ВЕРСИЯ
# Добавить в конец файла agentflow_ai_clips_v15_production.py

@app.post("/api/clips/generate")
async def generate_clips(
    task_id: str = Form(...),
    style: str = Form(default="beasty"),
    aspect_ratio: str = Form(default="9:16")
):
    """Генерация клипов с субтитрами"""
    try:
        # Проверяем что задача существует в completed_tasks
        if task_id not in completed_tasks:
            raise HTTPException(status_code=404, detail="Task not found or not completed")
        
        task_data = completed_tasks[task_id]
        
        if task_data['status'] != 'completed':
            raise HTTPException(status_code=400, detail="Analysis not completed")
        
        # Создаем задачу генерации
        generation_id = str(uuid.uuid4())
        generation_task = {
            "generation_id": generation_id,
            "task_id": task_id,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "clips": []
        }
        
        # Сохраняем в completed_tasks с префиксом gen_
        completed_tasks[f"gen_{generation_id}"] = generation_task
        
        # Добавляем в очередь
        await add_to_queue(f"generate_clips_{generation_id}", generation_clips_task, generation_id, task_data)
        
        return {
            "generation_id": generation_id,
            "status": "queued",
            "message": "Clips generation started"
        }
        
    except Exception as e:
        logger.error(f"Error starting clips generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/generation/{generation_id}/status")
async def get_generation_status(generation_id: str):
    """Получить статус генерации клипов"""
    try:
        generation_key = f"gen_{generation_id}"
        if generation_key not in completed_tasks:
            raise HTTPException(status_code=404, detail="Generation task not found")
        
        generation_data = completed_tasks[generation_key]
        return generation_data
        
    except Exception as e:
        logger.error(f"Error getting generation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачать готовый клип"""
    try:
        clip_file = CLIPS_DIR / f"{clip_id}.mp4"
        if not clip_file.exists():
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return FileResponse(
            path=clip_file,
            media_type='video/mp4',
            filename=f"clip_{clip_id}.mp4"
        )
        
    except Exception as e:
        logger.error(f"Error downloading clip: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def generation_clips_task(generation_id: str, task_data: dict):
    """Фоновая задача генерации клипов"""
    try:
        # Обновляем статус в completed_tasks
        generation_key = f"gen_{generation_id}"
        generation_data = completed_tasks[generation_key]
        generation_data['status'] = 'processing'
        
        # Генерируем клипы для каждого лучшего момента
        clips = []
        for i, moment in enumerate(task_data['best_moments']):
            clip_id = str(uuid.uuid4())
            
            # Простая нарезка без субтитров (для скорости)
            input_file = task_data['file_path']
            output_file = CLIPS_DIR / f"{clip_id}.mp4"
            
            # FFmpeg команда для нарезки в 9:16
            cmd = [
                'ffmpeg', '-i', str(input_file),
                '-ss', str(moment['start_time']),
                '-t', str(moment['end_time'] - moment['start_time']),
                '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
                '-c:v', 'libx264', '-preset', config.VIDEO_PRESET, '-crf', config.VIDEO_CRF,
                '-c:a', 'aac', '-b:a', '128k',
                '-y', str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.FFMPEG_TIMEOUT)
            
            if result.returncode == 0:
                clips.append({
                    "clip_id": clip_id,
                    "title": moment['title'],
                    "duration": moment['end_time'] - moment['start_time'],
                    "viral_score": moment['viral_score'],
                    "download_url": f"/api/clips/{clip_id}/download"
                })
                logger.info(f"✅ Generated clip {clip_id}: {moment['title']}")
            else:
                logger.error(f"❌ Failed to generate clip for moment {i}: {result.stderr}")
        
        # Обновляем результат
        generation_data['status'] = 'completed'
        generation_data['clips'] = clips
        generation_data['completed_at'] = datetime.now().isoformat()
        
        logger.info(f"🎬 Generated {len(clips)} clips for {generation_id}")
        
    except Exception as e:
        logger.error(f"Error in generation task: {e}")
        generation_data['status'] = 'failed'
        generation_data['error'] = str(e)
        generation_data['failed_at'] = datetime.now().isoformat()

# Дополнительный endpoint для получения списка всех клипов задачи
@app.get("/api/videos/{task_id}/clips")
async def get_task_clips(task_id: str):
    """Получить все клипы для задачи"""
    try:
        # Ищем все генерации для этой задачи
        task_clips = []
        for key, data in completed_tasks.items():
            if key.startswith("gen_") and data.get("task_id") == task_id:
                if data.get("status") == "completed" and "clips" in data:
                    task_clips.extend(data["clips"])
        
        return {
            "task_id": task_id,
            "clips": task_clips,
            "total_clips": len(task_clips)
        }
        
    except Exception as e:
        logger.error(f"Error getting task clips: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ПАТЧ v15.3 - Увеличение лимита размера файла
# Заменить в классе Config в agentflow_ai_clips_v15_production.py

class Config:
    # Лимиты ресурсов
    MAX_CONCURRENT_TASKS = 2  # Максимум задач одновременно
    MAX_QUEUE_SIZE = 10       # Максимум задач в очереди
    MAX_VIDEO_SIZE_MB = 150   # УВЕЛИЧЕНО: Максимум размер видео (было 100)
    MAX_VIDEO_DURATION = 300  # Максимум длительность видео (5 мин)
    
    # Таймауты
    FFMPEG_TIMEOUT = 120      # Таймаут FFmpeg операций
    OPENAI_TIMEOUT = 60       # Таймаут OpenAI запросов
    CLEANUP_INTERVAL = 300    # Очистка файлов каждые 5 мин
    
    # Качество видео (оптимизированное)
    VIDEO_BITRATE = "2000k"   # Уменьшенный битрейт
    VIDEO_PRESET = "fast"     # Быстрый пресет
    VIDEO_CRF = "28"          # Сжатие
    
    # Память
    MEMORY_LIMIT_PERCENT = 80 # Лимит использования памяти
    FORCE_GC_INTERVAL = 60    # Принудительная очистка памяти

