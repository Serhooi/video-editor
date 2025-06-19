#!/usr/bin/env python3
"""
AgentFlow AI Clips v16.0 - Complete Opus.pro Clone
Полноценная видеоплатформа с выбором форматов и улучшенными субтитрами
"""

import os
import json
import uuid
import asyncio
import logging
import subprocess
import tempfile
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import openai
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger("app")

# Настройка OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("❌ OPENAI_API_KEY не установлен!")
    raise ValueError("OPENAI_API_KEY environment variable is required")

# Создание директорий
os.makedirs("uploads", exist_ok=True)
os.makedirs("audio", exist_ok=True)
os.makedirs("clips", exist_ok=True)

app = FastAPI(
    title="AgentFlow AI Clips v16.0",
    description="Complete Opus.pro clone with format selection and advanced subtitles",
    version="16.0.0-opus-clone"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoFormatManager:
    """Менеджер форматов видео как в Opus.pro"""
    
    def __init__(self):
        self.formats = {
            "16:9": {
                "name": "Landscape 16:9",
                "description": "YouTube, Horizontal videos",
                "width": 1920,
                "height": 1080,
                "crop_filter": self._get_landscape_filter
            },
            "9:16": {
                "name": "Vertical 9:16", 
                "description": "TikTok, Instagram Reels, Shorts",
                "width": 1080,
                "height": 1920,
                "crop_filter": self._get_vertical_filter
            },
            "1:1": {
                "name": "Square 1:1",
                "description": "Instagram Feed",
                "width": 1080,
                "height": 1080,
                "crop_filter": self._get_square_filter
            },
            "4:5": {
                "name": "Portrait 4:5",
                "description": "Instagram Stories",
                "width": 1080,
                "height": 1350,
                "crop_filter": self._get_portrait_filter
            }
        }
    
    def get_available_formats(self) -> List[Dict]:
        """Получить список доступных форматов"""
        return [
            {
                "id": format_id,
                "name": format_data["name"],
                "description": format_data["description"],
                "width": format_data["width"],
                "height": format_data["height"]
            }
            for format_id, format_data in self.formats.items()
        ]
    
    def get_crop_filter(self, format_id: str) -> str:
        """Получить фильтр обрезки для формата"""
        if format_id not in self.formats:
            format_id = "9:16"  # Default
        
        return self.formats[format_id]["crop_filter"]()
    
    def _get_landscape_filter(self) -> str:
        """Фильтр для 16:9 (1920x1080)"""
        return "scale='if(gte(iw/ih,16/9),1920,-1)':'if(gte(iw/ih,16/9),-1,1080)',crop=1920:1080:(iw-1920)/2:(ih-1080)/2"
    
    def _get_vertical_filter(self) -> str:
        """Фильтр для 9:16 (1080x1920)"""
        return "scale='if(gte(iw/ih,9/16),1080,-1)':'if(gte(iw/ih,9/16),-1,1920)',crop=1080:1920:(iw-1080)/2:(ih-1920)/2"
    
    def _get_square_filter(self) -> str:
        """Фильтр для 1:1 (1080x1080)"""
        return "scale='if(gte(iw,ih),1080,-1)':'if(gte(iw,ih),-1,1080)',crop=1080:1080:(iw-1080)/2:(ih-1080)/2"
    
    def _get_portrait_filter(self) -> str:
        """Фильтр для 4:5 (1080x1350)"""
        return "scale='if(gte(iw/ih,4/5),1080,-1)':'if(gte(iw/ih,4/5),-1,1350)',crop=1080:1350:(iw-1080)/2:(ih-1350)/2"

class OpusProSubtitleSystem:
    """Система субтитров как в Opus.pro"""
    
    def __init__(self):
        self.styles = {
            "modern": {
                "base_color": "white",
                "highlight_color": "#00FF88",
                "shadow": "black@0.8",
                "font_family": "DejaVuSans-Bold.ttf"
            },
            "neon": {
                "base_color": "white", 
                "highlight_color": "#00FFFF",
                "shadow": "black@0.8",
                "font_family": "DejaVuSans-Bold.ttf"
            },
            "fire": {
                "base_color": "white",
                "highlight_color": "#FF6600", 
                "shadow": "black@0.8",
                "font_family": "DejaVuSans-Bold.ttf"
            },
            "elegant": {
                "base_color": "white",
                "highlight_color": "#FFD700",
                "shadow": "black@0.8", 
                "font_family": "DejaVuSans-Bold.ttf"
            }
        }
        
        # Минимальные интервалы отображения
        self.min_display_duration = 0.8  # секунд
        self.min_word_duration = 0.3     # секунд
    
    def calculate_adaptive_font_size(self, text_length: int, format_id: str = "9:16") -> int:
        """Адаптивный размер шрифта в зависимости от формата и длины текста"""
        logger.info(f"📏 Расчет размера шрифта для {text_length} символов, формат {format_id}")
        
        # Базовые размеры для разных форматов
        base_sizes = {
            "16:9": {"small": 48, "medium": 40, "large": 32, "xlarge": 28},
            "9:16": {"small": 64, "medium": 48, "large": 40, "xlarge": 32},
            "1:1": {"small": 56, "medium": 44, "large": 36, "xlarge": 30},
            "4:5": {"small": 60, "medium": 46, "large": 38, "xlarge": 31}
        }
        
        sizes = base_sizes.get(format_id, base_sizes["9:16"])
        
        if text_length <= 20:
            size = sizes["small"]
        elif text_length <= 40:
            size = sizes["medium"]
        elif text_length <= 70:
            size = sizes["large"]
        else:
            size = sizes["xlarge"]
            
        logger.info(f"✅ Выбран размер шрифта: {size}px для формата {format_id}")
        return size
    
    def smart_phrase_grouping(self, words_with_timing: List[Dict], max_words: int = 6) -> List[Dict]:
        """Умная группировка слов в фразы как в Opus.pro"""
        if not words_with_timing:
            return []
        
        phrases = []
        current_phrase_words = []
        current_phrase_start = None
        
        for i, word_data in enumerate(words_with_timing):
            if current_phrase_start is None:
                current_phrase_start = word_data['start']
            
            current_phrase_words.append(word_data)
            
            # Логика группировки как в Opus.pro
            should_break = False
            
            # 1. Достигли максимума слов
            if len(current_phrase_words) >= max_words:
                should_break = True
            
            # 2. Логические паузы (знаки препинания)
            elif word_data['word'].endswith(('.', '!', '?', ',')):
                should_break = True
            
            # 3. Большая пауза до следующего слова
            elif i < len(words_with_timing) - 1:
                next_word = words_with_timing[i + 1]
                pause_duration = next_word['start'] - word_data['end']
                if pause_duration > 0.5:  # Пауза больше 0.5 сек
                    should_break = True
            
            # 4. Последнее слово
            elif i == len(words_with_timing) - 1:
                should_break = True
            
            if should_break:
                phrase_text = ' '.join([w['word'] for w in current_phrase_words])
                phrase_end = current_phrase_words[-1]['end']
                
                # Обеспечиваем минимальную длительность
                phrase_duration = phrase_end - current_phrase_start
                if phrase_duration < self.min_display_duration:
                    phrase_end = current_phrase_start + self.min_display_duration
                
                phrases.append({
                    'text': phrase_text,
                    'start': current_phrase_start,
                    'end': phrase_end,
                    'words': current_phrase_words.copy()
                })
                
                current_phrase_words = []
                current_phrase_start = None
        
        logger.info(f"📝 Создано {len(phrases)} фраз с умной группировкой")
        return phrases
    
    def create_opus_style_animation(self, phrase: Dict, style_name: str = "modern", format_id: str = "9:16") -> str:
        """Создание анимации в стиле Opus.pro"""
        logger.info(f"🎨 Генерация анимации Opus.pro для: '{phrase['text'][:30]}...'")
        
        style = self.styles.get(style_name, self.styles["modern"])
        text = phrase['text']
        
        # Адаптивный размер шрифта
        font_size = self.calculate_adaptive_font_size(len(text), format_id)
        highlight_size = font_size + 8  # Увеличение для подсветки
        
        # Позиционирование в зависимости от формата
        y_positions = {
            "16:9": "h-150",    # Ближе к низу для горизонтального
            "9:16": "h-300",    # Выше для вертикального
            "1:1": "h-200",     # По центру для квадратного
            "4:5": "h-250"      # Средняя позиция для портретного
        }
        y_pos = y_positions.get(format_id, "h-300")
        
        # Экранирование текста
        escaped_text = self.escape_text_for_ffmpeg(text)
        
        # Базовый текст (белый, всегда видимый)
        base_filter = f"drawtext=text='{escaped_text}':fontfile=/usr/share/fonts/truetype/dejavu/{style['font_family']}:fontsize={font_size}:fontcolor={style['base_color']}:x=(w-text_w)/2:y={y_pos}:shadowcolor={style['shadow']}:shadowx=3:shadowy=3"
        
        # Анимация подсветки слов как в Opus.pro
        word_filters = []
        for word_data in phrase['words']:
            word = word_data['word']
            word_start = word_data['start']
            word_end = max(word_data['end'], word_start + self.min_word_duration)
            
            escaped_word = self.escape_text_for_ffmpeg(word)
            
            # Эффект подсветки: увеличение + цвет + дополнительная тень
            highlight_filter = f"drawtext=text='{escaped_word}':fontfile=/usr/share/fonts/truetype/dejavu/{style['font_family']}:fontsize={highlight_size}:fontcolor={style['highlight_color']}:x=(w-text_w)/2:y={y_pos}:shadowcolor={style['shadow']}:shadowx=4:shadowy=4:enable='between(t,{word_start:.3f},{word_end:.3f})'"
            
            word_filters.append(highlight_filter)
        
        # Объединяем все фильтры
        phrase_start = phrase['start']
        phrase_end = phrase['end']
        
        # Базовый текст показывается всё время фразы
        base_with_timing = f"{base_filter}:enable='between(t,{phrase_start:.3f},{phrase_end:.3f})'"
        
        # Собираем финальный фильтр
        all_filters = [base_with_timing] + word_filters
        result = ','.join(all_filters)
        
        logger.info(f"✅ Создан Opus.pro фильтр длиной {len(result)} символов")
        return result
    
    def escape_text_for_ffmpeg(self, text: str) -> str:
        """Улучшенное экранирование текста для FFmpeg"""
        # Заменяем специальные символы
        text = text.replace("'", "\\'")
        text = text.replace(":", "\\:")
        text = text.replace("[", "\\[")
        text = text.replace("]", "\\]")
        text = text.replace(",", "\\,")
        text = text.replace(";", "\\;")
        text = text.replace("(", "\\(")
        text = text.replace(")", "\\)")
        text = text.replace("=", "\\=")
        return text
    
    def find_segments_for_timerange(self, segments: List[Dict], start_time: float, end_time: float) -> List[Dict]:
        """Улучшенный поиск сегментов в заданном временном диапазоне"""
        logger.info(f"🔍 Поиск сегментов для диапазона {start_time:.1f}-{end_time:.1f}s")
        
        found_segments = []
        for segment in segments:
            # Универсальная обработка сегментов (объект или dict)
            seg_start = segment.start if hasattr(segment, 'start') else segment.get('start', 0)
            seg_end = segment.end if hasattr(segment, 'end') else segment.get('end', 0)
            
            # Более точная проверка пересечения
            overlap_start = max(start_time, seg_start)
            overlap_end = min(end_time, seg_end)
            
            # Если есть пересечение хотя бы на 0.1 секунды
            if overlap_end - overlap_start >= 0.1:
                found_segments.append(segment)
        
        logger.info(f"📊 Найдено {len(found_segments)} сегментов")
        return found_segments
    
    def create_word_level_timings(self, segments: List[Dict], start_time: float, end_time: float) -> List[Dict]:
        """Создание точных таймингов на уровне слов"""
        words_with_timing = []
        
        for segment in segments:
            # Универсальная обработка сегментов
            seg_start = segment.start if hasattr(segment, 'start') else segment.get('start', 0)
            seg_end = segment.end if hasattr(segment, 'end') else segment.get('end', 0)
            seg_text = segment.text if hasattr(segment, 'text') else segment.get('text', '')
            
            # Проверяем пересечение с нужным диапазоном
            overlap_start = max(start_time, seg_start)
            overlap_end = min(end_time, seg_end)
            
            if overlap_end > overlap_start:
                # Корректируем время относительно начала клипа
                word_start = max(0, overlap_start - start_time)
                word_end = min(end_time - start_time, overlap_end - start_time)
                
                # Разбиваем сегмент на слова
                words = seg_text.strip().split()
                if words and word_end > word_start:
                    duration_per_word = (word_end - word_start) / len(words)
                    
                    for i, word in enumerate(words):
                        # Очищаем слово от знаков препинания для отображения
                        clean_word = word.strip('.,!?;:"()[]{}')
                        if clean_word:  # Пропускаем пустые слова
                            word_timing = {
                                'word': word,  # Оригинальное слово с пунктуацией
                                'clean_word': clean_word,  # Очищенное слово
                                'start': word_start + i * duration_per_word,
                                'end': word_start + (i + 1) * duration_per_word
                            }
                            words_with_timing.append(word_timing)
        
        logger.info(f"📝 Создано {len(words_with_timing)} слов с таймингами")
        return words_with_timing
    
    def generate_opus_subtitles(self, segments: List[Dict], start_time: float, end_time: float, 
                               style: str = "modern", format_id: str = "9:16") -> str:
        """Генерация субтитров в стиле Opus.pro"""
        logger.info(f"🎬 Генерация Opus.pro субтитров для {start_time:.1f}-{end_time:.1f}s, формат {format_id}")
        
        # Поиск сегментов в диапазоне
        relevant_segments = self.find_segments_for_timerange(segments, start_time, end_time)
        
        if not relevant_segments:
            logger.warning("⚠️ Сегменты не найдены, используем fallback")
            return self._create_fallback_subtitle(format_id, style)
        
        # Создание таймингов на уровне слов
        words_with_timing = self.create_word_level_timings(relevant_segments, start_time, end_time)
        
        if not words_with_timing:
            logger.warning("⚠️ Слова с таймингами не найдены")
            return self._create_fallback_subtitle(format_id, style)
        
        # Умная группировка в фразы как в Opus.pro
        phrases = self.smart_phrase_grouping(words_with_timing, max_words=6)
        
        if not phrases:
            logger.warning("⚠️ Фразы не созданы")
            return self._create_fallback_subtitle(format_id, style)
        
        # Генерация анимации для каждой фразы
        phrase_filters = []
        for phrase in phrases:
            phrase_filter = self.create_opus_style_animation(phrase, style, format_id)
            phrase_filters.append(phrase_filter)
        
        # Объединение всех фильтров
        final_filter = ','.join(phrase_filters)
        
        logger.info(f"✅ Opus.pro субтитры созданы, длина: {len(final_filter)} символов")
        return final_filter
    
    def _create_fallback_subtitle(self, format_id: str, style: str) -> str:
        """Создание fallback субтитров"""
        style_data = self.styles.get(style, self.styles["modern"])
        font_size = self.calculate_adaptive_font_size(20, format_id)
        
        y_positions = {
            "16:9": "h-150",
            "9:16": "h-300", 
            "1:1": "h-200",
            "4:5": "h-250"
        }
        y_pos = y_positions.get(format_id, "h-300")
        
        return f"drawtext=text='Processing subtitles...':fontfile=/usr/share/fonts/truetype/dejavu/{style_data['font_family']}:fontsize={font_size}:fontcolor={style_data['base_color']}:x=(w-text_w)/2:y={y_pos}:shadowcolor={style_data['shadow']}:shadowx=3:shadowy=3"

# Глобальные переменные
tasks = {}
active_tasks = set()
task_queue = deque()
generation_tasks = {}

# Инициализация систем
format_manager = VideoFormatManager()
subtitle_system = OpusProSubtitleSystem()

def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """Извлечение аудио из видео"""
    try:
        logger.info(f"🎵 Извлекаем аудио: {video_path} -> {audio_path}")
        
        cmd = [
            "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le", 
            "-ar", "16000", "-ac", "1", "-y", audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(audio_path):
            logger.info(f"✅ Аудио извлечено: {audio_path}")
            return True
        else:
            logger.error(f"❌ Ошибка извлечения аудио: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Исключение при извлечении аудио: {e}")
        return False

def transcribe_audio_with_whisper(audio_path: str) -> Optional[Dict]:
    """Транскрибация аудио с помощью Whisper API"""
    try:
        logger.info(f"🎤 Начинаем транскрибацию: {audio_path}")
        
        # Проверяем размер файла
        file_size = os.path.getsize(audio_path)
        logger.info(f"📊 Размер аудио файла: {file_size / 1024 / 1024:.2f} MB")
        
        if file_size > 25 * 1024 * 1024:  # 25MB лимит
            logger.info("📂 Файл большой, используем chunked транскрибацию")
            return transcribe_large_audio_chunked(audio_path)
        
        logger.info("🔄 Отправляем запрос к Whisper API...")
        
        with open(audio_path, "rb") as audio_file:
            client = openai.OpenAI()
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json"
            )
        
        logger.info("✅ Транскрибация завершена успешно")
        logger.info(f"📝 Текст: {transcript.text[:100]}...")
        logger.info(f"📊 Количество сегментов: {len(transcript.segments) if hasattr(transcript, 'segments') else 'N/A'}")
        
        return transcript
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрибации: {e}")
        return None

def transcribe_large_audio_chunked(audio_path: str, chunk_duration: int = 600) -> Optional[Dict]:
    """Транскрибация больших аудио файлов по частям"""
    try:
        logger.info(f"📂 Chunked транскрибация: {audio_path}")
        
        # Получаем длительность аудио
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("❌ Не удалось получить длительность аудио")
            return None
        
        total_duration = float(result.stdout.strip())
        logger.info(f"⏱️ Общая длительность: {total_duration:.1f} секунд")
        
        all_segments = []
        full_text = ""
        
        # Разбиваем на части
        for start_time in range(0, int(total_duration), chunk_duration):
            end_time = min(start_time + chunk_duration, total_duration)
            
            # Создаем временный файл для части
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Извлекаем часть аудио
                cmd = [
                    "ffmpeg", "-i", audio_path, "-ss", str(start_time), 
                    "-t", str(end_time - start_time), "-y", temp_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"❌ Ошибка извлечения части {start_time}-{end_time}")
                    continue
                
                # Транскрибируем часть
                with open(temp_path, "rb") as audio_file:
                    client = openai.OpenAI()
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json"
                    )
                
                # Корректируем время сегментов
                if hasattr(transcript, 'segments'):
                    for segment in transcript.segments:
                        # Универсальная обработка сегментов
                        if hasattr(segment, 'start'):
                            segment.start += start_time
                            segment.end += start_time
                        else:
                            segment['start'] += start_time
                            segment['end'] += start_time
                        all_segments.append(segment)
                
                full_text += " " + transcript.text
                logger.info(f"✅ Обработана часть {start_time}-{end_time}")
                
            finally:
                # Удаляем временный файл
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        # Создаем объект результата
        class TranscriptResult:
            def __init__(self, text, segments):
                self.text = text.strip()
                self.segments = segments
        
        result = TranscriptResult(full_text, all_segments)
        logger.info(f"✅ Chunked транскрибация завершена: {len(all_segments)} сегментов")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка chunked транскрибации: {e}")
        return None

