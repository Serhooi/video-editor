"""
AgentFlow AI Clips v15.4 - SUBTITLES FIXED
Полная версия с наложением субтитров поверх видео
Основана на рабочей версии v15.3.2 (998 строк) + функции субтитров

НОВЫЕ ВОЗМОЖНОСТИ:
1. Наложение субтитров с помощью FFmpeg drawtext
2. Стилизованный текст (белый цвет, черная обводка)  
3. Позиционирование внизу экрана
4. Автоматическое разбиение длинного текста на строки
5. Поддержка специальных символов и кавычек

СОХРАНЕНЫ ВСЕ ВОЗМОЖНОСТИ v15.3.2:
- Поддержка длинных видео до 20 минут
- Chunking система для больших аудио файлов
- Исправленный формат сегментов Whisper API
- Диагностика и детальное логирование
- Увеличенные timeout'ы
- Queue система для масштабирования
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
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
app = FastAPI(title="AgentFlow AI Clips", version="15.4-subtitles-fixed")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PRODUCTION КОНФИГУРАЦИЯ - ПОЛНАЯ ИЗ v15.3.2 + НАСТРОЙКИ СУБТИТРОВ
class Config:
    # Лимиты ресурсов
    MAX_CONCURRENT_TASKS = 2  # Максимум задач одновременно
    MAX_QUEUE_SIZE = 10       # Максимум задач в очереди
    MAX_VIDEO_SIZE_MB = 150   # Максимум размер видео
    MAX_VIDEO_DURATION = 1200 # УВЕЛИЧЕНО: Максимум длительность видео (20 мин)
    
    # Таймауты - ИСПРАВЛЕНО ДЛЯ ДЛИННЫХ ВИДЕО
    FFMPEG_TIMEOUT = 300      # УВЕЛИЧЕНО: Таймаут FFmpeg операций (5 мин)
    OPENAI_TIMEOUT = 600      # УВЕЛИЧЕНО: Таймаут OpenAI запросов (10 мин)
    WHISPER_TIMEOUT = 900     # НОВОЕ: Специальный таймаут для Whisper (15 мин)
    CLEANUP_INTERVAL = 300    # Очистка файлов каждые 5 мин
    
    # Chunking для очень длинных видео
    MAX_AUDIO_SIZE_MB = 25    # НОВОЕ: Максимум размер аудио для одного запроса
    CHUNK_DURATION = 600      # НОВОЕ: Максимум длительность chunk (10 мин)
    
    # Качество видео (оптимизированное)
    VIDEO_BITRATE = "2000k"   # Уменьшенный битрейт
    VIDEO_PRESET = "fast"     # Быстрый пресет
    VIDEO_CRF = "28"          # Сжатие
    
    # Память
    MEMORY_LIMIT_PERCENT = 80 # Лимит использования памяти
    FORCE_GC_INTERVAL = 60    # Принудительная очистка памяти
    
    # НОВОЕ: Настройки субтитров
    SUBTITLE_FONTSIZE = 60        # Размер шрифта
    SUBTITLE_FONTCOLOR = "white"  # Цвет текста
    SUBTITLE_BORDERCOLOR = "black" # Цвет обводки
    SUBTITLE_BORDERW = 3          # Толщина обводки
    SUBTITLE_Y_POSITION = "h-150" # Позиция (150px от низа)
    SUBTITLE_MAX_CHARS_PER_LINE = 40  # Максимум символов в строке

config = Config()

# OpenAI клиент - ДИАГНОСТИЧЕСКАЯ ВЕРСИЯ
client = None
try:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    
    logger.info(f"🔍 ДИАГНОСТИКА: Инициализация OpenAI клиента...")
    
    if api_key:
        logger.info(f"🔑 ДИАГНОСТИКА: API ключ найден")
        logger.info(f"🔑 ДИАГНОСТИКА: Длина ключа: {len(api_key)} символов")
        logger.info(f"🔑 ДИАГНОСТИКА: Начинается с: {api_key[:15]}...")
        logger.info(f"🔑 ДИАГНОСТИКА: Тип: {'Project key' if api_key.startswith('sk-proj-') else 'Legacy key'}")
        
        # УВЕЛИЧЕННЫЙ TIMEOUT ДЛЯ WHISPER
        client = OpenAI(api_key=api_key, timeout=config.WHISPER_TIMEOUT)
        logger.info("✅ ДИАГНОСТИКА: OpenAI client инициализирован с расширенным timeout")
        
        # ТЕСТОВЫЙ ЗАПРОС ДЛЯ ПРОВЕРКИ ДОСТУПНОСТИ
        try:
            logger.info("🧪 ДИАГНОСТИКА: Тестируем доступность API...")
            test_response = client.models.list()
            available_models = [model.id for model in test_response.data]
            
            if "whisper-1" in available_models:
                logger.info("✅ ДИАГНОСТИКА: Модель whisper-1 ДОСТУПНА на вашем Tier!")
            else:
                logger.error("❌ ДИАГНОСТИКА: Модель whisper-1 НЕ ДОСТУПНА на вашем Tier!")
                logger.info(f"🔍 ДИАГНОСТИКА: Доступные модели: {available_models[:5]}...")
                
        except Exception as test_error:
            logger.error(f"❌ ДИАГНОСТИКА: Ошибка тестового запроса: {test_error}")
            
    else:
        logger.error("❌ ДИАГНОСТИКА: OPENAI_API_KEY не найден в переменных окружения")
        
except ImportError as e:
    logger.error(f"❌ ДИАГНОСТИКА: Ошибка импорта OpenAI: {e}")
except Exception as e:
    logger.error(f"❌ ДИАГНОСТИКА: Общая ошибка инициализации OpenAI: {e}")

# Глобальные переменные
completed_tasks = {}
generation_queue = {}
task_queue = deque()
active_tasks = {}
executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_TASKS)

# Создание директорий
os.makedirs("uploads", exist_ok=True)
os.makedirs("audio", exist_ok=True)
os.makedirs("clips", exist_ok=True)

# НОВЫЕ ФУНКЦИИ ДЛЯ СУБТИТРОВ
def escape_text_for_ffmpeg(text: str) -> str:
    """
    Экранирует текст для безопасного использования в FFmpeg drawtext фильтре
    """
    # Заменяем специальные символы
    text = text.replace("'", "\\'")  # Одинарные кавычки
    text = text.replace('"', '\\"')  # Двойные кавычки
    text = text.replace(":", "\\:")  # Двоеточия
    text = text.replace(",", "\\,")  # Запятые
    text = text.replace("[", "\\[")  # Квадратные скобки
    text = text.replace("]", "\\]")
    text = text.replace("(", "\\(")  # Круглые скобки
    text = text.replace(")", "\\)")
    text = text.replace("=", "\\=")  # Знак равенства
    text = text.replace(";", "\\;")  # Точка с запятой
    
    return text

def split_text_for_subtitles(text: str, max_chars: int = None) -> List[str]:
    """
    Разбивает длинный текст на строки для субтитров
    """
    if max_chars is None:
        max_chars = config.SUBTITLE_MAX_CHARS_PER_LINE
    
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + " " + word) <= max_chars:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines

def create_subtitle_filter(text: str) -> str:
    """
    Создает FFmpeg фильтр для наложения субтитров
    """
    # Экранируем текст
    escaped_text = escape_text_for_ffmpeg(text)
    
    # Разбиваем на строки если текст длинный
    lines = split_text_for_subtitles(escaped_text)
    
    if len(lines) == 1:
        # Одна строка
        subtitle_filter = (
            f"drawtext=text='{lines[0]}'"
            f":fontsize={config.SUBTITLE_FONTSIZE}"
            f":fontcolor={config.SUBTITLE_FONTCOLOR}"
            f":bordercolor={config.SUBTITLE_BORDERCOLOR}"
            f":borderw={config.SUBTITLE_BORDERW}"
            f":x=(w-text_w)/2"
            f":y={config.SUBTITLE_Y_POSITION}"
        )
    else:
        # Несколько строк
        subtitle_filters = []
        for i, line in enumerate(lines):
            y_offset = f"{config.SUBTITLE_Y_POSITION}+{i*70}"  # 70px между строками
            filter_part = (
                f"drawtext=text='{line}'"
                f":fontsize={config.SUBTITLE_FONTSIZE}"
                f":fontcolor={config.SUBTITLE_FONTCOLOR}"
                f":bordercolor={config.SUBTITLE_BORDERCOLOR}"
                f":borderw={config.SUBTITLE_BORDERW}"
                f":x=(w-text_w)/2"
                f":y={y_offset}"
            )
            subtitle_filters.append(filter_part)
        
        subtitle_filter = ",".join(subtitle_filters)
    
    return subtitle_filter

# Функции мониторинга ресурсов
def get_memory_usage():
    """Получить использование памяти в процентах"""
    return psutil.virtual_memory().percent

def get_disk_usage():
    """Получить использование диска в процентах"""
    return psutil.disk_usage('/').percent

def get_cpu_usage():
    """Получить использование CPU в процентах"""
    return psutil.cpu_percent(interval=1)

def cleanup_old_files():
    """Очистка старых файлов"""
    try:
        current_time = time.time()
        
        # Очистка uploads (старше 1 часа)
        for file_path in Path("uploads").glob("*"):
            if current_time - file_path.stat().st_mtime > 3600:
                file_path.unlink()
                logger.info(f"🗑️ Удален старый файл: {file_path}")
        
        # Очистка audio (старше 30 минут)
        for file_path in Path("audio").glob("*"):
            if current_time - file_path.stat().st_mtime > 1800:
                file_path.unlink()
                logger.info(f"🗑️ Удален аудио файл: {file_path}")
        
        # Очистка clips (старше 2 часов)
        for file_path in Path("clips").glob("*"):
            if current_time - file_path.stat().st_mtime > 7200:
                file_path.unlink()
                logger.info(f"🗑️ Удален клип: {file_path}")
                
        # Принудительная очистка памяти
        gc.collect()
        
    except Exception as e:
        logger.error(f"Ошибка очистки файлов: {e}")

def add_to_queue(task_id: str, task_data: dict):
    """Добавить задачу в очередь"""
    if len(task_queue) >= config.MAX_QUEUE_SIZE:
        raise HTTPException(status_code=429, detail="Queue is full")
    
    task_queue.append((task_id, task_data))
    logger.info(f"🚀 ДИАГНОСТИКА: Задача {task_id} добавлена в очередь, позиция: {len(task_queue)-1}")
    
    # Запуск обработки если есть свободные слоты
    if len(active_tasks) < config.MAX_CONCURRENT_TASKS:
        process_queue()

def process_queue():
    """Обработка очереди задач"""
    while task_queue and len(active_tasks) < config.MAX_CONCURRENT_TASKS:
        task_id, task_data = task_queue.popleft()
        active_tasks[task_id] = {
            "status": "processing",
            "start_time": time.time()
        }
        
        # Запуск задачи в отдельном потоке
        future = executor.submit(analyze_video_task, task_id, task_data)
        
        def task_completed(fut):
            try:
                result = fut.result()
                completed_tasks[task_id] = result
            except Exception as e:
                logger.error(f"❌ ДИАГНОСТИКА: Analysis failed for task {task_id}: {e}")
                logger.error(f"❌ ДИАГНОСТИКА: Traceback: {traceback.format_exc()}")
                completed_tasks[task_id] = {
                    "status": "failed",
                    "error": str(e),
                    "progress": 0
                }
            finally:
                if task_id in active_tasks:
                    del active_tasks[task_id]
                process_queue()  # Обработка следующей задачи
        
        future.add_done_callback(task_completed)

# ИСПРАВЛЕННАЯ ФУНКЦИЯ ТРАНСКРИБАЦИИ С ПОДДЕРЖКОЙ НОВОГО ФОРМАТА СЕГМЕНТОВ
def transcribe_single_audio(audio_path: str, time_offset: float = 0) -> Tuple[str, List[dict]]:
    """
    Транскрибация одного аудио файла с исправленной обработкой сегментов
    """
    try:
        logger.info(f"🔍 ДИАГНОСТИКА: Начинаем транскрибацию файла {audio_path}")
        
        if not client:
            raise Exception("OpenAI client не инициализирован")
        
        logger.info("✅ ДИАГНОСТИКА: OpenAI client инициализирован")
        
        # Проверяем размер файла
        file_size = os.path.getsize(audio_path)
        logger.info(f"📁 ДИАГНОСТИКА: Размер аудио файла: {file_size} байт ({file_size/1024/1024:.2f} MB)")
        
        # Проверяем API ключ
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            logger.info(f"🔑 ДИАГНОСТИКА: API ключ найден, начинается с: {api_key[:15]}...")
            logger.info(f"🔑 ДИАГНОСТИКА: Тип ключа: {'Project key' if api_key.startswith('sk-proj-') else 'Legacy key'}")
        
        logger.info("🎤 ДИАГНОСТИКА: Отправляем запрос к Whisper API...")
        logger.info("🎤 ДИАГНОСТИКА: Модель: whisper-1")
        logger.info("🎤 ДИАГНОСТИКА: Формат ответа: verbose_json")
        logger.info("🎤 ДИАГНОСТИКА: Язык: en")
        
        with open(audio_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                language="en"
            )
        
        logger.info("✅ ДИАГНОСТИКА: Whisper API ответил успешно!")
        
        # Получаем транскрипт
        transcript = response.text
        logger.info(f"📝 ДИАГНОСТИКА: Длина транскрипта: {len(transcript)} символов")
        
        # ИСПРАВЛЕННАЯ ОБРАБОТКА СЕГМЕНТОВ - ПОДДЕРЖКА НОВОГО ФОРМАТА
        segments = []
        
        if hasattr(response, 'segments') and response.segments:
            logger.info(f"📊 ДИАГНОСТИКА: Количество сегментов: {len(response.segments)}")
            
            try:
                # Проверяем формат первого сегмента
                first_seg = response.segments[0]
                logger.info(f"🔍 ДИАГНОСТИКА: Тип первого сегмента: {type(first_seg)}")
                logger.info(f"🔍 ДИАГНОСТИКА: Содержимое первого сегмента: {first_seg}")
                
                # УНИВЕРСАЛЬНАЯ ОБРАБОТКА СЕГМЕНТОВ
                segments = []
                for i, seg in enumerate(response.segments):
                    try:
                        # Проверяем является ли сегмент словарем (новый формат) или объектом (старый формат)
                        if isinstance(seg, dict):
                            # НОВЫЙ ФОРМАТ: сегмент это словарь
                            segment = {
                                "start": seg.get("start", 0) + time_offset,
                                "end": seg.get("end", 0) + time_offset,
                                "text": seg.get("text", "").strip()
                            }
                            logger.info(f"📊 ДИАГНОСТИКА: Сегмент {i} (dict): {segment['start']:.2f}-{segment['end']:.2f}s: '{segment['text'][:50]}...'")
                        else:
                            # СТАРЫЙ ФОРМАТ: сегмент это объект с атрибутами
                            segment = {
                                "start": getattr(seg, 'start', 0) + time_offset,
                                "end": getattr(seg, 'end', 0) + time_offset,
                                "text": getattr(seg, 'text', "").strip()
                            }
                            logger.info(f"📊 ДИАГНОСТИКА: Сегмент {i} (object): {segment['start']:.2f}-{segment['end']:.2f}s: '{segment['text'][:50]}...'")
                        
                        segments.append(segment)
                        
                    except Exception as seg_error:
                        logger.error(f"❌ ДИАГНОСТИКА: Ошибка обработки сегмента {i}: {seg_error}")
                        logger.error(f"❌ ДИАГНОСТИКА: Тип сегмента: {type(seg)}")
                        logger.error(f"❌ ДИАГНОСТИКА: Содержимое сегмента: {seg}")
                        continue
                
                logger.info(f"✅ ДИАГНОСТИКА: Успешно обработано {len(segments)} сегментов")
                
            except Exception as segments_error:
                logger.error(f"❌ ДИАГНОСТИКА: Общая ошибка обработки сегментов: {type(segments_error).__name__}")
                logger.error(f"❌ ДИАГНОСТИКА: Детали ошибки: {segments_error}")
                logger.error(f"❌ ДИАГНОСТИКА: Traceback: {traceback.format_exc()}")
                
                # FALLBACK: создаем простую сегментацию
                logger.info("🔄 ДИАГНОСТИКА: Используем fallback сегментацию...")
                segments = [{
                    "start": time_offset,
                    "end": time_offset + 30,  # Примерная длительность
                    "text": transcript
                }]
        else:
            logger.info("⚠️ ДИАГНОСТИКА: Сегменты не найдены, создаем fallback")
            # Fallback: создаем один сегмент из всего транскрипта
            segments = [{
                "start": time_offset,
                "end": time_offset + 30,  # Примерная длительность
                "text": transcript
            }]
        
        logger.info(f"✅ ДИАГНОСТИКА: Транскрибация завершена. Сегментов: {len(segments)}")
        return transcript, segments
        
    except Exception as e:
        logger.error(f"❌ ДИАГНОСТИКА: Общая ошибка транскрибации: {type(e).__name__}")
        logger.error(f"❌ ДИАГНОСТИКА: Детали ошибки: {e}")
        logger.error(f"❌ ДИАГНОСТИКА: Traceback: {traceback.format_exc()}")
        raise Exception("Failed to transcribe audio")

# НОВАЯ ФУНКЦИЯ: CHUNKING ДЛЯ ДЛИННЫХ АУДИО
def transcribe_audio_with_chunking(audio_path: str) -> Tuple[str, List[dict]]:
    """
    Транскрибация аудио с разбиением на части для длинных файлов
    """
    try:
        # Проверяем размер файла
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"🎵 ДИАГНОСТИКА: Audio extracted: {file_size_mb:.1f}MB")
        logger.info(f"🎵 ДИАГНОСТИКА: Audio file size: {file_size_mb:.1f}MB")
        
        if file_size_mb <= config.MAX_AUDIO_SIZE_MB:
            # Файл небольшой, транскрибируем целиком
            logger.info("🎤 ДИАГНОСТИКА: Файл небольшой, транскрибируем целиком")
            return transcribe_single_audio(audio_path)
        
        # Файл большой, нужно разбить на части
        logger.info(f"📦 ДИАГНОСТИКА: Файл большой ({file_size_mb:.1f}MB > {config.MAX_AUDIO_SIZE_MB}MB), разбиваем на части")
        
        # Получаем длительность аудио
        duration_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", audio_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
        total_duration = float(duration_result.stdout.strip())
        
        logger.info(f"⏱️ ДИАГНОСТИКА: Общая длительность аудио: {total_duration:.1f} секунд")
        
        # Вычисляем количество частей
        chunk_duration = min(config.CHUNK_DURATION, total_duration / 2)  # Не более половины от общей длительности
        num_chunks = max(1, int(total_duration / chunk_duration))
        actual_chunk_duration = total_duration / num_chunks
        
        logger.info(f"📦 ДИАГНОСТИКА: Разбиваем на {num_chunks} частей по {actual_chunk_duration:.1f} секунд")
        
        # Транскрибируем каждую часть
        all_transcript = ""
        all_segments = []
        
        for i in range(num_chunks):
            start_time = i * actual_chunk_duration
            chunk_path = f"audio/chunk_{i}_{uuid.uuid4().hex[:8]}.wav"
            
            logger.info(f"📦 ДИАГНОСТИКА: Обрабатываем часть {i+1}/{num_chunks} ({start_time:.1f}s - {start_time + actual_chunk_duration:.1f}s)")
            
            # Извлекаем часть аудио
            chunk_cmd = [
                "ffmpeg", "-i", audio_path, "-ss", str(start_time),
                "-t", str(actual_chunk_duration), "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1", chunk_path, "-y"
            ]
            
            subprocess.run(chunk_cmd, capture_output=True, timeout=config.FFMPEG_TIMEOUT)
            
            try:
                # Транскрибируем часть
                chunk_transcript, chunk_segments = transcribe_single_audio(chunk_path, start_time)
                
                all_transcript += " " + chunk_transcript
                all_segments.extend(chunk_segments)
                
                logger.info(f"✅ ДИАГНОСТИКА: Часть {i+1} обработана: {len(chunk_transcript)} символов, {len(chunk_segments)} сегментов")
                
            finally:
                # Удаляем временный файл части
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
        
        logger.info(f"✅ ДИАГНОСТИКА: Chunking завершен: {len(all_transcript)} символов, {len(all_segments)} сегментов")
        return all_transcript.strip(), all_segments
        
    except Exception as e:
        logger.error(f"❌ ДИАГНОСТИКА: Ошибка chunking транскрибации: {e}")
        logger.error(f"❌ ДИАГНОСТИКА: Traceback: {traceback.format_exc()}")
        raise Exception("Failed to transcribe audio with chunking")

def analyze_video_task(task_id: str, task_data: dict):
    """Анализ видео в отдельном потоке"""
    try:
        logger.info(f"🎬 ДИАГНОСТИКА: Starting video analysis for {task_id}")
        
        video_path = task_data["video_path"]
        
        # Обновляем статус
        completed_tasks[task_id] = {
            "status": "processing",
            "progress": 10,
            "stage": "extracting_audio"
        }
        
        # Извлечение аудио
        audio_path = f"audio/{task_id}.wav"
        logger.info(f"🎵 ДИАГНОСТИКА: Извлекаем аудио из {video_path}")
        
        extract_cmd = [
            "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", audio_path, "-y"
        ]
        
        result = subprocess.run(extract_cmd, capture_output=True, timeout=config.FFMPEG_TIMEOUT)
        if result.returncode != 0:
            raise Exception(f"Failed to extract audio: {result.stderr.decode()}")
        
        # Обновляем статус
        completed_tasks[task_id] = {
            "status": "processing",
            "progress": 30,
            "stage": "transcribing"
        }
        
        # ИСПРАВЛЕННАЯ ТРАНСКРИБАЦИЯ С CHUNKING
        transcript, segments = transcribe_audio_with_chunking(audio_path)
        
        # Обновляем статус
        completed_tasks[task_id] = {
            "status": "processing",
            "progress": 70,
            "stage": "analyzing"
        }
        
        # Анализ с ChatGPT
        analysis_prompt = f"""
        Analyze this video transcript and find the 3 most viral-worthy moments for short-form content.
        
        Transcript: {transcript}
        
        For each moment, provide:
        1. A catchy title (max 50 characters)
        2. Start and end timestamps
        3. The exact quote
        4. Viral potential score (1-100)
        5. Why it would go viral
        
        Focus on:
        - Controversial or surprising statements
        - Emotional moments
        - Quotable one-liners
        - Strong opinions or declarations
        
        Return as JSON array with this structure:
        [
          {{
            "title": "Moment Title",
            "start_time": 0,
            "end_time": 10,
            "quote": "Exact quote from transcript",
            "viral_score": 85,
            "reason": "Why this would go viral"
          }}
        ]
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": analysis_prompt}],
            timeout=config.OPENAI_TIMEOUT
        )
        
        # Парсим ответ
        analysis_text = response.choices[0].message.content
        
        # Извлекаем JSON из ответа
        import re
        json_match = re.search(r'\[.*\]', analysis_text, re.DOTALL)
        if json_match:
            highlights = json.loads(json_match.group())
        else:
            highlights = []
        
        # Финальный результат
        result = {
            "status": "completed",
            "progress": 100,
            "transcript": transcript,
            "segments": segments,
            "highlights": highlights,
            "video_path": video_path,
            "audio_path": audio_path,
            "analysis_time": time.time()
        }
        
        logger.info(f"✅ ДИАГНОСТИКА: Analysis completed for {task_id}")
        return result
        
    except Exception as e:
        logger.error(f"❌ ДИАГНОСТИКА: Analysis failed for task {task_id}: {e}")
        logger.error(f"❌ ДИАГНОСТИКА: Traceback: {traceback.format_exc()}")
        raise Exception("Failed to transcribe audio")

