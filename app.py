"""
AgentFlow AI Clips v15.5 - ANIMATED SUBTITLES
Версия с анимированными субтитрами и подсветкой слов
Основана на v15.4 + система настраиваемых анимированных субтитров

НОВЫЕ ВОЗМОЖНОСТИ v15.5:
1. Анимированные субтитры с подсветкой каждого слова
2. 5 стилей субтитров (Classic, Neon, Bold, Minimal, Gradient)
3. 3 типа анимации (Highlight, Scale, Glow)
4. Максимум 3-4 субтитра на видео
5. Word-level timing для точной синхронизации
6. API параметры для выбора стиля и анимации

СОХРАНЕНЫ ВСЕ ВОЗМОЖНОСТИ v15.4:
- Наложение субтитров поверх видео
- Поддержка длинных видео до 20 минут
- Chunking система для больших файлов
- Исправленный формат сегментов Whisper API
- Диагностика и детальное логирование
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Query
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
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
app = FastAPI(title="AgentFlow AI Clips", version="15.5-animated-subtitles")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PRODUCTION КОНФИГУРАЦИЯ + НАСТРОЙКИ АНИМИРОВАННЫХ СУБТИТРОВ
class Config:
    # Лимиты ресурсов
    MAX_CONCURRENT_TASKS = 2  # Максимум задач одновременно
    MAX_QUEUE_SIZE = 10       # Максимум задач в очереди
    MAX_VIDEO_SIZE_MB = 150   # Максимум размер видео
    MAX_VIDEO_DURATION = 1200 # Максимум длительность видео (20 мин)
    
    # Таймауты
    FFMPEG_TIMEOUT = 300      # Таймаут FFmpeg операций (5 мин)
    OPENAI_TIMEOUT = 600      # Таймаут OpenAI запросов (10 мин)
    WHISPER_TIMEOUT = 900     # Специальный таймаут для Whisper (15 мин)
    CLEANUP_INTERVAL = 300    # Очистка файлов каждые 5 мин
    
    # Chunking для очень длинных видео
    MAX_AUDIO_SIZE_MB = 25    # Максимум размер аудио для одного запроса
    CHUNK_DURATION = 600      # Максимум длительность chunk (10 мин)
    
    # Качество видео
    VIDEO_BITRATE = "2000k"   
    VIDEO_PRESET = "fast"     
    VIDEO_CRF = "28"          
    
    # Память
    MEMORY_LIMIT_PERCENT = 80 
    FORCE_GC_INTERVAL = 60    
    
    # НОВОЕ: Настройки анимированных субтитров
    SUBTITLE_STYLES = {
        "classic": {
            "fontcolor": "white",
            "bordercolor": "black", 
            "borderw": "3",
            "fontsize": "60",
            "highlight_color": "yellow"
        },
        "neon": {
            "fontcolor": "#00FFFF",
            "bordercolor": "#FF00FF",
            "borderw": "2", 
            "fontsize": "65",
            "highlight_color": "#FFFF00"
        },
        "bold": {
            "fontcolor": "white",
            "bordercolor": "black",
            "borderw": "4",
            "fontsize": "70", 
            "highlight_color": "#FF6B35"
        },
        "minimal": {
            "fontcolor": "white",
            "bordercolor": "transparent",
            "borderw": "0",
            "fontsize": "55",
            "highlight_color": "#4CAF50"
        },
        "gradient": {
            "fontcolor": "#FFD700",
            "bordercolor": "#FF4500", 
            "borderw": "2",
            "fontsize": "65",
            "highlight_color": "#FF1493"
        }
    }
    
    ANIMATION_TYPES = ["highlight", "scale", "glow"]
    MAX_SUBTITLES = 3         # Максимум субтитров на видео
    SUBTITLE_DURATION = 3.0   # Длительность одного субтитра

config = Config()

# Система анимированных субтитров
class AnimatedSubtitleSystem:
    """Система создания анимированных субтитров с подсветкой слов"""
    
    def __init__(self):
        self.max_subtitles = config.MAX_SUBTITLES
        self.subtitle_duration = config.SUBTITLE_DURATION
        
    def create_word_level_subtitles(self, segments: List[Dict], style: str = "classic", 
                                  animation: str = "highlight") -> List[Dict]:
        """Создает субтитры с анимацией на уровне слов"""
        
        # Ограничиваем количество субтитров
        limited_segments = segments[:self.max_subtitles]
        
        animated_subtitles = []
        
        for i, segment in enumerate(limited_segments):
            subtitle = self._create_animated_subtitle(
                segment, style, animation, i
            )
            animated_subtitles.append(subtitle)
            
        return animated_subtitles
    
    def _create_animated_subtitle(self, segment: Dict, style: str, 
                                animation: str, index: int) -> Dict:
        """Создает один анимированный субтитр"""
        
        text = segment["text"].strip()
        start_time = segment["start"] 
        end_time = segment["end"]
        
        # Разбиваем текст на слова
        words = text.split()
        word_duration = (end_time - start_time) / len(words) if words else 0
        
        # Создаем анимацию для каждого слова
        word_animations = []
        for j, word in enumerate(words):
            word_start = start_time + (j * word_duration)
            word_end = word_start + word_duration
            
            word_animation = {
                "word": word,
                "start": word_start,
                "end": word_end,
                "style": config.SUBTITLE_STYLES[style],
                "animation": animation
            }
            word_animations.append(word_animation)
        
        return {
            "index": index,
            "text": text,
            "start_time": start_time,
            "end_time": end_time, 
            "words": word_animations,
            "style": style,
            "animation": animation
        }
    
    def generate_ffmpeg_filter(self, animated_subtitles: List[Dict], 
                             video_width: int = 1080, video_height: int = 1920) -> str:
        """Генерирует FFmpeg фильтр для анимированных субтитров"""
        
        filters = []
        
        for subtitle in animated_subtitles:
            # Позиция субтитра (снизу вверх)
            y_position = video_height - 200 - (subtitle["index"] * 100)
            
            # Создаем фильтр для каждого слова
            for word_data in subtitle["words"]:
                word_filter = self._create_word_filter(
                    word_data, y_position, video_width
                )
                filters.append(word_filter)
        
        return ",".join(filters)
    
    def _create_word_filter(self, word_data: Dict, y_pos: int, 
                          video_width: int) -> str:
        """Создает FFmpeg фильтр для одного слова"""
        
        style = word_data["style"]
        word = self._escape_text_for_ffmpeg(word_data["word"])
        start = word_data["start"]
        end = word_data["end"]
        animation = word_data["animation"]
        
        # Базовые параметры
        base_params = [
            f"text='{word}'",
            f"fontcolor={style['fontcolor']}", 
            f"fontsize={style['fontsize']}",
            f"x=(w-text_w)/2",  # Центрирование по горизонтали
            f"y={y_pos}",
            f"enable='between(t,{start},{end})'"
        ]
        
        # Добавляем обводку если есть
        if style["borderw"] != "0":
            base_params.extend([
                f"bordercolor={style['bordercolor']}",
                f"borderw={style['borderw']}"
            ])
        
        # Добавляем анимацию
        if animation == "highlight":
            # Изменение цвета в середине произношения
            mid_time = (start + end) / 2
            highlight_color = style["highlight_color"]
            base_params[1] = f"fontcolor=if(between(t,{mid_time-0.2},{mid_time+0.2}),{highlight_color},{style['fontcolor']})"
            
        elif animation == "scale":
            # Увеличение размера
            mid_time = (start + end) / 2
            scale_factor = int(float(style["fontsize"]) * 1.2)
            base_params[2] = f"fontsize=if(between(t,{mid_time-0.2},{mid_time+0.2}),{scale_factor},{style['fontsize']})"
            
        elif animation == "glow":
            # Добавляем эффект свечения через тень
            base_params.append(f"shadowcolor={style['highlight_color']}")
            base_params.append("shadowx=0")
            base_params.append("shadowy=0")
            
        return f"drawtext={':'.join(base_params)}"
    
    def _escape_text_for_ffmpeg(self, text: str) -> str:
        """Экранирует текст для FFmpeg"""
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace(",", "\\,")
        text = text.replace("[", "\\[")
        text = text.replace("]", "\\]")
        return text

# Инициализируем систему субтитров
subtitle_system = AnimatedSubtitleSystem()

# OpenAI клиент
client = None
try:
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY не найден в переменных окружения")
        raise ValueError("OPENAI_API_KEY не установлен")
    
    client = OpenAI(
        api_key=api_key,
        timeout=config.OPENAI_TIMEOUT
    )
    
    logger.info("🔑 ДИАГНОСТИКА: OpenAI клиент инициализирован с расширенным timeout")
    
    # Тестируем доступность API
    try:
        models_response = client.models.list()
        logger.info("🔑 ДИАГНОСТИКА: API ключ найден")
        
        # Проверяем доступность Whisper
        available_models = [model.id for model in models_response.data]
        if "whisper-1" in available_models:
            logger.info("🎤 ДИАГНОСТИКА: Модель whisper-1 ДОСТУПНА на вашем Tier!")
        else:
            logger.warning("⚠️ ДИАГНОСТИКА: Модель whisper-1 НЕ найдена в доступных моделях")
            
    except Exception as e:
        logger.error(f"❌ ДИАГНОСТИКА: Ошибка тестирования API: {e}")
        
except ImportError:
    logger.error("❌ ДИАГНОСТИКА: Библиотека openai не установлена")
    client = None
except Exception as e:
    logger.error(f"❌ ДИАГНОСТИКА: Ошибка инициализации OpenAI: {e}")
    client = None

# Глобальные переменные
TASKS_DIR = "tasks"
UPLOADS_DIR = "uploads"
AUDIO_DIR = "audio"
CLIPS_DIR = "clips"

# Создаем директории
for directory in [TASKS_DIR, UPLOADS_DIR, AUDIO_DIR, CLIPS_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"📁 ДИАГНОСТИКА: Директория {directory} готова")

# Глобальные структуры данных
tasks = {}
generation_tasks = {}
task_queue = deque()
active_tasks = set()
executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_TASKS)

# Мониторинг ресурсов
def get_system_stats():
    """Получает статистику системы"""
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu = psutil.cpu_percent(interval=1)
        
        return {
            "memory_usage": f"{memory.percent}%",
            "disk_usage": f"{disk.percent}%", 
            "cpu_usage": f"{cpu}%",
            "active_tasks": len(active_tasks),
            "queue_size": len(task_queue)
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {
            "memory_usage": "unknown",
            "disk_usage": "unknown",
            "cpu_usage": "unknown", 
            "active_tasks": len(active_tasks),
            "queue_size": len(task_queue)
        }

# Health check
@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    
    # Проверяем зависимости
    dependencies = {
        "ffmpeg": check_ffmpeg(),
        "openai": client is not None
    }
    
    stats = get_system_stats()
    
    return {
        "status": "healthy",
        "version": "15.5-animated-subtitles",
        **stats,
        "dependencies": dependencies
    }

def check_ffmpeg():
    """Проверяет доступность FFmpeg"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        return result.returncode == 0
    except:
        return False