def analyze_video_with_chatgpt(transcript_text: str, duration: float) -> Optional[List[Dict]]:
    """Исправленный анализ видео с ChatGPT - всегда возвращает JSON"""
    try:
        logger.info("🤖 Анализируем видео с ChatGPT (исправленная версия)...")
        
        prompt = f"""
Проанализируй этот текст из видео длительностью {duration:.1f} секунд и найди лучшие моменты для создания коротких клипов.

Текст: "{transcript_text}"

ВАЖНО: Ответь ТОЛЬКО в формате JSON, без дополнительного текста. Даже если видео короткое или содержит мало информации, создай хотя бы 1-3 момента на основе имеющегося контента.

Для каждого момента укажи:
- start_time: время начала в секундах (число)
- end_time: время окончания в секундах (число)
- quote: точная цитата из текста
- reason: почему этот момент интересен
- viral_score: оценка вирусности от 1 до 100 (число)

Формат ответа (ТОЛЬКО JSON):
{{
  "highlights": [
    {{
      "start_time": 0.0,
      "end_time": {min(duration, 10.0)},
      "quote": "цитата из текста",
      "reason": "объяснение интереса",
      "viral_score": 75
    }}
  ]
}}

Если текст очень короткий, создай один момент с полным содержанием видео.
"""

        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты помощник для анализа видео. Отвечай ТОЛЬКО в формате JSON, без дополнительного текста или объяснений."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        logger.info(f"📝 Ответ ChatGPT: {result_text[:200]}...")
        
        # Очищаем ответ от возможного markdown
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
        
        # Парсим JSON ответ
        try:
            result = json.loads(result_text)
            highlights = result.get("highlights", [])
            
            # Валидация и исправление данных
            valid_highlights = []
            for highlight in highlights:
                try:
                    start_time = float(highlight.get("start_time", 0))
                    end_time = float(highlight.get("end_time", duration))
                    
                    # Исправляем некорректные тайминги
                    if start_time < 0:
                        start_time = 0
                    if end_time > duration:
                        end_time = duration
                    if end_time <= start_time:
                        end_time = min(start_time + 5.0, duration)
                    
                    valid_highlight = {
                        "start_time": start_time,
                        "end_time": end_time,
                        "quote": str(highlight.get("quote", transcript_text[:100])),
                        "reason": str(highlight.get("reason", "Интересный момент")),
                        "viral_score": int(highlight.get("viral_score", 75))
                    }
                    valid_highlights.append(valid_highlight)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Пропускаем некорректный highlight: {e}")
                    continue
            
            # Если нет валидных highlights, создаем один по умолчанию
            if not valid_highlights:
                logger.info("📝 Создаем highlight по умолчанию для короткого видео")
                valid_highlights = [{
                    "start_time": 0.0,
                    "end_time": min(duration, 10.0),
                    "quote": transcript_text[:100] if transcript_text else "Интересный контент",
                    "reason": "Основной контент видео",
                    "viral_score": 70
                }]
            
            logger.info(f"✅ Найдено {len(valid_highlights)} интересных моментов")
            for i, highlight in enumerate(valid_highlights, 1):
                logger.info(f"🎯 Момент {i}: {highlight['start_time']:.1f}-{highlight['end_time']:.1f}s, Score: {highlight['viral_score']}")
            
            return valid_highlights
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
            logger.error(f"📄 Проблемный ответ: {result_text}")
            
            # Fallback: создаем highlight по умолчанию
            logger.info("🔄 Создаем fallback highlight")
            return [{
                "start_time": 0.0,
                "end_time": min(duration, 10.0),
                "quote": transcript_text[:100] if transcript_text else "Контент видео",
                "reason": "Автоматически выбранный момент",
                "viral_score": 65
            }]
            
    except Exception as e:
        logger.error(f"❌ Ошибка анализа с ChatGPT: {e}")
        
        # Fallback: создаем highlight по умолчанию
        logger.info("🔄 Создаем emergency fallback highlight")
        return [{
            "start_time": 0.0,
            "end_time": min(duration, 10.0),
            "quote": transcript_text[:100] if transcript_text else "Видео контент",
            "reason": "Резервный выбор при ошибке анализа",
            "viral_score": 60
        }]

