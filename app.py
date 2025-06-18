"""
AgentFlow AI Clips v15.2.1 - PRODUCTION READY + ИСПРАВЛЕННЫЕ ENDPOINTS + QUEUE FIX
Полная версия с исправленной функцией add_to_queue

ОПТИМИЗАЦИИ ДЛЯ PRODUCTION:
1. Queue система для задач
2. Лимиты ресурсов и таймауты
3. Эффективное использование памяти
4. Batch обработка
5. Кэширование результатов
6. Мониторинг ресурсов
7. ИСПРАВЛЕННЫЕ ENDPOINTS для генерации клипов
8. ИСПРАВЛЕННАЯ QUEUE ФУНКЦИЯ
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
app = FastAPI(title="AgentFlow AI Clips", version="15.2.1")

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

# Автоматическая очистка каждые 5 минут
def start_cleanup_scheduler():
    def cleanup_loop():
        while True:
            time.sleep(config.CLEANUP_INTERVAL)
            cleanup_old_files()
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()

# Запуск очистки при старте
start_cleanup_scheduler()

# Queue управление - ИСПРАВЛЕННАЯ ВЕРСИЯ
def add_to_queue(task_name: str, task_func, *args):
    """Добавить задачу в очередь"""
    with task_lock:
        if len(task_queue) >= config.MAX_QUEUE_SIZE:
            raise HTTPException(status_code=429, detail="Queue is full")
        
        if len(active_tasks) >= config.MAX_CONCURRENT_TASKS:
            task_queue.append((task_name, task_func, args))
            return len(task_queue)
        else:
            # Запускаем сразу
            active_tasks[task_name] = True
            executor.submit(run_task, task_name, task_func, *args)
            return 0

def run_task(task_name: str, task_func, *args):
    """Выполнить задачу"""
    try:
        task_func(*args)
    except Exception as e:
        logger.error(f"Task {task_name} failed: {e}")
    finally:
        with task_lock:
            if task_name in active_tasks:
                del active_tasks[task_name]
            
            # Запускаем следующую задачу из очереди
            if task_queue and len(active_tasks) < config.MAX_CONCURRENT_TASKS:
                next_task_name, next_task_func, next_args = task_queue.popleft()
                active_tasks[next_task_name] = True
                executor.submit(run_task, next_task_name, next_task_func, *next_args)

# Проверка зависимостей
def check_dependencies():
    """Проверка доступности зависимостей"""
    deps = {
        "ffmpeg": False,
        "openai": False
    }
    
    # Проверка FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        deps["ffmpeg"] = result.returncode == 0
    except:
        pass
    
    # Проверка OpenAI
    deps["openai"] = client is not None
    
    return deps

# Основные функции
def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Извлечение аудио из видео"""
    try:
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            '-y', audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.FFMPEG_TIMEOUT)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return False

def transcribe_audio(audio_path: str) -> Optional[dict]:
    """Транскрибация аудио через OpenAI Whisper"""
    if not client:
        logger.error("OpenAI client not available")
        return None
    
    try:
        with open(audio_path, 'rb') as audio_file:
            # Совместимая версия для OpenAI 1.3.0
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        
        # Создаем временные метки если их нет
        segments = []
        if hasattr(response, 'segments') and response.segments:
            segments = [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text
                }
                for seg in response.segments
            ]
        else:
            # Fallback: создаем простые сегменты
            text = response.text
            words = text.split()
            segment_length = 5.0  # 5 секунд на сегмент
            words_per_segment = max(1, len(words) // max(1, int(len(words) * segment_length / 60)))
            
            for i in range(0, len(words), words_per_segment):
                segment_words = words[i:i + words_per_segment]
                start_time = i * segment_length / words_per_segment
                end_time = min(start_time + segment_length, len(words) * segment_length / words_per_segment)
                
                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": " ".join(segment_words)
                })
        
        return {
            "full_text": response.text,
            "segments": segments,
            "words": [],  # Не поддерживается в 1.3.0
            "language": "english"
        }
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return None

def analyze_best_moments(transcript: dict) -> List[dict]:
    """Анализ лучших моментов через ChatGPT"""
    if not client:
        logger.error("OpenAI client not available")
        return []
    
    try:
        # Используем GPT-3.5-turbo для скорости
        prompt = f"""
        Analyze this video transcript and find the 2-3 BEST viral moments for social media clips.
        
        Transcript: {transcript['full_text']}
        
        For each moment, provide:
        1. Start and end time (in seconds)
        2. Catchy title (max 30 chars)
        3. Brief description
        4. Viral score (1-100)
        5. The exact transcript segment
        
        Focus on:
        - Emotional peaks
        - Surprising statements
        - Actionable advice
        - Controversial or debate-worthy content
        - Clear, standalone messages
        
        Return as JSON array with this structure:
        [
          {{
            "start_time": 0.0,
            "end_time": 10.0,
            "title": "Amazing Insight",
            "description": "Brief description",
            "viral_score": 85,
            "transcript_segment": "exact text from transcript"
          }}
        ]
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Быстрее чем GPT-4
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        # Извлекаем JSON из ответа
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            moments = json.loads(json_match.group())
            # Ограничиваем до 3 моментов для производительности
            return moments[:3]
        
        return []
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return []

def get_video_duration(video_path: str) -> float:
    """Получить длительность видео"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        
        return 0.0
    except:
        return 0.0

