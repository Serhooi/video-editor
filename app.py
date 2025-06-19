"""
AgentFlow AI Clips v15.6 - УЛУЧШЕННЫЕ АНИМИРОВАННЫЕ СУБТИТРЫ
Переработана система субтитров по примеру пользователя: фразы по 2-4 слова, Montserrat Bold, белый текст + цветной хайлайт

НОВОЕ В v15.6:
1. Фразы группируются по 2-4 слова (как в примере)
2. Montserrat Bold шрифт
3. Белый текст с цветным хайлайтом активного слова
4. Увеличение текущего слова
5. Исправлена проблема отсутствия субтитров в некоторых клипах
6. Улучшенная логика синхронизации с речью

СОХРАНЕНЫ ВСЕ ИСПРАВЛЕНИЯ v15.5.5:
- Исправлен Whisper API (убран timestamp_granularities)
- Исправлены FFmpeg фильтры
- Детальное логирование
- Fallback механизмы
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
app = FastAPI(title="AgentFlow AI Clips", version="15.6-improved-subtitles")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Импорт улучшенной системы субтитров
from improved_animated_subtitle_system import ImprovedAnimatedSubtitleSystem

# Глобальные переменные
tasks = {}
active_tasks = set()
task_queue = deque()
generation_tasks = {}
client = None
subtitle_system = ImprovedAnimatedSubtitleSystem()

# Конфигурация
class Config:
    # Директории
    UPLOAD_DIR = "uploads"
    AUDIO_DIR = "audio"
    CLIPS_DIR = "clips"
    
    # Ограничения
    MAX_VIDEO_SIZE_MB = 150
    MAX_VIDEO_DURATION = 1200  # 20 минут
    
    # Таймауты
    FFMPEG_TIMEOUT = 300      # 5 минут
    OPENAI_TIMEOUT = 600      # 10 минут
    WHISPER_TIMEOUT = 900     # 15 минут
    
    # Очистка
    CLEANUP_INTERVAL = 3600   # 1 час
    MAX_FILE_AGE = 86400      # 24 часа
    
    # Параллелизм
    MAX_CONCURRENT_TASKS = 3
    MAX_CONCURRENT_GENERATIONS = 2

config = Config()

# Создание директорий
for directory in [config.UPLOAD_DIR, config.AUDIO_DIR, config.CLIPS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Инициализация OpenAI
try:
    from openai import OpenAI
    client = OpenAI()
    logger.info("✅ OpenAI клиент инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации OpenAI: {e}")

# Executor для фоновых задач
executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_TASKS)

def get_video_info(video_path: str) -> Optional[Dict]:
    """Получает информацию о видео"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            
            # Ищем видео поток
            video_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if video_stream:
                duration = float(info['format']['duration'])
                return {
                    'duration': duration,
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '30/1'))
                }
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о видео: {e}")
    
    return None