def generate_clip_with_opus_subtitles(video_path: str, start_time: float, end_time: float, 
                                    output_path: str, segments: List[Dict], 
                                    style: str = "modern", format_id: str = "9:16") -> bool:
    """Генерация клипа с субтитрами в стиле Opus.pro"""
    try:
        logger.info(f"🎬 Создаем Opus.pro клип: {start_time:.1f}-{end_time:.1f}s -> {output_path}")
        logger.info(f"📐 Формат: {format_id}, Стиль: {style}")
        
        # Генерируем субтитры в стиле Opus.pro
        logger.info("📝 Генерируем Opus.pro субтитры...")
        subtitle_filter = subtitle_system.generate_opus_subtitles(
            segments, start_time, end_time, style, format_id
        )
        
        logger.info(f"📝 Фильтр субтитров: {len(subtitle_filter)} символов")
        
        # Проверяем что фильтр не пустой
        if not subtitle_filter or len(subtitle_filter) < 10:
            logger.warning("⚠️ Фильтр субтитров пустой, используем fallback")
            subtitle_filter = subtitle_system._create_fallback_subtitle(format_id, style)
        
        # Получаем фильтр обрезки для выбранного формата
        crop_filter = format_manager.get_crop_filter(format_id)
        
        # Создаем финальный фильтр
        filter_complex = f"[0:v]{crop_filter},{subtitle_filter}[v]"
        
        # FFmpeg команда
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", str(start_time),
            "-t", str(end_time - start_time),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-preset", "fast", "-crf", "23",
            "-y", output_path
        ]
        
        logger.info("🔄 Запускаем FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"✅ Opus.pro клип создан: {output_path} ({file_size / 1024 / 1024:.1f} MB)")
            return True
        else:
            logger.error(f"❌ Ошибка создания клипа: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания клипа: {e}")
        return False

async def process_video_analysis(task_id: str, video_path: str):
    """Асинхронная обработка анализа видео"""
    try:
        logger.info(f"🎬 Начинаем анализ видео: {task_id}")
        
        # Обновляем статус
        tasks[task_id]["status"] = "extracting_audio"
        tasks[task_id]["progress"] = 10
        
        # Извлекаем аудио
        audio_path = f"audio/{task_id}.wav"
        if not extract_audio_from_video(video_path, audio_path):
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = "Ошибка извлечения аудио"
            return
        
        # Обновляем статус
        tasks[task_id]["status"] = "transcribing"
        tasks[task_id]["progress"] = 30
        
        # Транскрибируем аудио
        transcript = transcribe_audio_with_whisper(audio_path)
        if not transcript:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = "Ошибка транскрибации"
            return
        
        # Обновляем статус
        tasks[task_id]["status"] = "analyzing"
        tasks[task_id]["progress"] = 60
        
        # Получаем длительность видео
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip()) if result.returncode == 0 else 60.0
        
        # Анализируем с ChatGPT
        highlights = analyze_video_with_chatgpt(transcript.text, duration)
        if not highlights:
            tasks[task_id]["status"] = "error"
            tasks[task_id]["error"] = "Ошибка анализа с ChatGPT"
            return
        
        # Сохраняем результаты
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 100
        tasks[task_id]["transcript"] = transcript.text
        tasks[task_id]["segments"] = transcript.segments
        tasks[task_id]["highlights"] = highlights
        tasks[task_id]["duration"] = duration
        tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"✅ Анализ видео завершен: {task_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа видео {task_id}: {e}")
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
    finally:
        # Удаляем из активных задач
        active_tasks.discard(task_id)