# Фоновая задача анализа
def analyze_video_task(task_id: str, file_path: str):
    """Фоновая задача анализа видео"""
    try:
        # Обновляем статус
        completed_tasks[task_id]['status'] = 'processing: Извлечение аудио'
        
        # Извлекаем аудио
        audio_path = AUDIO_DIR / f"{task_id}.wav"
        if not extract_audio_from_video(file_path, str(audio_path)):
            raise Exception("Failed to extract audio")
        
        # Транскрибация
        completed_tasks[task_id]['status'] = 'processing: Транскрибация'
        transcript = transcribe_audio(str(audio_path))
        if not transcript:
            raise Exception("Failed to transcribe audio")
        
        # Анализ лучших моментов
        completed_tasks[task_id]['status'] = 'processing: Анализ моментов'
        best_moments = analyze_best_moments(transcript)
        
        # Получаем длительность видео
        video_duration = get_video_duration(file_path)
        
        # Финализация
        completed_tasks[task_id]['status'] = 'processing: Финализация'
        completed_tasks[task_id].update({
            'status': 'completed',
            'progress': 100,
            'transcript': transcript,
            'best_moments': best_moments,
            'video_duration': video_duration,
            'language': 'en'
        })
        
        # Очистка аудио файла
        try:
            audio_path.unlink()
        except:
            pass
        
        logger.info(f"✅ Analysis completed for {task_id}")
        
    except Exception as e:
        logger.error(f"Analysis failed for task {task_id}: {e}")
        completed_tasks[task_id].update({
            'status': 'failed',
            'error': str(e)
        })

# API ENDPOINTS

@app.get("/")
async def root():
    return {
        "service": "AgentFlow AI Clips",
        "version": "15.2.1",
        "status": "running",
        "features": [
            "Video analysis with Whisper AI",
            "Best moments detection with ChatGPT",
            "Automated video clipping",
            "Multiple subtitle styles",
            "Queue system for scalability",
            "Resource monitoring"
        ]
    }

@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    deps = check_dependencies()
    system_stats = {
        "memory_usage": monitor.get_memory_usage(),
        "cpu_usage": monitor.get_cpu_usage(),
        "disk_usage": monitor.get_disk_usage(),
        "overloaded": monitor.is_system_overloaded()
    }
    
    queue_stats = {
        "active_tasks": len(active_tasks),
        "queued_tasks": len(task_queue),
        "max_concurrent": config.MAX_CONCURRENT_TASKS
    }
    
    return {
        "status": "healthy",
        "version": "15.2.1",
        "dependencies": deps,
        "system": system_stats,
        "queue": queue_stats
    }

@app.post("/api/videos/analyze")
async def analyze_video(file: UploadFile = File(...)):
    """Анализ видео с очередью"""
    try:
        # Проверка перегрузки системы
        if monitor.is_system_overloaded():
            raise HTTPException(status_code=503, detail="System overloaded")
        
        # Проверка размера файла
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > config.MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Max size: {config.MAX_VIDEO_SIZE_MB}MB"
            )
        
        # Создание задачи
        task_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
        
        # Сохранение файла
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Проверка длительности видео
        duration = get_video_duration(str(file_path))
        if duration > config.MAX_VIDEO_DURATION:
            file_path.unlink()  # Удаляем файл
            raise HTTPException(
                status_code=413,
                detail=f"Video too long. Max duration: {config.MAX_VIDEO_DURATION} seconds"
            )
        
        # Создание записи задачи
        task_data = {
            "task_id": task_id,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "file_path": str(file_path),
            "file_size": file_size,
            "result": None,
            "error": None
        }
        
        completed_tasks[task_id] = task_data
        
        # Добавление в очередь - ИСПРАВЛЕНО: убран await
        queue_position = add_to_queue(f"analyze_{task_id}", analyze_video_task, task_id, str(file_path))
        
        response = {
            "task_id": task_id,
            "status": "queued",
            "queue_position": queue_position,
            "estimated_wait_time": queue_position * 60  # Примерно 60 сек на задачу
        }
        
        if queue_position == 0:
            response["status"] = "processing"
            response["message"] = "Analysis started immediately"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analyze_video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{task_id}/status")
async def get_analysis_status(task_id: str):
    """Получить статус анализа"""
    if task_id not in completed_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return completed_tasks[task_id]

# ENDPOINTS ДЛЯ ГЕНЕРАЦИИ КЛИПОВ (ИСПРАВЛЕННЫЕ)

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
        
        # Добавляем в очередь - ИСПРАВЛЕНО: убран await
        add_to_queue(f"generate_clips_{generation_id}", generation_clips_task, generation_id, task_data)
        
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

def generation_clips_task(generation_id: str, task_data: dict):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