# ОБНОВЛЕННАЯ ФУНКЦИЯ ГЕНЕРАЦИИ КЛИПОВ С СУБТИТРАМИ
def generate_clips_task(generation_task_id: str):
    """Генерация клипов с субтитрами в отдельном потоке"""
    try:
        task_info = generation_queue[generation_task_id]
        highlights = task_info["highlights"]
        video_path = task_info["video_path"]
        
        logger.info(f"🎬 СУБТИТРЫ: Начинаем генерацию {len(highlights)} клипов с субтитрами")
        
        clips = []
        
        for i, highlight in enumerate(highlights):
            try:
                # Обновляем прогресс
                progress = int((i / len(highlights)) * 100)
                generation_queue[generation_task_id]["progress"] = progress
                generation_queue[generation_task_id]["log"].append(f"Генерируем клип {i+1}/{len(highlights)}: {highlight['title']}")
                
                # Параметры клипа
                start_time = highlight["start_time"]
                end_time = highlight["end_time"]
                duration = end_time - start_time
                clip_id = str(uuid.uuid4())
                clip_path = f"clips/{clip_id}.mp4"
                
                # Получаем текст для субтитров
                subtitle_text = highlight.get("quote", "").strip()
                
                logger.info(f"🎬 СУБТИТРЫ: Генерируем клип {i+1}: '{highlight['title']}'")
                logger.info(f"📝 СУБТИТРЫ: Текст субтитров: '{subtitle_text}'")
                
                # Создаем фильтр субтитров
                subtitle_filter = create_subtitle_filter(subtitle_text)
                
                # Полный видео фильтр с субтитрами
                video_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}"
                
                # FFmpeg команда с субтитрами
                cmd = [
                    "ffmpeg", "-i", video_path,
                    "-ss", str(start_time), "-t", str(duration),
                    "-vf", video_filter,
                    "-c:v", "libx264", "-preset", config.VIDEO_PRESET, "-crf", config.VIDEO_CRF,
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    clip_path, "-y"
                ]
                
                logger.info(f"🎬 СУБТИТРЫ: Выполняем FFmpeg команду...")
                logger.info(f"🔧 СУБТИТРЫ: Фильтр: {video_filter}")
                
                result = subprocess.run(cmd, capture_output=True, timeout=config.FFMPEG_TIMEOUT)
                
                if result.returncode != 0:
                    error_msg = result.stderr.decode()
                    logger.error(f"❌ СУБТИТРЫ: FFmpeg ошибка для клипа {i+1}: {error_msg}")
                    generation_queue[generation_task_id]["log"].append(f"Ошибка клипа {i+1}: {error_msg}")
                    continue
                
                # Проверяем что файл создан
                if os.path.exists(clip_path) and os.path.getsize(clip_path) > 1000:
                    clip_info = {
                        "id": clip_id,
                        "title": highlight["title"],
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": duration,
                        "viral_score": highlight.get("viral_score", 0),
                        "quote": subtitle_text,
                        "file_path": clip_path,
                        "file_size": os.path.getsize(clip_path)
                    }
                    clips.append(clip_info)
                    
                    logger.info(f"✅ СУБТИТРЫ: Клип {i+1} создан: {clip_path} ({clip_info['file_size']} байт)")
                    generation_queue[generation_task_id]["log"].append(f"✅ Клип {i+1} готов: {highlight['title']}")
                else:
                    logger.error(f"❌ СУБТИТРЫ: Клип {i+1} не создан или слишком мал")
                    generation_queue[generation_task_id]["log"].append(f"❌ Клип {i+1} не создан")
                
            except Exception as e:
                logger.error(f"❌ СУБТИТРЫ: Ошибка генерации клипа {i+1}: {e}")
                generation_queue[generation_task_id]["log"].append(f"❌ Ошибка клипа {i+1}: {str(e)}")
                continue
        
        # Финализируем результат
        generation_queue[generation_task_id].update({
            "status": "completed",
            "progress": 100,
            "clips": clips,
            "completed_at": time.time()
        })
        
        logger.info(f"🎉 СУБТИТРЫ: Генерация завершена! Создано {len(clips)} клипов из {len(highlights)}")
        
    except Exception as e:
        logger.error(f"❌ СУБТИТРЫ: Общая ошибка генерации: {e}")
        logger.error(f"❌ СУБТИТРЫ: Traceback: {traceback.format_exc()}")
        generation_queue[generation_task_id].update({
            "status": "failed",
            "error": str(e),
            "progress": 0
        })