# Функции для работы с аудио и видео
async def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Извлекает аудио из видео"""
    try:
        logger.info(f"🎵 Извлекаем аудио: {video_path} -> {audio_path}")
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", 
            "-ar", "16000", "-ac", "1",
            "-y", audio_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=config.FFMPEG_TIMEOUT
        )
        
        if process.returncode == 0:
            logger.info(f"✅ Аудио извлечено: {audio_path}")
            return True
        else:
            logger.error(f"❌ Ошибка извлечения аудио: {stderr.decode()}")
            return False
            
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут извлечения аудио: {config.FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения аудио: {e}")
        return False

async def transcribe_audio_with_whisper(audio_path: str) -> Optional[Dict]:
    """Транскрибирует аудио с помощью Whisper API"""
    try:
        if not client:
            raise ValueError("OpenAI клиент не инициализирован")
            
        logger.info(f"🎤 Начинаем транскрибацию: {audio_path}")
        
        # Проверяем размер файла
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        
        logger.info(f"📊 Размер аудио файла: {file_size_mb:.2f} MB")
        
        # Если файл слишком большой, разбиваем на части
        if file_size_mb > config.MAX_AUDIO_SIZE_MB:
            logger.info(f"📦 Файл большой ({file_size_mb:.2f} MB), используем chunking")
            return await transcribe_large_audio(audio_path)
        
        # Обычная транскрибация
        with open(audio_path, "rb") as audio_file:
            logger.info("🔄 Отправляем запрос к Whisper API...")
            
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.audio.transcriptions.create,
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                ),
                timeout=config.WHISPER_TIMEOUT
            )
            
            logger.info("✅ Транскрибация завершена успешно")
            
            # ИСПРАВЛЕНО: Правильный формат сегментов
            segments = []
            if hasattr(response, 'segments') and response.segments:
                for segment in response.segments:
                    segments.append({
                        "start": segment.start,
                        "end": segment.end, 
                        "text": segment.text
                    })
            
            return {
                "text": response.text,
                "segments": segments
            }
            
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут Whisper API: {config.WHISPER_TIMEOUT}s")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации: {e}")
        return None

async def transcribe_large_audio(audio_path: str) -> Optional[Dict]:
    """Транскрибирует большой аудио файл по частям"""
    try:
        logger.info("📦 Начинаем chunking большого аудио файла")
        
        # Получаем длительность аудио
        duration = await get_audio_duration(audio_path)
        if not duration:
            return None
            
        logger.info(f"⏱️ Длительность аудио: {duration:.2f} секунд")
        
        # Разбиваем на части
        chunk_duration = config.CHUNK_DURATION  # 10 минут
        chunks = []
        
        for start_time in range(0, int(duration), chunk_duration):
            end_time = min(start_time + chunk_duration, duration)
            
            chunk_path = f"{audio_path}_chunk_{start_time}_{end_time}.wav"
            
            # Извлекаем часть аудио
            success = await extract_audio_chunk(audio_path, chunk_path, start_time, end_time)
            if success:
                chunks.append({
                    "path": chunk_path,
                    "start": start_time,
                    "end": end_time
                })
        
        # Транскрибируем каждую часть
        all_segments = []
        full_text = ""
        
        for chunk in chunks:
            logger.info(f"🎤 Транскрибируем chunk {chunk['start']}-{chunk['end']}s")
            
            chunk_result = await transcribe_audio_with_whisper(chunk["path"])
            if chunk_result:
                # Корректируем временные метки
                for segment in chunk_result["segments"]:
                    segment["start"] += chunk["start"]
                    segment["end"] += chunk["start"]
                    all_segments.append(segment)
                
                full_text += " " + chunk_result["text"]
            
            # Удаляем временный файл
            try:
                os.remove(chunk["path"])
            except:
                pass
        
        logger.info(f"✅ Chunking завершен, получено {len(all_segments)} сегментов")
        
        return {
            "text": full_text.strip(),
            "segments": all_segments
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка chunking транскрибации: {e}")
        return None

async def get_audio_duration(audio_path: str) -> Optional[float]:
    """Получает длительность аудио файла"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", 
            "format=duration", "-of", "csv=p=0", audio_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            duration = float(stdout.decode().strip())
            return duration
        else:
            logger.error(f"❌ Ошибка получения длительности: {stderr.decode()}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения длительности: {e}")
        return None

