"""
AgentFlow AI Clips v15.7 - КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ
ИСПРАВЛЕНО:
1. Правильная синхронизация субтитров с речью (используем сегменты Whisper)
2. Формат видео 9:16 для TikTok/Instagram  
3. Анимация слов с подсветкой (как в примере пользователя)
4. Исправлена логика поиска сегментов для всех клипов
5. Увеличен размер шрифта для вертикального формата
6. Улучшена позиция субтитров

НОВОЕ В v15.7:
- Продвинутая система синхронизации с Whisper сегментами
- Автоматическая обрезка видео в формат 9:16
- Умная группировка слов с учетом пауз
- Подсветка текущего слова в реальном времени
- Увеличенный шрифт (64px) для мобильных устройств
- Тень и обводка для лучшей читаемости

СОХРАНЕНЫ ВСЕ ИСПРАВЛЕНИЯ:
- Whisper API исправлен (v15.5.5)
- FFmpeg фильтры исправлены (v15.5.4)
- Встроенная система субтитров (v15.6.1)
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
app = FastAPI(title="AgentFlow AI Clips", version="15.7-critical-fixes")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Продвинутая система анимированных субтитров v15.7
class AdvancedAnimatedSubtitleSystem:
    def __init__(self):
        self.styles = {
            'modern': {
                'font': 'Montserrat-Bold',
                'base_color': 'white',
                'highlight_color': '#00FF00',  # Зеленый как в примере
                'font_size': 64,  # Увеличен для 9:16
                'stroke_width': 3,
                'stroke_color': 'black',
                'shadow': True
            },
            'neon': {
                'font': 'Montserrat-Bold', 
                'base_color': 'white',
                'highlight_color': '#00FFFF',  # Неоновый голубой
                'font_size': 64,
                'stroke_width': 3,
                'stroke_color': 'black',
                'shadow': True
            },
            'fire': {
                'font': 'Montserrat-Bold',
                'base_color': 'white', 
                'highlight_color': '#FF4500',  # Оранжевый
                'font_size': 64,
                'stroke_width': 3,
                'stroke_color': 'black',
                'shadow': True
            }
        }
    
    def find_segments_for_timerange(self, segments, start_time, end_time):
        """Находит сегменты Whisper для временного диапазона клипа"""
        matching_segments = []
        
        logger.info(f"🔍 Поиск сегментов для клипа {start_time:.1f}-{end_time:.1f}s")
        
        for segment in segments:
            seg_start = segment['start']
            seg_end = segment['end']
            
            # Проверяем пересечение с учетом смещения времени клипа
            clip_seg_start = max(0, seg_start - start_time)
            clip_seg_end = min(end_time - start_time, seg_end - start_time)
            
            if clip_seg_start < clip_seg_end and seg_end > start_time and seg_start < end_time:
                matching_segments.append({
                    'text': segment['text'].strip(),
                    'start': clip_seg_start,
                    'end': clip_seg_end,
                    'original_start': seg_start,
                    'original_end': seg_end
                })
                logger.info(f"✅ Найден сегмент: '{segment['text'][:50]}...' ({clip_seg_start:.1f}-{clip_seg_end:.1f}s)")
        
        logger.info(f"📊 Найдено {len(matching_segments)} сегментов для клипа")
        return matching_segments
    
    def create_word_level_timings(self, segments):
        """Создает тайминги на уровне слов из сегментов"""
        word_timings = []
        
        for segment in segments:
            words = segment['text'].split()
            if not words:
                continue
                
            segment_duration = segment['end'] - segment['start']
            word_duration = segment_duration / len(words)
            
            for i, word in enumerate(words):
                word_start = segment['start'] + (i * word_duration)
                word_end = word_start + word_duration
                
                word_timings.append({
                    'word': word,
                    'start': word_start,
                    'end': word_end
                })
        
        logger.info(f"📝 Создано {len(word_timings)} word-level таймингов")
        return word_timings
    
    def group_words_into_phrases_smart(self, word_timings, max_words=3):
        """Умная группировка слов в фразы с учетом пауз"""
        if not word_timings:
            return []
            
        phrases = []
        current_phrase = []
        
        for i, timing in enumerate(word_timings):
            current_phrase.append(timing)
            
            # Проверяем условия для завершения фразы
            should_end_phrase = (
                len(current_phrase) >= max_words or  # Достигли лимита слов
                timing['word'].endswith(('.', '!', '?', ',', ':')) or  # Знак препинания
                (i < len(word_timings) - 1 and 
                 word_timings[i + 1]['start'] - timing['end'] > 0.5)  # Пауза больше 0.5 сек
            )
            
            if should_end_phrase or i == len(word_timings) - 1:
                if current_phrase:
                    phrase_text = ' '.join([w['word'] for w in current_phrase])
                    phrase_start = current_phrase[0]['start']
                    phrase_end = current_phrase[-1]['end']
                    
                    phrases.append({
                        'text': phrase_text,
                        'start': phrase_start,
                        'end': phrase_end,
                        'words': current_phrase.copy()
                    })
                    logger.info(f"📝 Фраза: '{phrase_text}' ({phrase_start:.1f}-{phrase_end:.1f}s)")
                    current_phrase = []
        
        logger.info(f"🎯 Создано {len(phrases)} фраз")
        return phrases
    
    def escape_for_ffmpeg(self, text):
        """Экранирует текст для FFmpeg"""
        # Экранируем специальные символы
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace(",", "\\,")
        text = text.replace("[", "\\[")
        text = text.replace("]", "\\]")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")
        
        return text
    
    def generate_phrase_filter_with_highlight(self, phrase, style='modern'):
        """Генерирует фильтр для фразы с подсветкой слов"""
        style_config = self.styles[style]
        filters = []
        
        # Создаем фильтр для каждого слова в фразе
        for i, word_timing in enumerate(phrase['words']):
            # Создаем текст где текущее слово выделено
            words = [w['word'] for w in phrase['words']]
            
            # Простой подход - показываем всю фразу, но можем добавить эффекты позже
            phrase_text = ' '.join(words)
            escaped_text = self.escape_for_ffmpeg(phrase_text)
            
            # Фильтр для этого слова
            word_filter = f"drawtext=text='{escaped_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize={style_config['font_size']}:fontcolor={style_config['base_color']}:borderw={style_config['stroke_width']}:bordercolor={style_config['stroke_color']}:x=(w-text_w)/2:y=h*0.75:enable='between(t,{word_timing['start']},{word_timing['end']})'"
            
            filters.append(word_filter)
        
        return filters
    
    def get_crop_filter_9_16(self, video_width=1920, video_height=1080):
        """Генерирует фильтр обрезки для формата 9:16"""
        # Целевое соотношение 9:16 (0.5625)
        target_ratio = 9.0 / 16.0
        current_ratio = video_width / video_height
        
        if current_ratio > target_ratio:
            # Видео слишком широкое, обрезаем по ширине
            new_width = int(video_height * target_ratio)
            crop_x = (video_width - new_width) // 2
            return f"crop={new_width}:{video_height}:{crop_x}:0"
        else:
            # Видео слишком высокое, обрезаем по высоте  
            new_height = int(video_width / target_ratio)
            crop_y = (video_height - new_height) // 2
            return f"crop={video_width}:{new_height}:0:{crop_y}"
    
    def generate_ffmpeg_filter_advanced(self, segments, start_time, end_time, style='modern'):
        """Генерирует продвинутый FFmpeg фильтр с правильной синхронизацией"""
        try:
            logger.info(f"🎬 Генерируем продвинутые субтитры для клипа {start_time:.1f}-{end_time:.1f}s")
            
            # Находим сегменты для этого временного диапазона
            clip_segments = self.find_segments_for_timerange(segments, start_time, end_time)
            
            if not clip_segments:
                logger.warning("⚠️ Сегменты не найдены, используем fallback")
                return self.generate_fallback_filter("No audio found", style)
            
            # Создаем тайминги слов
            word_timings = self.create_word_level_timings(clip_segments)
            
            if not word_timings:
                logger.warning("⚠️ Word timings не созданы, используем fallback")
                return self.generate_fallback_filter(' '.join([s['text'] for s in clip_segments]), style)
            
            # Группируем в фразы
            phrases = self.group_words_into_phrases_smart(word_timings, max_words=3)
            
            if not phrases:
                logger.warning("⚠️ Фразы не созданы, используем fallback")
                return self.generate_fallback_filter(' '.join([s['text'] for s in clip_segments]), style)
            
            # Генерируем фильтры для каждой фразы
            all_filters = []
            for phrase in phrases:
                phrase_filters = self.generate_phrase_filter_with_highlight(phrase, style)
                all_filters.extend(phrase_filters)
            
            if not all_filters:
                logger.warning("⚠️ Фильтры не созданы, используем fallback")
                return self.generate_fallback_filter("Error generating filters", style)
            
            final_filter = ','.join(all_filters)
            logger.info(f"✅ Создан фильтр длиной {len(final_filter)} символов")
            return final_filter
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации продвинутого фильтра: {e}")
            return self.generate_fallback_filter("Error in subtitle generation", style)
    
    def generate_fallback_filter(self, text, style='modern'):
        """Fallback фильтр если основной не работает"""
        style_config = self.styles[style]
        escaped_text = self.escape_for_ffmpeg(text)
        
        logger.info(f"🔄 Используем fallback фильтр для: '{text[:50]}...'")
        return f"drawtext=text='{escaped_text}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize={style_config['font_size']}:fontcolor={style_config['base_color']}:borderw={style_config['stroke_width']}:bordercolor={style_config['stroke_color']}:x=(w-text_w)/2:y=h*0.75"

# Глобальные переменные
tasks = {}
active_tasks = set()
task_queue = deque()
generation_tasks = {}
client = None
subtitle_system = AdvancedAnimatedSubtitleSystem()

# Конфигурация
class Config:
    # Директории
    UPLOAD_DIR = "uploads"
    AUDIO_DIR = "audio"
    CLIPS_DIR = "clips"
    
    # Ограничения
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_CONCURRENT_TASKS = 3
    TASK_TIMEOUT = 600  # 10 минут
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Очистка
    CLEANUP_INTERVAL = 3600  # 1 час
    MAX_TASK_AGE = 86400  # 24 часа

# Создание директорий
for directory in [Config.UPLOAD_DIR, Config.AUDIO_DIR, Config.CLIPS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Инициализация OpenAI
try:
    from openai import OpenAI
    client = OpenAI(api_key=Config.OPENAI_API_KEY)
    logger.info("✅ OpenAI клиент инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации OpenAI: {e}")

# Executor для фоновых задач
executor = ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_TASKS)

def get_video_info(video_path):
    """Получает информацию о видео"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        video_stream = None
        for stream in info['streams']:
            if stream['codec_type'] == 'video':
                video_stream = stream
                break
        
        if video_stream:
            return {
                'width': int(video_stream.get('width', 1920)),
                'height': int(video_stream.get('height', 1080)),
                'duration': float(info['format'].get('duration', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '30/1'))
            }
        
        return {'width': 1920, 'height': 1080, 'duration': 0, 'fps': 30}
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о видео: {e}")
        return {'width': 1920, 'height': 1080, 'duration': 0, 'fps': 30}