# API Endpoints
@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    memory_percent = get_memory_usage()
    disk_percent = get_disk_usage()
    cpu_percent = get_cpu_usage()
    
    # Принудительная очистка памяти если нужно
    if memory_percent > config.MEMORY_LIMIT_PERCENT:
        gc.collect()
        logger.info(f"🧠 Memory cleanup: {memory_percent}% used")
    
    return {
        "status": "healthy",
        "version": "15.4-subtitles-fixed",
        "memory_usage": f"{memory_percent}%",
        "disk_usage": f"{disk_percent}%", 
        "cpu_usage": f"{cpu_percent}%",
        "active_tasks": len(active_tasks),
        "queue_size": len(task_queue),
        "dependencies": {
            "ffmpeg": True,
            "openai": client is not None
        }
    }

@app.post("/api/videos/analyze")
async def analyze_video(file: UploadFile = File(...)):
    """Анализ видео с извлечением аудио и транскрибацией"""
    try:
        logger.info(f"📤 ДИАГНОСТИКА: Получен запрос на анализ видео: {file.filename}")
        
        # Проверка размера файла
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        logger.info(f"📁 ДИАГНОСТИКА: Размер загруженного файла: {file_size} байт ({file_size/1024/1024:.2f} MB)")
        
        if file_size > config.MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large. Max size: {config.MAX_VIDEO_SIZE_MB}MB")
        
        # Сохранение файла
        task_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        video_path = f"uploads/{task_id}_{file.filename}"
        
        logger.info(f"💾 ДИАГНОСТИКА: Сохраняем файл как: {video_path}")
        
        with open(video_path, "wb") as f:
            f.write(content)
        
        # Проверка длительности видео
        duration_cmd = [
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", video_path
        ]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
        duration = float(duration_result.stdout.strip())
        
        logger.info(f"📹 ДИАГНОСТИКА: Длительность видео: {duration} секунд")
        
        if duration > config.MAX_VIDEO_DURATION:
            os.remove(video_path)
            raise HTTPException(status_code=413, detail=f"Video too long. Max duration: {config.MAX_VIDEO_DURATION/60} minutes")
        
        # Добавление в очередь
        task_data = {
            "video_path": video_path,
            "filename": file.filename,
            "file_size": file_size,
            "duration": duration,
            "created_at": time.time()
        }
        
        add_to_queue(task_id, task_data)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Video analysis started",
            "estimated_time": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{task_id}/status")