async def process_clip_generation(generation_id: str, video_path: str, highlights: List[Dict], 
                                segments: List[Dict], style: str = "modern", format_id: str = "9:16"):
    """Асинхронная генерация клипов в стиле Opus.pro"""
    try:
        logger.info(f"🎬 Начинаем генерацию Opus.pro клипов: {generation_id}")
        logger.info(f"📐 Формат: {format_id}, Стиль: {style}")
        
        generation_tasks[generation_id]["status"] = "generating"
        generation_tasks[generation_id]["progress"] = 0
        
        created_clips = []
        total_clips = len(highlights)
        
        for i, highlight in enumerate(highlights):
            try:
                # Обновляем прогресс
                progress = int((i / total_clips) * 100)
                generation_tasks[generation_id]["progress"] = progress
                
                # Генерируем уникальное имя клипа
                clip_id = str(uuid.uuid4())
                output_path = f"clips/{clip_id}.mp4"
                
                # Создаем клип в стиле Opus.pro
                success = generate_clip_with_opus_subtitles(
                    video_path,
                    highlight["start_time"],
                    highlight["end_time"],
                    output_path,
                    segments,
                    style,
                    format_id
                )
                
                if success:
                    clip_info = {
                        "id": clip_id,
                        "start_time": highlight["start_time"],
                        "end_time": highlight["end_time"],
                        "duration": highlight["end_time"] - highlight["start_time"],
                        "quote": highlight["quote"],
                        "viral_score": highlight["viral_score"],
                        "file_path": output_path,
                        "file_size": os.path.getsize(output_path),
                        "format": format_id,
                        "style": style
                    }
                    created_clips.append(clip_info)
                    logger.info(f"✅ Opus.pro клип {i+1}/{total_clips} создан: {clip_id}")
                else:
                    logger.error(f"❌ Ошибка создания клипа {i+1}/{total_clips}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка создания клипа: {output_path}")
                logger.error(f"❌ Ошибка создания клипа: {e}")
        
        # Завершаем генерацию
        generation_tasks[generation_id]["status"] = "completed"
        generation_tasks[generation_id]["progress"] = 100
        generation_tasks[generation_id]["clips"] = created_clips
        generation_tasks[generation_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"✅ Генерация Opus.pro клипов завершена: {generation_id}, создано {len(created_clips)} клипов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации клипов {generation_id}: {e}")
        generation_tasks[generation_id]["status"] = "error"
        generation_tasks[generation_id]["error"] = str(e)