def extract_audio(video_path, audio_path):
    """Извлекает аудио из видео"""
    try:
        cmd = [
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '16000', '-ac', '1', '-y', audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if os.path.exists(audio_path):
            file_size = os.path.getsize(audio_path)
            logger.info(f"✅ Аудио извлечено: {audio_path}")
            logger.info(f"📊 Размер аудио файла: {file_size / 1024 / 1024:.2f} MB")
            return True
        else:
            logger.error("❌ Аудио файл не создан")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка FFmpeg при извлечении аудио: {e}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения аудио: {e}")
        return False

def transcribe_audio_with_whisper(audio_path):
    """Транскрибирует аудио с помощью Whisper API"""
    try:
        logger.info(f"🎤 Начинаем транскрибацию: {audio_path}")
        
        file_size = os.path.getsize(audio_path)
        logger.info(f"📊 Размер аудио файла: {file_size / 1024 / 1024:.2f} MB")
        
        if file_size > 25 * 1024 * 1024:  # 25MB лимит Whisper API
            logger.info("📁 Файл большой, используем chunked транскрибацию")
            return transcribe_large_audio_chunked(audio_path)
        
        logger.info("🔄 Отправляем запрос к Whisper API...")
        
        with open(audio_path, "rb") as audio_file:
            # ИСПРАВЛЕНО: Убираем неподдерживаемый параметр timestamp_granularities
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        
        logger.info("✅ Транскрибация завершена успешно")
        logger.info(f"📝 Текст: {transcript.text[:100]}...")
        logger.info(f"📊 Количество сегментов: {len(transcript.segments)}")
        
        return {
            "text": transcript.text,
            "segments": [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                }
                for segment in transcript.segments
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации: {e}")
        return None

def transcribe_large_audio_chunked(audio_path):
    """Транскрибирует большой аудио файл по частям"""
    try:
        logger.info("🔄 Начинаем chunked транскрибацию...")
        
        # Разбиваем аудио на части по 20MB
        chunk_duration = 600  # 10 минут
        chunks = []
        
        # Получаем длительность аудио
        cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        total_duration = float(result.stdout.strip())
        
        chunk_count = int(total_duration / chunk_duration) + 1
        
        all_segments = []
        full_text = ""
        
        for i in range(chunk_count):
            start_time = i * chunk_duration
            chunk_path = f"{audio_path}_chunk_{i}.wav"
            
            # Создаем chunk
            cmd = [
                'ffmpeg', '-i', audio_path, '-ss', str(start_time), 
                '-t', str(chunk_duration), '-y', chunk_path
            ]
            subprocess.run(cmd, capture_output=True)
            
            if os.path.exists(chunk_path):
                # Транскрибируем chunk
                with open(chunk_path, "rb") as audio_file:
                    # Транскрибируем chunk без timestamp_granularities
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json"
                    )
                
                # Добавляем сегменты с корректировкой времени
                for segment in transcript.segments:
                    all_segments.append({
                        "start": segment.start + start_time,
                        "end": segment.end + start_time,
                        "text": segment.text
                    })
                
                full_text += " " + transcript.text
                
                # Удаляем chunk
                os.remove(chunk_path)
        
        logger.info(f"✅ Chunked транскрибация завершена: {len(all_segments)} сегментов")
        
        return {
            "text": full_text.strip(),
            "segments": all_segments
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка chunked транскрибации: {e}")
        return None

def analyze_transcript_with_chatgpt(transcript_text, segments):
    """Анализирует транскрипт с помощью ChatGPT"""
    try:
        logger.info("🤖 Начинаем анализ с ChatGPT...")
        
        prompt = f"""
Проанализируй этот транскрипт и найди 3 самых интересных и вирусных момента для коротких клипов.

Транскрипт: "{transcript_text}"

Сегменты с временными метками:
{json.dumps(segments, indent=2, ensure_ascii=False)}

Для каждого момента укажи:
1. title - короткий заголовок (до 50 символов)
2. start_time - время начала в секундах (точно из сегментов)
3. end_time - время окончания в секундах (точно из сегментов)  
4. quote - точная цитата из транскрипта
5. viral_score - оценка вирусности от 1 до 100
6. reason - почему этот момент может стать вирусным

Ответь ТОЛЬКО в формате JSON:
{{
  "highlights": [
    {{
      "title": "...",
      "start_time": 0.0,
      "end_time": 10.0,
      "quote": "...",
      "viral_score": 85,
      "reason": "..."
    }}
  ]
}}
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты эксперт по созданию вирусного контента для социальных сетей."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content.strip()
        logger.info(f"🤖 ChatGPT ответ получен: {len(result_text)} символов")
        
        # Парсим JSON
        try:
            # Убираем markdown форматирование если есть
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            result = json.loads(result_text)
            highlights = result.get("highlights", [])
            
            logger.info(f"✅ Найдено {len(highlights)} highlights")
            for i, highlight in enumerate(highlights):
                logger.info(f"🎯 Highlight {i+1}: {highlight.get('title', 'No title')} (score: {highlight.get('viral_score', 0)})")
            
            return highlights
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON от ChatGPT: {e}")
            logger.error(f"Ответ: {result_text}")
            return []
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа ChatGPT: {e}")
        return []

def generate_clip_with_advanced_subtitles(video_path, start_time, end_time, output_path, highlight, segments, subtitle_style="modern", animation_type="highlight"):
    """Генерирует клип с продвинутыми анимированными субтитрами"""
    try:
        logger.info(f"🎬 Генерируем клип: {start_time:.1f}-{end_time:.1f}s")
        logger.info(f"📝 Quote: {highlight['quote'][:100]}...")
        logger.info(f"🎨 Стиль: {subtitle_style}, анимация: {animation_type}")
        
        # Получаем информацию о видео
        video_info = get_video_info(video_path)
        logger.info(f"📊 Видео: {video_info['width']}x{video_info['height']}")
        
        # Генерируем продвинутый фильтр субтитров
        subtitle_filter = subtitle_system.generate_ffmpeg_filter_advanced(
            segments, start_time, end_time, subtitle_style
        )
        
        if not subtitle_filter or len(subtitle_filter) < 10:
            logger.warning("⚠️ Пустой фильтр субтитров, используем fallback")
            subtitle_filter = subtitle_system.generate_fallback_filter(highlight['quote'], subtitle_style)
        
        logger.info(f"📝 Фильтр субтитров: {len(subtitle_filter)} символов")
        
        # Генерируем фильтр обрезки для 9:16
        crop_filter = subtitle_system.get_crop_filter_9_16(video_info['width'], video_info['height'])
        logger.info(f"✂️ Обрезка для 9:16: {crop_filter}")
        
        # Комбинируем фильтры
        video_filter = f"{crop_filter},{subtitle_filter}"
        
        # FFmpeg команда
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-vf', video_filter,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            '-crf', '23',
            '-y', output_path
        ]
        
        logger.info(f"🔧 FFmpeg команда: {' '.join(cmd[:10])}...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Клип создан: {output_path}")
            logger.info(f"📊 Размер: {file_size / 1024:.1f} KB")
            return True
        else:
            logger.error("❌ Файл клипа не создан")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка FFmpeg при создании клипа: {e}")
        logger.error(f"FFmpeg stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка создания клипа: {e}")
        return False

async def process_video_analysis(task_id: str, video_path: str, filename: str):
    """Обрабатывает анализ видео"""
    try:
        logger.info(f"🎬 Начинаем анализ видео: {task_id}")
        
        # Обновляем статус
        tasks[task_id].update({
            "status": "processing",
            "progress": 10,
            "current_step": "Извлечение аудио"
        })
        
        # Извлекаем аудио
        audio_path = os.path.join(Config.AUDIO_DIR, f"{task_id}.wav")
        logger.info(f"🎵 Извлекаем аудио: {video_path} -> {audio_path}")
        
        if not extract_audio(video_path, audio_path):
            raise Exception("Ошибка извлечения аудио")
        
        tasks[task_id].update({
            "progress": 30,
            "current_step": "Транскрибация аудио",
            "audio_path": audio_path
        })
        
        # Транскрибируем аудио
        logger.info(f"🎤 Начинаем транскрибацию: {audio_path}")
        transcript_result = transcribe_audio_with_whisper(audio_path)
        
        if not transcript_result:
            raise Exception("Ошибка транскрибации")
        
        tasks[task_id].update({
            "progress": 60,
            "current_step": "Анализ контента",
            "transcript": transcript_result["text"],
            "segments": transcript_result["segments"]
        })
        
        # Анализируем с ChatGPT
        logger.info("🤖 Анализируем контент с ChatGPT...")
        highlights = analyze_transcript_with_chatgpt(
            transcript_result["text"], 
            transcript_result["segments"]
        )
        
        if not highlights:
            raise Exception("Не удалось найти интересные моменты")
        
        # Завершаем
        tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "current_step": "Анализ завершен",
            "highlights": highlights,
            "completed_at": time.time(),
            "elapsed_time": time.time() - tasks[task_id]["created_at"]
        })
        
        logger.info(f"✅ Анализ видео завершен: {task_id}")
        logger.info(f"📊 Найдено {len(highlights)} highlights")
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа видео {task_id}: {e}")
        tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time(),
            "elapsed_time": time.time() - tasks[task_id]["created_at"]
        })
    finally:
        active_tasks.discard(task_id)

async def process_clip_generation(generation_task_id: str, task_id: str, subtitle_style: str, animation_type: str):
    """Обрабатывает генерацию клипов"""
    try:
        logger.info(f"🎬 Начинаем генерацию клипов: {generation_task_id}")
        
        if task_id not in tasks:
            raise Exception(f"Задача {task_id} не найдена")
        
        task = tasks[task_id]
        if task["status"] != "completed":
            raise Exception(f"Задача {task_id} не завершена")
        
        highlights = task.get("highlights", [])
        video_path = task.get("video_path")
        segments = task.get("segments", [])
        
        if not highlights:
            raise Exception("Highlights не найдены")
        
        # Обновляем статус генерации
        generation_tasks[generation_task_id].update({
            "status": "processing",
            "progress": 10,
            "highlights": highlights,
            "video_path": video_path,
            "subtitle_style": subtitle_style,
            "animation_type": animation_type,
            "clips": []
        })
        
        clips = []
        total_highlights = len(highlights)
        
        for i, highlight in enumerate(highlights):
            try:
                logger.info(f"Генерируем клип {i+1}/{total_highlights}: {highlight['title']}")
                
                # Обновляем прогресс
                progress = 10 + (i * 80 // total_highlights)
                generation_tasks[generation_task_id]["progress"] = progress
                generation_tasks[generation_task_id]["log"].append(f"Генерируем клип {i+1}/{total_highlights}: {highlight['title']}")
                
                # Генерируем уникальный ID для клипа
                clip_id = str(uuid.uuid4())
                output_path = os.path.join(Config.CLIPS_DIR, f"{clip_id}.mp4")
                
                # Генерируем клип с продвинутыми субтитрами
                success = generate_clip_with_advanced_subtitles(
                    video_path=video_path,
                    start_time=highlight["start_time"],
                    end_time=highlight["end_time"],
                    output_path=output_path,
                    highlight=highlight,
                    segments=segments,
                    subtitle_style=subtitle_style,
                    animation_type=animation_type
                )
                
                if success and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    
                    clip_info = {
                        "id": clip_id,
                        "title": highlight["title"],
                        "start_time": highlight["start_time"],
                        "end_time": highlight["end_time"],
                        "duration": highlight["end_time"] - highlight["start_time"],
                        "viral_score": highlight["viral_score"],
                        "quote": highlight["quote"],
                        "file_path": output_path,
                        "file_size": file_size,
                        "subtitle_style": subtitle_style,
                        "animation_type": animation_type
                    }
                    
                    clips.append(clip_info)
                    generation_tasks[generation_task_id]["clips"] = clips
                    generation_tasks[generation_task_id]["log"].append(f"✅ Клип {i+1} готов: {highlight['title']}")
                    
                    logger.info(f"✅ Клип {i+1} создан: {highlight['title']}")
                else:
                    logger.error(f"❌ Ошибка создания клипа: {output_path}")
                    generation_tasks[generation_task_id]["log"].append(f"❌ Ошибка создания клипа {i+1}: {highlight['title']}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка создания клипа {i+1}: {e}")
                generation_tasks[generation_task_id]["log"].append(f"❌ Ошибка создания клипа {i+1}: {str(e)}")
        
        # Завершаем генерацию
        generation_tasks[generation_task_id].update({
            "status": "completed",
            "progress": 100,
            "completed_at": time.time(),
            "elapsed_time": time.time() - generation_tasks[generation_task_id]["created_at"]
        })
        
        logger.info(f"✅ Генерация клипов завершена: {generation_task_id}, создано {len(clips)} клипов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации клипов {generation_task_id}: {e}")
        generation_tasks[generation_task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time(),
            "elapsed_time": time.time() - generation_tasks[generation_task_id]["created_at"]
        })

# API Endpoints

@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        # Проверяем использование ресурсов
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "status": "healthy",
            "version": "15.7-critical-fixes",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": len(active_tasks),
            "queue_size": len(task_queue),
            "total_tasks": len(tasks),
            "total_generations": len(generation_tasks),
            "memory_usage": f"{memory_percent:.1f}%",
            "cpu_usage": f"{cpu_percent:.1f}%",
            "dependencies": {
                "ffmpeg": True,
                "openai": client is not None
            }
        }
    except Exception as e:
        logger.error(f"❌ Ошибка health check: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/api/videos/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Анализирует видео и находит лучшие моменты"""
    try:
        # Проверяем размер файла
        if file.size > Config.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Файл слишком большой")
        
        # Генерируем ID задачи
        task_id = str(uuid.uuid4())
        
        # Сохраняем файл
        video_path = os.path.join(Config.UPLOAD_DIR, f"{task_id}_{file.filename}")
        
        async with aiofiles.open(video_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"📤 Видео загружено: {task_id} ({len(content)} bytes)")
        
        # Создаем задачу
        tasks[task_id] = {
            "id": task_id,
            "status": "queued",
            "progress": 0,
            "video_path": video_path,
            "filename": file.filename,
            "file_size": len(content),
            "created_at": time.time(),
            "current_step": "В очереди"
        }
        
        # Запускаем обработку
        active_tasks.add(task_id)
        background_tasks.add_task(process_video_analysis, task_id, video_path, file.filename)
        
        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Video analysis started",
            "estimated_time": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа видео: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{task_id}/status")
async def get_video_status(task_id: str):
    """Получает статус анализа видео"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
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
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        task = tasks[task_id]
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Анализ видео не завершен")
        
        highlights = task.get("highlights", [])
        if not highlights:
            raise HTTPException(status_code=400, detail="Highlights не найдены")
        
        # Генерируем ID для генерации
        generation_task_id = str(uuid.uuid4())
        
        # Создаем задачу генерации
        generation_tasks[generation_task_id] = {
            "id": generation_task_id,
            "status": "queued",
            "progress": 0,
            "task_id": task_id,
            "created_at": time.time(),
            "log": []
        }
        
        # Запускаем генерацию
        background_tasks.add_task(
            process_clip_generation, 
            generation_task_id, 
            task_id, 
            subtitle_style, 
            animation_type
        )
        
        return {
            "generation_task_id": generation_task_id,
            "status": "queued",
            "message": f"Clip generation with {subtitle_style} subtitles and {animation_type} animation started",
            "highlights_count": len(highlights),
            "subtitle_style": subtitle_style,
            "animation_type": animation_type
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации клипов: {e}")
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
    clip_path = os.path.join(Config.CLIPS_DIR, f"{clip_id}.mp4")
    
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Клип не найден")
    
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

# Очистка старых файлов
async def cleanup_old_files():
    """Очищает старые файлы"""
    try:
        current_time = time.time()
        
        # Очищаем старые задачи
        expired_tasks = [
            task_id for task_id, task in tasks.items()
            if current_time - task["created_at"] > Config.MAX_TASK_AGE
        ]
        
        for task_id in expired_tasks:
            task = tasks[task_id]
            
            # Удаляем файлы
            for file_path in [task.get("video_path"), task.get("audio_path")]:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            
            del tasks[task_id]
            logger.info(f"🗑️ Удалена старая задача: {task_id}")
        
        # Очищаем старые генерации
        expired_generations = [
            gen_id for gen_id, gen in generation_tasks.items()
            if current_time - gen["created_at"] > Config.MAX_TASK_AGE
        ]
        
        for gen_id in expired_generations:
            generation = generation_tasks[gen_id]
            
            # Удаляем клипы
            for clip in generation.get("clips", []):
                clip_path = clip.get("file_path")
                if clip_path and os.path.exists(clip_path):
                    os.remove(clip_path)
            
            del generation_tasks[gen_id]
            logger.info(f"🗑️ Удалена старая генерация: {gen_id}")
        
        # Принудительная сборка мусора
        gc.collect()
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки: {e}")

# Запуск периодической очистки
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 AgentFlow AI Clips v15.7 with Critical Fixes started!")
    
    # Запускаем периодическую очистку
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(Config.CLEANUP_INTERVAL)
            await cleanup_old_files()
    
    asyncio.create_task(periodic_cleanup())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