async def get_analysis_status(task_id: str):
    """Получение статуса анализа видео"""
    
    # Проверяем активные задачи
    if task_id in active_tasks:
        return {
            "task_id": task_id,
            "status": "processing",
            "progress": 50,
            "stage": "analyzing"
        }
    
    # Проверяем завершенные задачи
    if task_id in completed_tasks:
        return completed_tasks[task_id]
    
    # Проверяем очередь
    for queued_task_id, _ in task_queue:
        if queued_task_id == task_id:
            position = list(task_queue).index((task_id, _))
            return {
                "task_id": task_id,
                "status": "queued",
                "progress": 0,
                "queue_position": position
            }
    
    raise HTTPException(status_code=404, detail="Task not found")

# ENDPOINTS ДЛЯ ГЕНЕРАЦИИ КЛИПОВ С СУБТИТРАМИ
@app.post("/api/clips/generate")
async def generate_clips(task_id: str):
    """Генерация клипов с субтитрами из проанализированного видео"""
    try:
        # Проверяем что задача существует и завершена
        if task_id not in completed_tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task_data = completed_tasks[task_id]
        if task_data["status"] != "completed":
            raise HTTPException(status_code=400, detail="Task not completed yet")
        
        highlights = task_data.get("highlights", [])
        if not highlights:
            raise HTTPException(status_code=400, detail="No highlights found for this task")
        
        # Создаем задачу генерации
        generation_task_id = str(uuid.uuid4())
        generation_queue[generation_task_id] = {
            "status": "queued",
            "progress": 0,
            "clips": [],
            "log": [],
            "task_id": task_id,
            "highlights": highlights,
            "video_path": task_data.get("video_path"),
            "created_at": time.time()
        }
        
        # Запускаем генерацию в отдельном потоке
        threading.Thread(target=generate_clips_task, args=(generation_task_id,)).start()
        
        logger.info(f"🎬 СУБТИТРЫ: Запущена генерация клипов для задачи {task_id}")
        
        return {
            "generation_task_id": generation_task_id,
            "status": "queued",
            "highlights_count": len(highlights),
            "message": "Clip generation with subtitles started"
        }
        
    except Exception as e:
        logger.error(f"Error starting clips generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/generation/{generation_task_id}/status")