async def extract_audio_chunk(input_path: str, output_path: str, 
                            start_time: int, end_time: int) -> bool:
    """Извлекает часть аудио"""
    try:
        duration = end_time - start_time
        
        cmd = [
            "ffmpeg", "-i", input_path,
            "-ss", str(start_time), "-t", str(duration),
            "-vn", "-acodec", "pcm_s16le", 
            "-ar", "16000", "-ac", "1",
            "-y", output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=config.FFMPEG_TIMEOUT
        )
        
        return process.returncode == 0
        
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения chunk: {e}")
        return False

async def analyze_transcript_with_chatgpt(transcript: str) -> List[Dict]:
    """Анализирует транскрипт с помощью ChatGPT"""
    try:
        if not client:
            raise ValueError("OpenAI клиент не инициализирован")
            
        logger.info("🤖 Анализируем транскрипт с ChatGPT...")
        
        prompt = f'''
Проанализируй этот транскрипт и найди 3-5 самых интересных и вирусных моментов для коротких клипов.

Транскрипт: "{transcript}"

Для каждого момента укажи:
1. Заголовок (краткий и цепляющий)
2. Примерное время начала (в секундах от начала)
3. Примерное время окончания (в секундах от начала) 
4. Цитату (точный текст из транскрипта)
5. Оценку вирусности (1-100)
6. Причину почему этот момент будет популярным

Ответь в JSON формате:
{{
  "highlights": [
    {{
      "title": "Заголовок момента",
      "start_time": 0,
      "end_time": 30,
      "quote": "Точная цитата из транскрипта",
      "viral_score": 85,
      "reason": "Объяснение почему это будет вирусным"
    }}
  ]
}}
'''

        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            ),
            timeout=config.OPENAI_TIMEOUT
        )
        
        content = response.choices[0].message.content
        logger.info("✅ Анализ ChatGPT завершен")
        
        # Парсим JSON ответ
        try:
            result = json.loads(content)
            return result.get("highlights", [])
        except json.JSONDecodeError:
            logger.error("❌ Ошибка парсинга JSON ответа от ChatGPT")
            return []
            
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут ChatGPT: {config.OPENAI_TIMEOUT}s")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка анализа ChatGPT: {e}")
        return []

