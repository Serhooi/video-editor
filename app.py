"""
AgentFlow AI Clips v15.5.4 - ИСПРАВЛЕНИЕ ОШИБКИ FFMPEG
Исправлена ошибка "No such filter: ''" в анимированных субтитрах

ИСПРАВЛЕНИЯ v15.5.4:
1. Улучшена логика поиска сегментов для клипов
2. Добавлена валидация фильтра перед передачей в FFmpeg  
3. Добавлен fallback на статичные субтитры
4. Детальное логирование для диагностики
5. Исправлено экранирование специальных символов

СОХРАНЕНЫ ВСЕ ВОЗМОЖНОСТИ v15.5:
- Анимированные субтитры с подсветкой слов
- 5 стилей субтитров (Classic, Neon, Bold, Minimal, Gradient)
- 3 типа анимации (Highlight, Scale, Glow)
- Word-level timing для точной синхронизации
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
app = FastAPI(title="AgentFlow AI Clips", version="15.5.5-whisper-fix")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация
class Config:
    # Основные настройки
    MAX_VIDEO_SIZE_MB = 100
    MAX_CONCURRENT_TASKS = 3
    MAX_QUEUE_SIZE = 10
    
    # Настройки видео
    VIDEO_PRESET = "fast"
    VIDEO_CRF = "23"
    VIDEO_BITRATE = "2M"
    
    # Таймауты (увеличены для длинных видео)
    WHISPER_TIMEOUT = 900  # 15 минут
    FFMPEG_TIMEOUT = 300   # 5 минут
    OPENAI_TIMEOUT = 120   # 2 минуты
    
    # Настройки аудио chunking
    MAX_AUDIO_SIZE_MB = 20  # Максимальный размер для Whisper API
    CHUNK_DURATION = 300    # 5 минут на chunk
    
    # Настройки очистки
    CLEANUP_INTERVAL = 3600  # 1 час
    MAX_FILE_AGE = 86400     # 24 часа

config = Config()

# Директории
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
AUDIO_DIR = BASE_DIR / "audio"
CLIPS_DIR = BASE_DIR / "clips"
TASKS_DIR = BASE_DIR / "tasks"

# Создаем директории
for directory in [UPLOADS_DIR, AUDIO_DIR, CLIPS_DIR, TASKS_DIR]:
    directory.mkdir(exist_ok=True)
    logger.info(f"📁 ДИАГНОСТИКА: Директория {directory.name} готова")

# Глобальные переменные
tasks: Dict[str, Dict] = {}
generation_tasks: Dict[str, Dict] = {}
active_tasks = set()
task_queue = deque()

# Система анимированных субтитров
class AnimatedSubtitleSystem:
    """Система создания анимированных субтитров с подсветкой слов"""
    
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
    
    ANIMATION_TYPES = {
        "highlight": "color_change",
        "scale": "size_increase", 
        "glow": "shadow_effect",
        "underline": "text_decoration",
        "bounce": "position_animation"
    }

    def __init__(self):
        self.max_subtitles = 3
        self.subtitle_duration = 3.0
        
    def create_word_level_subtitles(self, segments: List[Dict], style: str = "classic", 
                                  animation: str = "highlight") -> List[Dict]:
        """Создает субтитры с анимацией на уровне слов"""
        
        logger.info(f"🎨 Создаем анимированные субтитры: {len(segments)} сегментов, стиль: {style}, анимация: {animation}")
        
        # Ограничиваем количество субтитров
        limited_segments = segments[:self.max_subtitles]
        
        animated_subtitles = []
        
        for i, segment in enumerate(limited_segments):
            subtitle = self._create_animated_subtitle(
                segment, style, animation, i
            )
            animated_subtitles.append(subtitle)
            
        logger.info(f"✅ Создано {len(animated_subtitles)} анимированных субтитров")
        return animated_subtitles
    
    def _create_animated_subtitle(self, segment: Dict, style: str, 
                                animation: str, index: int) -> Dict:
        """Создает один анимированный субтитр"""
        
        text = segment["text"].strip()
        start_time = segment["start"] 
        end_time = segment["end"]
        
        logger.info(f"📝 Создаем субтитр {index+1}: '{text}' ({start_time:.1f}-{end_time:.1f}s)")
        
        # Разбиваем текст на слова
        words = text.split()
        word_duration = (end_time - start_time) / len(words) if len(words) > 0 else 1.0
        
        # Создаем анимацию для каждого слова
        word_animations = []
        for j, word in enumerate(words):
            word_start = start_time + (j * word_duration)
            word_end = word_start + word_duration
            
            word_animation = {
                "word": word,
                "start": word_start,
                "end": word_end,
                "style": self.SUBTITLE_STYLES[style],
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
        
        logger.info(f"🔧 Генерируем FFmpeg фильтр для {len(animated_subtitles)} субтитров")
        
        if not animated_subtitles:
            logger.warning("⚠️ Нет анимированных субтитров для генерации фильтра")
            return ""
        
        filters = []
        
        for subtitle in animated_subtitles:
            # Позиция субтитра (снизу вверх)
            y_position = video_height - 200 - (subtitle["index"] * 100)
            
            logger.info(f"🎯 Субтитр {subtitle['index']+1}: {len(subtitle['words'])} слов, позиция Y: {y_position}")
            
            # Создаем фильтр для каждого слова
            for word_data in subtitle["words"]:
                word_filter = self._create_word_filter(
                    word_data, y_position, video_width
                )
                if word_filter:  # Проверяем что фильтр не пустой
                    filters.append(word_filter)
        
        final_filter = ",".join(filters)
        logger.info(f"✅ FFmpeg фильтр создан: {len(final_filter)} символов")
        
        if len(final_filter) > 100:
            logger.info(f"🔍 Фильтр (первые 100 символов): {final_filter[:100]}...")
        else:
            logger.info(f"🔍 Полный фильтр: {final_filter}")
        
        return final_filter
    
    def _create_word_filter(self, word_data: Dict, y_pos: int, 
                          video_width: int) -> str:
        """Создает FFmpeg фильтр для одного слова"""
        
        try:
            style = word_data["style"]
            word = self._escape_text_for_ffmpeg(word_data["word"])
            start = word_data["start"]
            end = word_data["end"]
            animation = word_data["animation"]
            
            # Проверяем валидность данных
            if not word or start < 0 or end <= start:
                logger.warning(f"⚠️ Невалидные данные слова: '{word}', {start}-{end}")
                return ""
            
            # Базовые параметры
            base_params = [
                f"text='{word}'",
                f"fontcolor={style['fontcolor']}", 
                f"fontsize={style['fontsize']}",
                f"x=(w-text_w)/2",  # Центрирование по горизонтали
                f"y={y_pos}",
                f"enable='between(t,{start:.2f},{end:.2f})'"
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
                base_params[1] = f"fontcolor=if(between(t,{mid_time-0.2:.2f},{mid_time+0.2:.2f}),{highlight_color},{style['fontcolor']})"
                
            elif animation == "scale":
                # Увеличение размера
                mid_time = (start + end) / 2
                scale_factor = int(float(style["fontsize"]) * 1.2)
                base_params[2] = f"fontsize=if(between(t,{mid_time-0.2:.2f},{mid_time+0.2:.2f}),{scale_factor},{style['fontsize']})"
                
            elif animation == "glow":
                # Добавляем эффект свечения через тень
                base_params.append(f"shadowcolor={style['highlight_color']}")
                base_params.append("shadowx=0")
                base_params.append("shadowy=0")
            
            # Фильтруем пустые параметры
            valid_params = [param for param in base_params if param and "=" in param]
            
            if not valid_params:
                logger.warning(f"⚠️ Нет валидных параметров для слова '{word}'")
                return ""
            
            filter_result = f"drawtext={':'.join(valid_params)}"
            return filter_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания фильтра для слова: {e}")
            return ""
    
    def _escape_text_for_ffmpeg(self, text: str) -> str:
        """Экранирует текст для FFmpeg"""
        if not text:
            return ""
            
        # Заменяем специальные символы
        text = text.replace("\\", "\\\\")  # Экранируем обратные слеши первыми
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace(",", "\\,")
        text = text.replace("[", "\\[")
        text = text.replace("]", "\\]")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")
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
        logger.error(f"❌ ДИАГНОСТИКА: Ошибка проверки API: {e}")
        
except ImportError:
    logger.error("❌ OpenAI библиотека не установлена")
    client = None
except Exception as e:
    logger.error(f"❌ Ошибка инициализации OpenAI: {e}")
    client = None

# Функции для работы с видео и аудио
async def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Извлекает аудио из видео"""
    try:
        logger.info(f"🎵 Извлекаем аудио: {video_path} -> {audio_path}")
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
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
        logger.info(f"🎤 Начинаем транскрибацию: {audio_path}")
        
        if not client:
            raise ValueError("OpenAI клиент не инициализирован")
        
        # Проверяем размер файла
        file_size = os.path.getsize(audio_path)
        file_size_mb = file_size / (1024 * 1024)
        logger.info(f"📊 Размер аудио файла: {file_size_mb:.2f} MB")
        
        if file_size_mb > config.MAX_AUDIO_SIZE_MB:
            logger.info(f"📦 Файл большой ({file_size_mb:.2f} MB), используем chunking")
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
                # ИСПРАВЛЕНО: Универсальная обработка сегментов (dict или object)
                if isinstance(segment, dict):
                    segment_data = {
                        "start": segment.get("start", 0),
                        "end": segment.get("end", 0),
                        "text": segment.get("text", "").strip()
                    }
                else:
                    segment_data = {
                        "start": getattr(segment, "start", 0),
                        "end": getattr(segment, "end", 0),
                        "text": getattr(segment, "text", "").strip()
                    }
                
                if segment_data["text"]:  # Только непустые сегменты
                    segments.append(segment_data)
        
        return {
            "text": transcript.text,
            "segments": segments
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации: {e}")
        return None

async def transcribe_large_audio_chunked(audio_path: str) -> Optional[Dict]:
    """Транскрибирует большой аудио файл по частям"""
    try:
        logger.info(f"📦 Начинаем chunked транскрибацию: {audio_path}")
        
        # Получаем длительность аудио
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", 
               "-of", "csv=p=0", audio_path]
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise ValueError(f"Ошибка получения длительности: {stderr.decode()}")
        
        total_duration = float(stdout.decode().strip())
        logger.info(f"📊 Общая длительность: {total_duration:.2f} секунд")
        
        # Разбиваем на chunks
        chunk_duration = config.CHUNK_DURATION
        chunks = []
        all_segments = []
        full_text = ""
        
        for start_time in range(0, int(total_duration), chunk_duration):
            end_time = min(start_time + chunk_duration, total_duration)
            
            # Создаем chunk
            chunk_path = f"{audio_path}.chunk_{start_time}_{end_time}.wav"
            
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-ss", str(start_time), "-t", str(end_time - start_time),
                "-y", chunk_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
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
                
                # Обрабатываем сегменты с коррекцией времени
                if hasattr(transcript, 'segments') and transcript.segments:
                    for segment in transcript.segments:
                        if isinstance(segment, dict):
                            segment_data = {
                                "start": segment.get("start", 0) + start_time,
                                "end": segment.get("end", 0) + start_time,
                                "text": segment.get("text", "").strip()
                            }
                        else:
                            segment_data = {
                                "start": getattr(segment, "start", 0) + start_time,
                                "end": getattr(segment, "end", 0) + start_time,
                                "text": getattr(segment, "text", "").strip()
                            }
                        
                        if segment_data["text"]:
                            all_segments.append(segment_data)
                
                # Удаляем chunk файл
                os.remove(chunk_path)
            
        logger.info(f"✅ Chunked транскрибация завершена: {len(all_segments)} сегментов")
        
        return {
            "text": full_text.strip(),
            "segments": all_segments
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка chunked транскрибации: {e}")
        return None

async def analyze_transcript_with_chatgpt(transcript: str, segments: List[Dict]) -> List[Dict]:
    """Анализирует транскрипт с помощью ChatGPT для поиска лучших моментов"""
    try:
        logger.info("🤖 Анализируем транскрипт с ChatGPT...")
        
        if not client:
            raise ValueError("OpenAI клиент не инициализирован")
        
        # Создаем промпт для анализа
        prompt = f"""
Проанализируй этот транскрипт и найди 3 самых интересных и вирусных момента для коротких клипов.

Транскрипт: "{transcript}"

Сегменты с временными метками:
{json.dumps(segments, indent=2)}

Верни результат в JSON формате:
{{
  "highlights": [
    {{
      "title": "Краткое название момента",
      "start_time": 0.0,
      "end_time": 10.0,
      "viral_score": 85,
      "quote": "Точная цитата из этого момента"
    }}
  ]
}}

Требования:
- Каждый клип должен быть 10-30 секунд
- Выбирай самые эмоциональные и запоминающиеся моменты
- Viral score от 1 до 100
- Quote должна точно соответствовать тексту из сегментов
- Время должно точно соответствовать сегментам
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты эксперт по созданию вирусного контента. Анализируй видео и находи лучшие моменты для коротких клипов."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        logger.info("✅ Анализ ChatGPT завершен")
        
        # Логируем ответ для диагностики
        response_text = response.choices[0].message.content
        logger.info(f"🔍 Ответ ChatGPT (первые 500 символов): {response_text[:500]}...")
        
        # ИСПРАВЛЕНО: Улучшенный парсинг JSON
        try:
            # Ищем JSON в ответе с помощью regex
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
            else:
                # Пробуем парсить весь ответ как JSON
                result = json.loads(response_text)
            
            highlights = result.get("highlights", [])
            logger.info(f"✅ Найдено {len(highlights)} highlights")
            
            # Валидируем highlights
            valid_highlights = []
            for highlight in highlights:
                if all(key in highlight for key in ["title", "start_time", "end_time", "viral_score", "quote"]):
                    valid_highlights.append(highlight)
                else:
                    logger.warning(f"⚠️ Невалидный highlight: {highlight}")
            
            logger.info(f"✅ Валидных highlights: {len(valid_highlights)}")
            return valid_highlights
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON ответа от ChatGPT: {e}")
            logger.error(f"🔍 Ответ: {response_text}")
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
        logger.info(f"📝 Quote: {quote}")
        
        # ИСПРАВЛЕНО: Улучшенная логика поиска сегментов
        clip_segments = []
        for segment in segments:
            # Проверяем пересечение временных интервалов
            segment_start = segment["start"]
            segment_end = segment["end"]
            
            # Сегмент пересекается с клипом если:
            # 1. Начало сегмента внутри клипа
            # 2. Конец сегмента внутри клипа  
            # 3. Сегмент полностью покрывает клип
            # 4. Клип полностью покрывает сегмент
            if (start_time <= segment_start <= end_time) or \
               (start_time <= segment_end <= end_time) or \
               (segment_start <= start_time and segment_end >= end_time) or \
               (start_time <= segment_start and end_time >= segment_end):
                
                # Корректируем время относительно начала клипа
                adjusted_start = max(0, segment_start - start_time)
                adjusted_end = min(end_time - start_time, segment_end - start_time)
                
                # Проверяем что сегмент имеет положительную длительность
                if adjusted_end > adjusted_start:
                    adjusted_segment = {
                        "start": adjusted_start,
                        "end": adjusted_end,
                        "text": segment["text"]
                    }
                    clip_segments.append(adjusted_segment)
                    logger.info(f"📝 Добавлен сегмент: '{segment['text']}' ({adjusted_start:.1f}-{adjusted_end:.1f}s)")
        
        logger.info(f"📝 Найдено {len(clip_segments)} сегментов для субтитров")
        
        # ИСПРАВЛЕНО: Fallback если сегменты не найдены
        if not clip_segments:
            logger.warning("⚠️ Не найдено сегментов для анимированных субтитров, используем quote")
            # Создаем сегмент из quote
            duration = end_time - start_time
            clip_segments = [{
                "start": 0,
                "end": min(duration, 5.0),  # Максимум 5 секунд
                "text": quote
            }]
        
        # Создаем анимированные субтитры
        animated_subtitles = subtitle_system.create_word_level_subtitles(
            clip_segments, subtitle_style, animation_type
        )
        
        # Генерируем FFmpeg фильтр
        subtitle_filter = subtitle_system.generate_ffmpeg_filter(animated_subtitles)
        
        logger.info(f"🔧 FFmpeg фильтр создан: {len(subtitle_filter)} символов")
        
        # ИСПРАВЛЕНО: Валидация фильтра
        if not subtitle_filter or len(subtitle_filter) < 10:
            logger.warning("⚠️ Фильтр пустой или слишком короткий, используем fallback")
            # Fallback на простые статичные субтитры
            escaped_quote = quote.replace("'", "\\'").replace(":", "\\:")
            subtitle_filter = f"drawtext=text='{escaped_quote}':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=h-150:bordercolor=black:borderw=3"
        
        # Команда FFmpeg с анимированными субтитрами
        duration = end_time - start_time
        
        # ИСПРАВЛЕНО: Проверяем что фильтр не пустой перед добавлением в команду
        if subtitle_filter:
            vf_filter = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}"
        else:
            logger.warning("⚠️ Используем клип без субтитров")
            vf_filter = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", str(start_time), "-t", str(duration),
            "-vf", vf_filter,
            "-c:v", "libx264", "-preset", config.VIDEO_PRESET,
            "-crf", config.VIDEO_CRF, "-b:v", config.VIDEO_BITRATE,
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-y", output_path
        ]
        
        logger.info("🎬 Запускаем FFmpeg с анимированными субтитрами...")
        logger.info(f"🔧 Команда FFmpeg: {' '.join(cmd[:10])}... (сокращено)")
        
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
            error_msg = stderr.decode()
            logger.error(f"❌ Ошибка создания клипа: {error_msg}")
            
            # Дополнительная диагностика
            if "No such filter" in error_msg:
                logger.error("🔍 Ошибка фильтра FFmpeg - проверьте синтаксис")
                logger.error(f"🔍 Проблемный фильтр: {subtitle_filter}")
            
            return False
            
    except asyncio.TimeoutError:
        logger.error(f"⏰ Таймаут создания клипа: {config.FFMPEG_TIMEOUT}s")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка создания клипа: {e}")
        logger.error(f"🔍 Traceback: {traceback.format_exc()}")
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
            
        tasks[task_id]["progress"] = 60
        tasks[task_id]["transcript"] = transcript_result["text"]
        tasks[task_id]["segments"] = transcript_result["segments"]
        
        # Анализируем с ChatGPT
        highlights = await analyze_transcript_with_chatgpt(
            transcript_result["text"], 
            transcript_result["segments"]
        )
        
        tasks[task_id]["progress"] = 90
        tasks[task_id]["highlights"] = highlights
        
        # Завершаем
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["completed_at"] = time.time()
        
        logger.info(f"✅ Анализ видео завершен: {task_id}")
        
        # Запускаем следующую задачу из очереди
        if task_queue and len(active_tasks) < config.MAX_CONCURRENT_TASKS:
            next_task_id = task_queue.popleft()
            if next_task_id in tasks:
                active_tasks.add(next_task_id)
                # Здесь нужно запустить задачу, но у нас нет background_tasks
                # Это будет обработано в API endpoint
        
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
    
    # Добавляем информацию о времени
    if "created_at" in task_data:
        task_data["elapsed_time"] = time.time() - task_data["created_at"]
    
    return task_data

# НОВОЕ: API для генерации клипов с анимированными субтитрами
@app.post("/api/clips/generate")
async def generate_clips_with_animated_subtitles(
    background_tasks: BackgroundTasks,
    task_id: str = Query(..., description="ID задачи анализа видео"),
    subtitle_style: str = Query("classic", description="Стиль субтитров: classic, neon, bold, minimal, gradient"),
    animation_type: str = Query("highlight", description="Тип анимации: highlight, scale, glow")
):
    """Генерирует клипы с анимированными субтитрами"""
    try:
        # Проверяем что задача анализа существует и завершена
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="Задача анализа не найдена")
        
        task_data = tasks[task_id]
        if task_data["status"] != "completed":
            raise HTTPException(status_code=400, detail="Анализ видео не завершен")
        
        if not task_data.get("highlights"):
            raise HTTPException(status_code=400, detail="Не найдены highlights для генерации клипов")
        
        # Валидируем параметры
        valid_styles = ["classic", "neon", "bold", "minimal", "gradient"]
        valid_animations = ["highlight", "scale", "glow"]
        
        if subtitle_style not in valid_styles:
            raise HTTPException(status_code=400, detail=f"Неверный стиль субтитров. Доступные: {valid_styles}")
        
        if animation_type not in valid_animations:
            raise HTTPException(status_code=400, detail=f"Неверный тип анимации. Доступные: {valid_animations}")
        
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
        
        logger.info(f"🎬 Запущена генерация клипов: {generation_task_id} (стиль: {subtitle_style}, анимация: {animation_type})")
        
        return {
            "generation_task_id": generation_task_id,
            "status": "queued",
            "message": f"Clip generation with {subtitle_style} subtitles and {animation_type} animation started",
            "highlights_count": len(task_data["highlights"]),
            "subtitle_style": subtitle_style,
            "animation_type": animation_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка запуска генерации клипов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/generation/{generation_task_id}/status")
async def get_generation_status(generation_task_id: str):
    """Получает статус генерации клипов"""
    if generation_task_id not in generation_tasks:
        raise HTTPException(status_code=404, detail="Задача генерации не найдена")
    
    task_data = generation_tasks[generation_task_id].copy()
    
    # Добавляем информацию о времени
    if "created_at" in task_data:
        task_data["elapsed_time"] = time.time() - task_data["created_at"]
    
    return task_data

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

@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        # Проверяем доступность FFmpeg
        ffmpeg_available = False
        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg", "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=5)
            ffmpeg_available = process.returncode == 0
        except:
            pass
        
        # Проверяем OpenAI
        openai_available = client is not None
        
        # Информация о системе
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "status": "healthy",
            "version": "15.5.5-whisper-fix",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": len(active_tasks),
            "queue_size": len(task_queue),
            "total_tasks": len(tasks),
            "total_generations": len(generation_tasks),
            "memory_usage": f"{memory.percent}%",
            "cpu_usage": f"{cpu_percent}%",
            "dependencies": {
                "ffmpeg": ffmpeg_available,
                "openai": openai_available
            }
        }
    except Exception as e:
        logger.error(f"❌ Ошибка health check: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )

# Автоочистка старых файлов
async def cleanup_old_files():
    """Очищает старые файлы"""
    try:
        current_time = time.time()
        
        for directory in [UPLOADS_DIR, AUDIO_DIR, CLIPS_DIR]:
            for file_path in directory.glob("*"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > config.MAX_FILE_AGE:
                        file_path.unlink()
                        logger.info(f"🗑️ Удален старый файл: {file_path}")
        
        # Очищаем старые задачи
        old_task_ids = []
        for task_id, task_data in tasks.items():
            task_age = current_time - task_data.get("created_at", current_time)
            if task_age > config.MAX_FILE_AGE:
                old_task_ids.append(task_id)
        
        for task_id in old_task_ids:
            del tasks[task_id]
            logger.info(f"🗑️ Удалена старая задача: {task_id}")
        
        # Очищаем старые задачи генерации
        old_generation_ids = []
        for gen_id, gen_data in generation_tasks.items():
            gen_age = current_time - gen_data.get("created_at", current_time)
            if gen_age > config.MAX_FILE_AGE:
                old_generation_ids.append(gen_id)
        
        for gen_id in old_generation_ids:
            del generation_tasks[gen_id]
            logger.info(f"🗑️ Удалена старая задача генерации: {gen_id}")
        
        # Принудительная сборка мусора
        gc.collect()
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки: {e}")

# Запуск периодической очистки
@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 AgentFlow AI Clips v15.5.5 with Whisper Fix started!")
    
    # Запускаем периодическую очистку
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(config.CLEANUP_INTERVAL)
            await cleanup_old_files()
    
    asyncio.create_task(periodic_cleanup())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