# API Endpoints

@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "version": "16.0.0-opus-clone",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(active_tasks),
        "queue_size": len(task_queue),
        "features": ["format_selection", "opus_subtitles", "advanced_grouping"]
    }

@app.get("/api/formats")
async def get_video_formats():
    """Получение доступных форматов видео"""
    return {
        "formats": format_manager.get_available_formats()
    }

@app.get("/api/styles")
async def get_subtitle_styles():
    """Получение доступных стилей субтитров"""
    return {
        "styles": [
            {
                "id": "modern",
                "name": "Modern",
                "description": "Clean white text with green highlights",
                "preview_color": "#00FF88"
            },
            {
                "id": "neon",
                "name": "Neon",
                "description": "Futuristic cyan glow effect",
                "preview_color": "#00FFFF"
            },
            {
                "id": "fire",
                "name": "Fire",
                "description": "Energetic orange highlights",
                "preview_color": "#FF6600"
            },
            {
                "id": "elegant",
                "name": "Elegant",
                "description": "Sophisticated gold accents",
                "preview_color": "#FFD700"
            }
        ]
    }

@app.post("/api/videos/analyze")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Загрузка и анализ видео"""
    try:
        # Генерируем уникальный ID
        task_id = str(uuid.uuid4())
        
        # Сохраняем файл
        file_path = f"uploads/{task_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"📤 Видео загружено: {task_id} ({len(content)} bytes)")
        
        # Создаем задачу
        tasks[task_id] = {
            "id": task_id,
            "filename": file.filename,
            "file_path": file_path,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.now().isoformat()
        }
        
        # Добавляем в активные задачи
        active_tasks.add(task_id)
        
        # Запускаем обработку в фоне
        background_tasks.add_task(process_video_analysis, task_id, file_path)
        
        return {"task_id": task_id, "status": "queued"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки видео: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{task_id}/status")
async def get_analysis_status(task_id: str):
    """Получение статуса анализа видео"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = tasks[task_id]
    
    # Базовая информация
    response = {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "created_at": task["created_at"]
    }
    
    # Добавляем результаты если готово
    if task["status"] == "completed":
        response.update({
            "transcript": task["transcript"],
            "highlights": task["highlights"],
            "duration": task["duration"],
            "completed_at": task["completed_at"]
        })
    elif task["status"] == "error":
        response["error"] = task["error"]
    
    return response