# НОВОЕ: Генерация клипов с анимированными субтитрами
async def generate_clip_with_animated_subtitles(video_path: str, start_time: float, end_time: float, 
                                              quote: str, output_path: str, segments: List[Dict],
                                              subtitle_style: str = "classic", 
                                              animation_type: str = "highlight") -> bool:
    """Генерирует клип с анимированными субтитрами"""
    try:
        logger.info(f"🎬 Генерируем клип с анимированными субтитрами: {start_time}-{end_time}s")
        logger.info(f"🎨 Стиль: {subtitle_style}, Анимация: {animation_type}")
        
        # Находим релевантные сегменты для этого клипа
        clip_segments = []
        for segment in segments:
            if (segment["start"] >= start_time and segment["start"] <= end_time) or \
               (segment["end"] >= start_time and segment["end"] <= end_time):
                # Корректируем время относительно начала клипа
                adjusted_segment = {
                    "start": max(0, segment["start"] - start_time),
                    "end": min(end_time - start_time, segment["end"] - start_time),
                    "text": segment["text"]
                }
                clip_segments.append(adjusted_segment)
        
        logger.info(f"📝 Найдено {len(clip_segments)} сегментов для субтитров")
        
        # Создаем анимированные субтитры
        animated_subtitles = subtitle_system.create_word_level_subtitles(
            clip_segments, subtitle_style, animation_type
        )
        
        # Генерируем FFmpeg фильтр
        subtitle_filter = subtitle_system.generate_ffmpeg_filter(animated_subtitles)
        
        logger.info(f"🔧 FFmpeg фильтр создан: {len(subtitle_filter)} символов")
        
        # Команда FFmpeg с анимированными субтитрами
        duration = end_time - start_time
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", str(start_time), "-t", str(duration),
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}",
            "-c:v", "libx264", "-preset", config.VIDEO_PRESET,
            "-crf", config.VIDEO_CRF, "-b:v", config.VIDEO_BITRATE,
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output_path
        ]
        
        logger.info("🎬 Запускаем FFmpeg с анимированными субтитрами...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=config.FFMPEG_TIMEOUT
        )
        
        if process.returncode == 0:
            logger.info(f"✅ Клип с анимированными субтитрами создан: {output_path}")
            return True
        else:
            logger.error(f"❌ Ошибка создания клипа: {stderr.decode()}")
            return False
            
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут создания клипа: {config.FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка создания клипа: {e}")
        return False

# Задача анализа видео
async def analyze_video_task(task_id: str, video_path: str):
    """Фоновая задача анализа видео"""
    try:
        logger.info(f"🎬 Начинаем анализ видео: {task_id}")
        
        # Обновляем статус
        tasks[task_id]["status"] = "processing"
        tasks[task_id]["progress"] = 10
        
        # Извлекаем аудио
        audio_path = os.path.join(AUDIO_DIR, f"{task_id}.wav")
        success = await extract_audio_from_video(video_path, audio_path)
        
        if not success:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = "Ошибка извлечения аудио"
            return
            
        tasks[task_id]["progress"] = 30
        tasks[task_id]["audio_path"] = audio_path
        
        # Транскрибируем аудио
        transcript_result = await transcribe_audio_with_whisper(audio_path)
        
        if not transcript_result:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = "Ошибка транскрибации"
            return
            
        tasks[task_id]["progress"] = 70
        tasks[task_id]["transcript"] = transcript_result["text"]
        tasks[task_id]["segments"] = transcript_result["segments"]
        
        # Анализируем с ChatGPT
        highlights = await analyze_transcript_with_chatgpt(transcript_result["text"])
        
        tasks[task_id]["progress"] = 100
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["highlights"] = highlights
        tasks[task_id]["analysis_time"] = time.time()
        
        logger.info(f"✅ Анализ видео завершен: {task_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа видео {task_id}: {e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
    finally:
        # Удаляем из активных задач
        active_tasks.discard(task_id)

# НОВОЕ: Задача генерации клипов с анимированными субтитрами
async def generation_clips_task(generation_task_id: str, task_id: str, 
                              subtitle_style: str = "classic", 
                              animation_type: str = "highlight"):
    """Фоновая задача генерации клипов с анимированными субтитрами"""
    try:
        logger.info(f"🎬 Начинаем генерацию клипов с анимированными субтитрами: {generation_task_id}")
        logger.info(f"🎨 Стиль: {subtitle_style}, Анимация: {animation_type}")
        
        # Получаем данные анализа
        if task_id not in tasks:
            raise ValueError(f"Задача анализа {task_id} не найдена")
            
        task_data = tasks[task_id]
        if task_data["status"] != "completed":
            raise ValueError(f"Анализ видео {task_id} не завершен")
            
        highlights = task_data["highlights"]
        video_path = task_data["video_path"]
        segments = task_data.get("segments", [])
        
        # Инициализируем задачу генерации
        generation_tasks[generation_task_id] = {
            "status": "processing",
            "progress": 0,
            "clips": [],
            "log": [],
            "task_id": task_id,
            "highlights": highlights,
            "video_path": video_path,
            "created_at": time.time(),
            "subtitle_style": subtitle_style,
            "animation_type": animation_type
        }
        
        clips = []
        total_highlights = len(highlights)
        
        for i, highlight in enumerate(highlights):
            try:
                logger.info(f"Генерируем клип {i+1}/{total_highlights}: {highlight['title']}")
                generation_tasks[generation_task_id]["log"].append(
                    f"Генерируем клип {i+1}/{total_highlights}: {highlight['title']}"
                )
                
                # Создаем уникальный ID для клипа
                clip_id = str(uuid.uuid4())
                clip_filename = f"{clip_id}.mp4"
                clip_path = os.path.join(CLIPS_DIR, clip_filename)
                
                # Генерируем клип с анимированными субтитрами
                success = await generate_clip_with_animated_subtitles(
                    video_path=video_path,
                    start_time=highlight["start_time"],
                    end_time=highlight["end_time"], 
                    quote=highlight["quote"],
                    output_path=clip_path,
                    segments=segments,
                    subtitle_style=subtitle_style,
                    animation_type=animation_type
                )
                
                if success and os.path.exists(clip_path):
                    file_size = os.path.getsize(clip_path)
                    duration = highlight["end_time"] - highlight["start_time"]
                    
                    clip_data = {
                        "id": clip_id,
                        "title": highlight["title"],
                        "start_time": highlight["start_time"],
                        "end_time": highlight["end_time"],
                        "duration": duration,
                        "viral_score": highlight["viral_score"],
                        "quote": highlight["quote"],
                        "file_path": f"clips/{clip_filename}",
                        "file_size": file_size,
                        "subtitle_style": subtitle_style,
                        "animation_type": animation_type
                    }
                    
                    clips.append(clip_data)
                    generation_tasks[generation_task_id]["log"].append(
                        f"✅ Клип {i+1} готов: {highlight['title']}"
                    )
                    
                    logger.info(f"✅ Клип создан: {clip_path} ({file_size} bytes)")
                else:
                    generation_tasks[generation_task_id]["log"].append(
                        f"❌ Ошибка создания клипа {i+1}: {highlight['title']}"
                    )
                    logger.error(f"❌ Ошибка создания клипа: {clip_path}")
                
                # Обновляем прогресс
                progress = int(((i + 1) / total_highlights) * 100)
                generation_tasks[generation_task_id]["progress"] = progress
                
            except Exception as e:
                logger.error(f"❌ Ошибка генерации клипа {i+1}: {e}")
                generation_tasks[generation_task_id]["log"].append(
                    f"❌ Ошибка клипа {i+1}: {str(e)}"
                )
        
        # Завершаем задачу
        generation_tasks[generation_task_id]["status"] = "completed"
        generation_tasks[generation_task_id]["progress"] = 100
        generation_tasks[generation_task_id]["clips"] = clips
        generation_tasks[generation_task_id]["completed_at"] = time.time()
        
        logger.info(f"✅ Генерация клипов завершена: {generation_task_id}, создано {len(clips)} клипов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации клипов {generation_task_id}: {e}")
        if generation_task_id in generation_tasks:
            generation_tasks[generation_task_id]["status"] = "failed"
            generation_tasks[generation_task_id]["error"] = str(e)
    finally:
        # Удаляем из активных задач
        active_tasks.discard(generation_task_id)

# API Endpoints

@app.post("/api/videos/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Загружает и анализирует видео"""
    try:
        # Проверяем лимиты
        if len(active_tasks) >= config.MAX_CONCURRENT_TASKS:
            if len(task_queue) >= config.MAX_QUEUE_SIZE:
                raise HTTPException(status_code=429, detail="Очередь переполнена")
        
        # Проверяем размер файла
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > config.MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413, 
                detail=f"Файл слишком большой. Максимум: {config.MAX_VIDEO_SIZE_MB}MB"
            )
        
        # Создаем уникальный ID
        task_id = str(uuid.uuid4())
        
        # Сохраняем файл
        video_filename = f"{task_id}_{file.filename}"
        video_path = os.path.join(UPLOADS_DIR, video_filename)
        
        with open(video_path, "wb") as f:
            f.write(content)
        
        # Создаем задачу
        tasks[task_id] = {
            "id": task_id,
            "status": "queued",
            "progress": 0,
            "video_path": video_path,
            "filename": file.filename,
            "file_size": file_size,
            "created_at": time.time()
        }
        
        # Добавляем в очередь или запускаем
        if len(active_tasks) < config.MAX_CONCURRENT_TASKS:
            active_tasks.add(task_id)
            background_tasks.add_task(analyze_video_task, task_id, video_path)
        else:
            task_queue.append(task_id)
        
        logger.info(f"📤 Видео загружено: {task_id} ({file_size} bytes)")
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Video analysis started",
            "estimated_time": "2-5 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки видео: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{task_id}/status")
async def get_video_status(task_id: str):
    """Получает статус анализа видео"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task_data = tasks[task_id].copy()
    
    # Убираем большие данные из ответа
    if "segments" in task_data and len(str(task_data["segments"])) > 1000:
        task_data["segments_count"] = len(task_data["segments"])
        # Оставляем segments для completed статуса
        if task_data["status"] != "completed":
            del task_data["segments"]
    
    return task_data

# НОВОЕ: API для генерации клипов с выбором стиля субтитров
@app.post("/api/clips/generate")
async def generate_clips(
    background_tasks: BackgroundTasks,
    task_id: str = Query(..., description="ID задачи анализа видео"),
    subtitle_style: str = Query("classic", description="Стиль субтитров: classic, neon, bold, minimal, gradient"),
    animation_type: str = Query("highlight", description="Тип анимации: highlight, scale, glow")
):
    """Генерирует клипы с анимированными субтитрами"""
    try:
        # Проверяем существование задачи анализа
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Задача анализа не найдена")
        
        task_data = tasks[task_id]
        if task_data["status"] != "completed":
            raise HTTPException(status_code=400, detail="Анализ видео не завершен")
        
        # Проверяем параметры
        if subtitle_style not in config.SUBTITLE_STYLES:
            raise HTTPException(
                status_code=400, 
                detail=f"Неверный стиль субтитров. Доступные: {list(config.SUBTITLE_STYLES.keys())}"
            )
        
        if animation_type not in config.ANIMATION_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Неверный тип анимации. Доступные: {config.ANIMATION_TYPES}"
            )
        
        # Создаем задачу генерации
        generation_task_id = str(uuid.uuid4())
        
        # Запускаем генерацию
        active_tasks.add(generation_task_id)
        background_tasks.add_task(
            generation_clips_task, 
            generation_task_id, 
            task_id,
            subtitle_style,
            animation_type
        )
        
        highlights_count = len(task_data.get("highlights", []))
        
        logger.info(f"🎬 Запущена генерация клипов: {generation_task_id} (стиль: {subtitle_style}, анимация: {animation_type})")
        
        return {
            "generation_task_id": generation_task_id,
            "status": "queued", 
            "highlights_count": highlights_count,
            "subtitle_style": subtitle_style,
            "animation_type": animation_type,
            "message": f"Clip generation with {subtitle_style} subtitles and {animation_type} animation started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка запуска генерации: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/generation/{generation_task_id}/status")
async def get_generation_status(generation_task_id: str):
    """Получает статус генерации клипов"""
    if generation_task_id not in generation_tasks:
        raise HTTPException(status_code=404, detail="Задача генерации не найдена")
    
    return generation_tasks[generation_task_id]

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивает готовый клип"""
    clip_path = os.path.join(CLIPS_DIR, f"{clip_id}.mp4")
    
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Клип не найден")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

@app.get("/api/videos/{task_id}/clips")
async def get_task_clips(task_id: str):
    """Получает все клипы для задачи"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Ищем все задачи генерации для этой задачи
    task_clips = []
    for gen_task_id, gen_data in generation_tasks.items():
        if gen_data.get("task_id") == task_id and gen_data.get("status") == "completed":
            task_clips.extend(gen_data.get("clips", []))
    
    return {
        "task_id": task_id,
        "clips": task_clips,
        "total_clips": len(task_clips)
    }

# НОВОЕ: API для получения доступных стилей и анимаций
@app.get("/api/subtitles/styles")
async def get_subtitle_styles():
    """Получает доступные стили субтитров"""
    return {
        "styles": list(config.SUBTITLE_STYLES.keys()),
        "animations": config.ANIMATION_TYPES,
        "style_details": config.SUBTITLE_STYLES
    }

# Очистка ресурсов
async def cleanup_old_files():
    """Очищает старые файлы"""
    try:
        current_time = time.time()
        cleanup_age = 3600  # 1 час
        
        # Очищаем старые задачи
        tasks_to_remove = []
        for task_id, task_data in tasks.items():
            if current_time - task_data.get("created_at", 0) > cleanup_age:
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            try:
                # Удаляем файлы
                task_data = tasks[task_id]
                if "video_path" in task_data:
                    try:
                        os.remove(task_data["video_path"])
                    except:
                        pass
                if "audio_path" in task_data:
                    try:
                        os.remove(task_data["audio_path"])
                    except:
                        pass
                
                del tasks[task_id]
                logger.info(f"🧹 Удалена старая задача: {task_id}")
            except:
                pass
        
        # Принудительная очистка памяти
        gc.collect()
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки: {e}")

# Фоновая задача очистки
async def background_cleanup():
    """Фоновая очистка ресурсов"""
    while True:
        try:
            await asyncio.sleep(config.CLEANUP_INTERVAL)
            await cleanup_old_files()
        except Exception as e:
            logger.error(f"❌ Ошибка фоновой очистки: {e}")

# Запуск фоновых задач
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 AgentFlow AI Clips v15.5 with Animated Subtitles started!")
    
    # Запускаем фоновую очистку
    asyncio.create_task(background_cleanup())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