async def get_generation_status(generation_task_id: str):
    """Получение статуса генерации клипов"""
    if generation_task_id not in generation_queue:
        raise HTTPException(status_code=404, detail="Generation task not found")
    
    return generation_queue[generation_task_id]

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивание сгенерированного клипа"""
    clip_path = f"clips/{clip_id}.mp4"
    
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

@app.get("/api/videos/{task_id}/clips")
async def get_task_clips(task_id: str):
    """Получение всех клипов для задачи"""
    # Ищем все задачи генерации для данной задачи
    task_clips = []
    
    for gen_id, gen_data in generation_queue.items():
        if gen_data.get("task_id") == task_id and gen_data.get("status") == "completed":
            task_clips.extend(gen_data.get("clips", []))
    
    return {
        "task_id": task_id,
        "clips": task_clips,
        "total_clips": len(task_clips)
    }

# Фоновая задача очистки
async def cleanup_task():
    """Фоновая задача для очистки файлов"""
    while True:
        try:
            cleanup_old_files()
            await asyncio.sleep(config.CLEANUP_INTERVAL)
        except Exception as e:
            logger.error(f"Cleanup task error: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Запуск фоновых задач"""
    asyncio.create_task(cleanup_task())
    logger.info("🚀 AgentFlow AI Clips v15.4 with Subtitles started!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