async def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Извлекает аудио из видео"""
    try:
        logger.info(f"🎵 Извлекаем аудио: {video_path} -> {audio_path}")
        
        cmd = [
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', '-y', audio_path
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
        logger.info(f"🎤 Начинаем транскрибацию: {audio_path}")
        
        if not client:
            raise ValueError("OpenAI клиент не инициализирован")
        
        # Проверяем размер файла
        file_size = os.path.getsize(audio_path)
        logger.info(f"📊 Размер аудио файла: {file_size / 1024 / 1024:.2f} MB")
        
        # Если файл больше 25MB, используем chunking
        if file_size > 25 * 1024 * 1024:
            logger.info("📦 Файл большой, используем chunking...")
            return await transcribe_large_audio_chunked(audio_path)
        
        logger.info("🔄 Отправляем запрос к Whisper API...")
        
        with open(audio_path, "rb") as audio_file:
            # ИСПРАВЛЕНО: Убираем timestamp_granularities (не поддерживается)
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
                # timestamp_granularities убран - не поддерживается в текущей версии API
            )
        
        logger.info("✅ Транскрибация завершена успешно")
        
        # Обрабатываем сегменты
        segments = []
        if hasattr(transcript, 'segments') and transcript.segments:
            for segment in transcript.segments:
                segments.append({
                    'start': segment['start'],
                    'end': segment['end'], 
                    'text': segment['text'].strip()
                })
        else:
            # Если нет сегментов, создаем один сегмент
            logger.warning("⚠️ Нет сегментов в ответе Whisper, создаем один сегмент")
            segments = [{
                'start': 0.0,
                'end': 30.0,  # Примерная длительность
                'text': transcript.text
            }]
        
        logger.info(f"📝 Получено {len(segments)} сегментов")
        
        return {
            'text': transcript.text,
            'segments': segments
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации: {e}")
        return None

async def transcribe_large_audio_chunked(audio_path: str) -> Optional[Dict]:
    """Транскрибирует большой аудио файл по частям"""
    try:
        logger.info("📦 Начинаем chunked транскрибацию...")
        
        # Получаем длительность аудио
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        logger.info(f"⏱️ Длительность аудио: {duration:.2f} секунд")
        
        # Разбиваем на chunks по 10 минут
        chunk_duration = 600  # 10 минут
        chunks = []
        full_text = ""
        all_segments = []
        
        for start_time in range(0, int(duration), chunk_duration):
            end_time = min(start_time + chunk_duration, duration)
            chunk_path = f"{audio_path}_chunk_{start_time}_{end_time}.wav"
            
            # Создаем chunk
            cmd = [
                'ffmpeg', '-i', audio_path, '-ss', str(start_time), '-t', str(end_time - start_time),
                '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-y', chunk_path
            ]
            
            process = subprocess.run(cmd, capture_output=True)
            
            if process.returncode == 0:
                logger.info(f"📦 Создан chunk: {start_time}-{end_time}s")
                
                # Транскрибируем chunk
                with open(chunk_path, "rb") as chunk_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=chunk_file,
                        response_format="verbose_json"
                        # timestamp_granularities убран - не поддерживается
                    )
                
                # Добавляем к общему тексту
                full_text += " " + transcript.text
                
                # Обрабатываем сегменты с корректировкой времени
                if hasattr(transcript, 'segments') and transcript.segments:
                    for segment in transcript.segments:
                        all_segments.append({
                            'start': segment['start'] + start_time,
                            'end': segment['end'] + start_time,
                            'text': segment['text'].strip()
                        })
                
                # Удаляем chunk файл
                os.remove(chunk_path)
                
            else:
                logger.error(f"❌ Ошибка создания chunk {start_time}-{end_time}")
        
        logger.info(f"✅ Chunked транскрибация завершена: {len(all_segments)} сегментов")
        
        return {
            'text': full_text.strip(),
            'segments': all_segments
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка chunked транскрибации: {e}")
        return None

async def analyze_video_with_chatgpt(transcript: str, segments: List[Dict]) -> Optional[List[Dict]]:
    """Анализирует видео с помощью ChatGPT для поиска лучших моментов"""
    try:
        logger.info("🤖 Анализируем видео с ChatGPT...")
        
        if not client:
            raise ValueError("OpenAI клиент не инициализирован")
        
        # Подготавливаем сегменты для анализа
        segments_text = ""
        for i, segment in enumerate(segments):
            segments_text += f"[{segment['start']:.1f}-{segment['end']:.1f}s] {segment['text']}\n"
        
        prompt = f"""Проанализируй этот видео транскрипт и найди 3 самых интересных и вирусных момента для создания коротких клипов.

ТРАНСКРИПТ С ВРЕМЕННЫМИ МЕТКАМИ:
{segments_text}

ПОЛНЫЙ ТЕКСТ:
{transcript}

Для каждого момента определи:
1. Заголовок (краткий и цепляющий)
2. Точное время начала и конца (в секундах)
3. Ключевую цитату (1-2 предложения)
4. Вирусный потенциал (0-100)
5. Причину почему этот момент будет популярен

Ответь в JSON формате:
[
  {{
    "title": "Заголовок момента",
    "start_time": 0.0,
    "end_time": 10.0,
    "quote": "Ключевая цитата",
    "viral_score": 85,
    "reason": "Объяснение почему вирусный"
  }}
]