@app.post("/api/clips/generate")
async def generate_clips(background_tasks: BackgroundTasks, request: Dict[str, Any]):
    """Генерация клипов из анализированного видео"""
    try:
        task_id = request.get("task_id")
        style = request.get("style", "modern")
        format_id = request.get("format", "9:16")
        
        if not task_id or task_id not in tasks:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task = tasks[task_id]
        if task["status"] != "completed":
            raise HTTPException(status_code=400, detail="Analysis not completed")
        
        # Проверяем валидность формата
        available_formats = [f["id"] for f in format_manager.get_available_formats()]
        if format_id not in available_formats:
            format_id = "9:16"  # Default
        
        # Генерируем ID для генерации клипов
        generation_id = str(uuid.uuid4())
        
        # Создаем задачу генерации
        generation_tasks[generation_id] = {
            "id": generation_id,
            "task_id": task_id,
            "style": style,
            "format": format_id,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.now().isoformat()
        }
        
        # Запускаем генерацию в фоне
        background_tasks.add_task(
            process_clip_generation,
            generation_id,
            task["file_path"],
            task["highlights"],
            task["segments"],
            style,
            format_id
        )
        
        return {"generation_id": generation_id, "status": "queued", "format": format_id, "style": style}
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска генерации клипов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/clips/generation/{generation_id}/status")
async def get_generation_status(generation_id: str):
    """Получение статуса генерации клипов"""
    if generation_id not in generation_tasks:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    generation = generation_tasks[generation_id]
    
    # Базовая информация
    response = {
        "generation_id": generation_id,
        "status": generation["status"],
        "progress": generation["progress"],
        "created_at": generation["created_at"],
        "format": generation.get("format", "9:16"),
        "style": generation.get("style", "modern")
    }
    
    # Добавляем результаты если готово
    if generation["status"] == "completed":
        response.update({
            "clips": generation["clips"],
            "completed_at": generation["completed_at"]
        })
    elif generation["status"] == "error":
        response["error"] = generation["error"]
    
    return response

@app.get("/api/clips/{clip_id}/download")
async def download_clip(clip_id: str):
    """Скачивание готового клипа"""
    file_path = f"clips/{clip_id}.mp4"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=f"clip_{clip_id}.mp4"
    )

# Статические файлы
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    logger.info("🚀 AgentFlow AI Clips v16.0 - Complete Opus.pro Clone started!")
    uvicorn.run(app, host="0.0.0.0", port=10000)