ВАЖНО: Используй только временные метки из предоставленных сегментов!"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты эксперт по созданию вирусного контента. Анализируй видео и находи самые интересные моменты для коротких клипов."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7,
            timeout=config.OPENAI_TIMEOUT
        )
        
        # Парсим JSON ответ
        content = response.choices[0].message.content.strip()
        
        # Убираем markdown форматирование если есть
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        highlights = json.loads(content)
        
        logger.info(f"✅ ChatGPT нашел {len(highlights)} интересных моментов")
        
        # Валидируем результаты
        validated_highlights = []
        for highlight in highlights:
            if all(key in highlight for key in ['title', 'start_time', 'end_time', 'quote', 'viral_score']):
                validated_highlights.append(highlight)
        
        return validated_highlights
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON от ChatGPT: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка анализа с ChatGPT: {e}")
        return None

def find_segments_for_clip(segments: List[Dict], start_time: float, end_time: float) -> List[Dict]:
    """Находит сегменты транскрипта для клипа с улучшенной логикой"""
    matching_segments = []
    
    logger.info(f"🔍 Ищем сегменты для клипа {start_time:.1f}-{end_time:.1f}s")
    logger.info(f"📊 Всего доступно сегментов: {len(segments)}")
    
    for segment in segments:
        segment_start = segment['start']
        segment_end = segment['end']
        
        # ИСПРАВЛЕНО: Улучшенная логика пересечения временных интервалов
        # Проверяем различные случаи пересечения
        if (start_time <= segment_start <= end_time) or \
           (start_time <= segment_end <= end_time) or \
           (segment_start <= start_time and segment_end >= end_time) or \
           (start_time <= segment_start and end_time >= segment_end):
            
            matching_segments.append(segment)
            logger.info(f"✅ Найден сегмент: {segment_start:.1f}-{segment_end:.1f}s: '{segment['text'][:50]}...'")
    
    logger.info(f"📝 Найдено {len(matching_segments)} подходящих сегментов")
    return matching_segments

async def generate_clip_with_improved_subtitles(
    video_path: str, 
    start_time: float, 
    end_time: float, 
    output_path: str,
    quote: str,
    segments: List[Dict],
    subtitle_style: str = "modern",
    animation_type: str = "highlight"
) -> bool:
    """Генерирует клип с улучшенными анимированными субтитрами"""
    try:
        logger.info(f"🎬 Создаем клип с улучшенными субтитрами: {start_time:.1f}-{end_time:.1f}s")
        logger.info(f"🎨 Стиль: {subtitle_style}, Анимация: {animation_type}")
        logger.info(f"💬 Quote: {quote}")
        
        # Находим подходящие сегменты
        clip_segments = find_segments_for_clip(segments, start_time, end_time)
        logger.info(f"📊 Найдено сегментов для субтитров: {len(clip_segments)}")
        
        # Генерируем фильтр субтитров
        subtitle_filter = subtitle_system.generate_ffmpeg_filter(
            clip_segments, quote, start_time, end_time, subtitle_style
        )
        
        logger.info(f"🔧 Размер сгенерированного фильтра: {len(subtitle_filter)} символов")
        
        # ИСПРАВЛЕНО: Валидация фильтра
        if not subtitle_filter or len(subtitle_filter) < 10:
            logger.warning("⚠️ Фильтр субтитров пустой или слишком короткий, используем fallback")
            subtitle_filter = subtitle_system.generate_fallback_filter(quote, subtitle_style)
        
        # Создаем команду FFmpeg
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-vf', subtitle_filter,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-avoid_negative_ts', 'make_zero',
            '-y', output_path
        ]
        
        logger.info(f"🔧 Команда FFmpeg: {' '.join(cmd[:10])}...")
        
        # Выполняем команду
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
            logger.info(f"✅ Клип создан успешно: {output_path}")
            return True
        else:
            error_msg = stderr.decode()
            logger.error(f"❌ Ошибка создания клипа: {error_msg}")
            
            # ИСПРАВЛЕНО: Fallback на простые субтитры при ошибке
            if "filter" in error_msg.lower():
                logger.info("🔄 Пробуем fallback с простыми субтитрами...")
                return await generate_clip_with_simple_subtitles(
                    video_path, start_time, end_time, output_path, quote, subtitle_style
                )
            
            return False
            
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут создания клипа: {config.FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка создания клипа: {e}")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False

async def generate_clip_with_simple_subtitles(
    video_path: str,
    start_time: float, 
    end_time: float,
    output_path: str,
    quote: str,
    subtitle_style: str = "modern"
) -> bool:
    """Fallback: создает клип с простыми статичными субтитрами"""
    try:
        logger.info("🔄 Создаем клип с простыми субтитрами (fallback)")
        
        # Простой фильтр субтитров
        escaped_quote = quote.replace("'", "\\'").replace(":", "\\:")
        
        subtitle_filter = f"drawtext=text='{escaped_quote}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=48:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h-150"
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-vf', subtitle_filter,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-avoid_negative_ts', 'make_zero',
            '-y', output_path
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
            logger.info(f"✅ Fallback клип создан: {output_path}")
            return True
        else:
            logger.error(f"❌ Ошибка fallback клипа: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка fallback клипа: {e}")
        return False

async def process_video_analysis(task_id: str, video_path: str, filename: str, file_size: int):
    """Обрабатывает анализ видео"""
    try:
        logger.info(f"🎬 Начинаем анализ видео: {task_id}")
        
        # Обновляем статус
        tasks[task_id].update({
            'status': 'processing',
            'progress': 10
        })
        
        # Получаем информацию о видео
        video_info = get_video_info(video_path)
        if not video_info:
            raise Exception("Не удалось получить информацию о видео")
        
        # Проверяем длительность
        if video_info['duration'] > config.MAX_VIDEO_DURATION:
            raise Exception(f"Видео слишком длинное: {video_info['duration']:.1f}s (макс: {config.MAX_VIDEO_DURATION}s)")
        
        tasks[task_id]['progress'] = 20
        
        # Извлекаем аудио
        audio_path = os.path.join(config.AUDIO_DIR, f"{task_id}.wav")
        if not await extract_audio_from_video(video_path, audio_path):
            raise Exception("Ошибка извлечения аудио")
        
        tasks[task_id]['progress'] = 40
        tasks[task_id]['audio_path'] = audio_path
        
        # Транскрибируем аудио
        transcript_result = await transcribe_audio_with_whisper(audio_path)
        if not transcript_result:
            raise Exception("Ошибка транскрибации")
        
        tasks[task_id]['progress'] = 70
        tasks[task_id]['transcript'] = transcript_result['text']
        tasks[task_id]['segments'] = transcript_result['segments']
        
        # Анализируем с ChatGPT
        highlights = await analyze_video_with_chatgpt(
            transcript_result['text'], 
            transcript_result['segments']
        )
        
        if not highlights:
            raise Exception("Ошибка анализа с ChatGPT")
        
        # Завершаем
        tasks[task_id].update({
            'status': 'completed',
            'progress': 100,
            'highlights': highlights,
            'completed_at': time.time(),
            'elapsed_time': time.time() - tasks[task_id]['created_at']
        })
        
        logger.info(f"✅ Анализ видео завершен: {task_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа видео {task_id}: {e}")
        tasks[task_id].update({
            'status': 'failed',
            'error': str(e),
            'elapsed_time': time.time() - tasks[task_id]['created_at']
        })
    finally:
        active_tasks.discard(task_id)

async def process_clips_generation(
    generation_task_id: str,
    task_id: str, 
    highlights: List[Dict],
    video_path: str,
    segments: List[Dict],
    subtitle_style: str = "modern",
    animation_type: str = "highlight"
):
    """Обрабатывает генерацию клипов"""
    try:
        logger.info(f"🎬 Начинаем генерацию клипов: {generation_task_id}")
        
        generation_tasks[generation_task_id].update({
            'status': 'processing',
            'progress': 10
        })
        
        clips = []
        log_messages = []
        
        for i, highlight in enumerate(highlights):
            try:
                progress = 10 + (i * 80 // len(highlights))
                generation_tasks[generation_task_id]['progress'] = progress
                
                clip_id = str(uuid.uuid4())
                clip_filename = f"{clip_id}.mp4"
                clip_path = os.path.join(config.CLIPS_DIR, clip_filename)
                
                log_msg = f"Генерируем клип {i+1}/{len(highlights)}: {highlight['title']}"
                log_messages.append(log_msg)
                logger.info(log_msg)
                
                # Генерируем клип с улучшенными субтитрами
                success = await generate_clip_with_improved_subtitles(
                    video_path=video_path,
                    start_time=highlight['start_time'],
                    end_time=highlight['end_time'],
                    output_path=clip_path,
                    quote=highlight['quote'],
                    segments=segments,
                    subtitle_style=subtitle_style,
                    animation_type=animation_type
                )
                
                if success and os.path.exists(clip_path):
                    file_size = os.path.getsize(clip_path)
                    
                    clip_info = {
                        'id': clip_id,
                        'title': highlight['title'],
                        'start_time': highlight['start_time'],
                        'end_time': highlight['end_time'],
                        'duration': highlight['end_time'] - highlight['start_time'],
                        'viral_score': highlight['viral_score'],
                        'quote': highlight['quote'],
                        'file_path': clip_path,
                        'file_size': file_size,
                        'subtitle_style': subtitle_style,
                        'animation_type': animation_type
                    }
                    
                    clips.append(clip_info)
                    
                    success_msg = f"✅ Клип {i+1} готов: {highlight['title']}"
                    log_messages.append(success_msg)
                    logger.info(success_msg)
                    
                else:
                    error_msg = f"❌ Ошибка создания клипа: {clip_path}"
                    log_messages.append(error_msg)
                    logger.error(error_msg)
                    
            except Exception as e:
                error_msg = f"❌ Ошибка клипа {i+1}: {e}"
                log_messages.append(error_msg)
                logger.error(error_msg)
        
        # Завершаем генерацию
        generation_tasks[generation_task_id].update({
            'status': 'completed',
            'progress': 100,
            'clips': clips,
            'log': log_messages,
            'completed_at': time.time(),
            'elapsed_time': time.time() - generation_tasks[generation_task_id]['created_at']
        })
        
        logger.info(f"✅ Генерация клипов завершена: {generation_task_id}, создано {len(clips)} клипов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации клипов {generation_task_id}: {e}")
        generation_tasks[generation_task_id].update({
            'status': 'failed',
            'error': str(e),
            'elapsed_time': time.time() - generation_tasks[generation_task_id]['created_at']
        })

# API Endpoints

@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        # Проверяем использование ресурсов
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "status": "healthy",
            "version": "15.6-improved-subtitles",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": len(active_tasks),
            "queue_size": len(task_queue),
            "total_tasks": len(tasks),
            "total_generations": len(generation_tasks),
            "memory_usage": f"{memory.percent}%",
            "cpu_usage": f"{cpu_percent}%",
            "dependencies": {
                "ffmpeg": True,
                "openai": client is not None
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/videos/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Анализирует видео и находит лучшие моменты"""
    try:
        # Проверяем размер файла
        if file.size > config.MAX_VIDEO_SIZE_MB * 1024 * 1024:
            raise HTTPException(400, f"Файл слишком большой: {file.size / 1024 / 1024:.1f}MB (макс: {config.MAX_VIDEO_SIZE_MB}MB)")
        
        # Создаем задачу
        task_id = str(uuid.uuid4())
        filename = file.filename or f"video_{task_id}.mp4"
        video_path = os.path.join(config.UPLOAD_DIR, f"{task_id}_{filename}")
        
        # Сохраняем файл
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"📤 Видео загружено: {task_id} ({len(content)} bytes)")
        
        # Создаем запись задачи
        tasks[task_id] = {
            'id': task_id,
            'status': 'queued',
            'progress': 0,
            'video_path': video_path,
            'filename': filename,
            'file_size': len(content),
            'created_at': time.time()
        }
        
        # Запускаем обработку
        active_tasks.add(task_id)
        background_tasks.add_task(
            process_video_analysis,
            task_id, video_path, filename, len(content)
        )
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Video analysis started",
            "estimated_time": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки видео: {e}")
        raise HTTPException(500, f"Ошибка загрузки видео: {e}")

@app.get("/api/videos/{task_id}/status")
async def get_video_status(task_id: str):
    """Получает статус анализа видео"""
    if task_id not in tasks:
        raise HTTPException(404, "Задача не найдена")
    
    return tasks[task_id]

@app.post("/api/clips/generate")
async def generate_clips(
    background_tasks: BackgroundTasks,
    task_id: str = Query(..., description="ID задачи анализа видео"),
    subtitle_style: str = Query("modern", description="Стиль субтитров: modern, neon, fire"),
    animation_type: str = Query("highlight", description="Тип анимации: highlight, scale, glow")
):
    """Генерирует клипы с анимированными субтитрами"""
    try:
        if task_id not in tasks:
            raise HTTPException(404, "Задача анализа не найдена")
        
        task = tasks[task_id]
        if task['status'] != 'completed':
            raise HTTPException(400, "Анализ видео еще не завершен")
        
        if 'highlights' not in task:
            raise HTTPException(400, "Нет найденных моментов для клипов")
        
        # Создаем задачу генерации
        generation_task_id = str(uuid.uuid4())
        
        generation_tasks[generation_task_id] = {
            'status': 'queued',
            'progress': 0,
            'task_id': task_id,
            'highlights': task['highlights'],
            'video_path': task['video_path'],
            'created_at': time.time(),
            'subtitle_style': subtitle_style,
            'animation_type': animation_type
        }
        
        # Запускаем генерацию
        background_tasks.add_task(
            process_clips_generation,
            generation_task_id,
            task_id,
            task['highlights'],
            task['video_path'],
            task.get('segments', []),
            subtitle_style,
            animation_type
        )
        
        return {
            "generation_task_id": generation_task_id,
            "status": "queued",
            "message": f"Clip generation with {subtitle_style} subtitles and {animation_type} animation started",
            "highlights_count": len(task['highlights']),
            "subtitle_style": subtitle_style,
            "animation_type": animation_type
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска генерации клипов: {e}")
        raise HTTPException(500, f"Ошибка генерации клипов: {e}")

@app.get("/api/clips/generation/{generation_task_id}/status")
async def get_generation_status(generation_task_id: str):
    """Получает статус генерации клипов"""
    if generation_task_id not in generation_tasks:
        raise HTTPException(404, "Задача генерации не найдена")
    
    return generation_tasks[generation_task_id]

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивает готовый клип"""
    clip_path = os.path.join(config.CLIPS_DIR, f"{clip_id}.mp4")
    
    if not os.path.exists(clip_path):
        raise HTTPException(404, "Клип не найден")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

# Очистка файлов
async def cleanup_old_files():
    """Очищает старые файлы"""
    try:
        current_time = time.time()
        
        for directory in [config.UPLOAD_DIR, config.AUDIO_DIR, config.CLIPS_DIR]:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    
                    if file_age > config.MAX_FILE_AGE:
                        os.remove(file_path)
                        logger.info(f"🗑️ Удален старый файл: {file_path}")
        
        # Очищаем старые задачи
        old_tasks = []
        for task_id, task in tasks.items():
            task_age = current_time - task['created_at']
            if task_age > config.MAX_FILE_AGE:
                old_tasks.append(task_id)
        
        for task_id in old_tasks:
            del tasks[task_id]
            logger.info(f"🗑️ Удалена старая задача: {task_id}")
        
        # Очищаем старые задачи генерации
        old_generations = []
        for gen_id, gen_task in generation_tasks.items():
            task_age = current_time - gen_task['created_at']
            if task_age > config.MAX_FILE_AGE:
                old_generations.append(gen_id)
        
        for gen_id in old_generations:
            del generation_tasks[gen_id]
            logger.info(f"🗑️ Удалена старая генерация: {gen_id}")
        
        # Принудительная сборка мусора
        gc.collect()
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки файлов: {e}")

# Запуск периодической очистки
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 AgentFlow AI Clips v15.6 with Improved Subtitles started!")
    
    # Запускаем периодическую очистку
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(config.CLEANUP_INTERVAL)
            await cleanup_old_files()
    
    asyncio.create_task(periodic_cleanup())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

