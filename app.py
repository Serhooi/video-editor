"""
AgentFlow Video Platform API - Professional Edition
Полноценная видеоплатформа с функционалом Opus.pro + Canva

Основные модули:
1. AI Video Analysis - анализ и транскрибация
2. AI Clips Generator - автоматическая нарезка
3. Professional Video Editor - полноценный редактор
4. Caption Styles - стили кепшенов
5. Transitions Library - библиотека переходов
6. Music Library - музыкальная библиотека
7. Rendering Engine - движок рендеринга
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import uuid
import json
import asyncio
import tempfile
import shutil
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgentFlow Video Platform API",
    description="Professional video editing platform with AI capabilities",
    version="2.0.0"
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные для хранения состояния
tasks_storage = {}
projects_storage = {}
templates_storage = {}
music_library = {}

# ==================== МОДЕЛИ ДАННЫХ ====================

class VideoAnalysisRequest(BaseModel):
    video_id: str
    ai_model: str = "gpt-4"
    language: str = "ru"
    extract_highlights: bool = True
    generate_captions: bool = True

class TranscriptEdit(BaseModel):
    word_id: str
    new_text: str
    start_time: float
    end_time: float

class ClipGenerationRequest(BaseModel):
    video_id: str
    clip_model: str = "viral"
    genre: str = "general"
    length_range: tuple = (30, 90)
    custom_prompt: Optional[str] = None
    max_clips: int = 10

class CaptionStyle(BaseModel):
    style_id: str
    name: str
    font_family: str
    font_size: int
    color: str
    background_color: Optional[str] = None
    animation: str = "none"
    position: str = "bottom"
    outline: bool = False
    shadow: bool = False

class Transition(BaseModel):
    transition_id: str
    name: str
    type: str  # "fade", "zoom", "slide", "wipe"
    duration: float = 0.5
    easing: str = "ease-in-out"

class MusicTrack(BaseModel):
    track_id: str
    name: str
    artist: str
    duration: float
    genre: str
    mood: str
    bpm: int
    copyright_free: bool = True
    file_url: str

class EditorProject(BaseModel):
    project_id: str
    name: str
    timeline: List[Dict]
    settings: Dict
    created_at: datetime
    updated_at: datetime

class RenderSettings(BaseModel):
    resolution: str = "1920x1080"
    fps: int = 30
    format: str = "mp4"
    quality: str = "high"
    aspect_ratio: str = "16:9"

# ==================== ИНИЦИАЛИЗАЦИЯ БИБЛИОТЕК ====================

def initialize_caption_styles():
    """Инициализация стилей кепшенов"""
    styles = {
        "karaoke": CaptionStyle(
            style_id="karaoke",
            name="Karaoke",
            font_family="Arial Black",
            font_size=48,
            color="#FFFFFF",
            background_color="#000000",
            animation="highlight",
            position="bottom",
            outline=True
        ),
        "beasty": CaptionStyle(
            style_id="beasty",
            name="Beasty",
            font_family="Impact",
            font_size=52,
            color="#FF6B35",
            animation="bounce",
            position="center",
            outline=True,
            shadow=True
        ),
        "deep_diver": CaptionStyle(
            style_id="deep_diver",
            name="Deep Diver",
            font_family="Roboto",
            font_size=44,
            color="#00D4FF",
            background_color="rgba(0,0,0,0.7)",
            animation="fade",
            position="bottom"
        ),
        "youshael": CaptionStyle(
            style_id="youshael",
            name="Youshael",
            font_family="Montserrat",
            font_size=46,
            color="#FFD700",
            animation="typewriter",
            position="top",
            outline=True
        )
    }
    return styles

def initialize_transitions():
    """Инициализация библиотеки переходов"""
    transitions = {
        "cross_fade": Transition(
            transition_id="cross_fade",
            name="Cross Fade",
            type="fade",
            duration=0.5
        ),
        "cross_zoom": Transition(
            transition_id="cross_zoom",
            name="Cross Zoom",
            type="zoom",
            duration=0.8
        ),
        "zoom_in": Transition(
            transition_id="zoom_in",
            name="Zoom In",
            type="zoom",
            duration=0.6
        ),
        "zoom_out": Transition(
            transition_id="zoom_out",
            name="Zoom Out",
            type="zoom",
            duration=0.6
        ),
        "fade_in": Transition(
            transition_id="fade_in",
            name="Fade In",
            type="fade",
            duration=0.4
        ),
        "fade_out": Transition(
            transition_id="fade_out",
            name="Fade Out",
            type="fade",
            duration=0.4
        )
    }
    return transitions

def initialize_music_library():
    """Инициализация музыкальной библиотеки"""
    tracks = {
        "magnetic": MusicTrack(
            track_id="magnetic",
            name="Magnetic",
            artist="AudioJungle",
            duration=180.0,
            genre="Electronic",
            mood="Energetic",
            bpm=128,
            file_url="/music/magnetic.mp3"
        ),
        "cruising": MusicTrack(
            track_id="cruising",
            name="Cruising",
            artist="AudioJungle",
            duration=165.0,
            genre="Pop",
            mood="Upbeat",
            bpm=120,
            file_url="/music/cruising.mp3"
        ),
        "moonlight": MusicTrack(
            track_id="moonlight",
            name="Moonlight",
            artist="AudioJungle",
            duration=200.0,
            genre="Ambient",
            mood="Calm",
            bpm=85,
            file_url="/music/moonlight.mp3"
        ),
        "sober": MusicTrack(
            track_id="sober",
            name="SOBER",
            artist="AudioJungle",
            duration=145.0,
            genre="Hip-Hop",
            mood="Serious",
            bpm=95,
            file_url="/music/sober.mp3"
        )
    }
    return tracks

# Инициализация библиотек
caption_styles = initialize_caption_styles()
transitions_library = initialize_transitions()
music_library = initialize_music_library()

# ==================== ОСНОВНЫЕ ЭНДПОИНТЫ ====================

@app.get("/health")
async def health_check():
    """Проверка состояния API"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "modules": {
            "ai_analysis": True,
            "video_editor": True,
            "caption_styles": len(caption_styles),
            "transitions": len(transitions_library),
            "music_tracks": len(music_library)
        },
        "timestamp": datetime.now().isoformat()
    }

# ==================== AI АНАЛИЗ ВИДЕО ====================

@app.post("/api/videos/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ai_model: str = Form("gpt-4"),
    language: str = Form("ru"),
    extract_highlights: bool = Form(True),
    generate_captions: bool = Form(True)
):
    """Полный AI анализ видео с транскрибацией и поиском лучших моментов"""
    
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат видео")
    
    task_id = str(uuid.uuid4())
    
    # Сохранение файла
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Инициализация задачи
    tasks_storage[task_id] = {
        "status": "processing",
        "progress": 0,
        "file_path": file_path,
        "filename": file.filename,
        "ai_model": ai_model,
        "language": language,
        "extract_highlights": extract_highlights,
        "generate_captions": generate_captions,
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    # Запуск фоновой обработки
    background_tasks.add_task(process_video_analysis, task_id)
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Видео отправлено на анализ"
    }

async def process_video_analysis(task_id: str):
    """Фоновая обработка анализа видео"""
    try:
        task = tasks_storage[task_id]
        
        # Симуляция обработки с прогрессом
        stages = [
            ("Извлечение аудио", 20),
            ("Транскрибация речи", 40),
            ("AI анализ контента", 60),
            ("Поиск лучших моментов", 80),
            ("Генерация кепшенов", 90),
            ("Финализация", 100)
        ]
        
        for stage_name, progress in stages:
            task["status"] = f"processing: {stage_name}"
            task["progress"] = progress
            await asyncio.sleep(2)  # Симуляция обработки
        
        # Симуляция результата анализа
        result = {
            "video_info": {
                "duration": 180.5,
                "resolution": "1920x1080",
                "fps": 30,
                "format": "mp4"
            },
            "transcript": {
                "language": task["language"],
                "confidence": 0.95,
                "words": [
                    {
                        "id": "word_1",
                        "text": "Добро",
                        "start_time": 0.0,
                        "end_time": 0.5,
                        "confidence": 0.98
                    },
                    {
                        "id": "word_2", 
                        "text": "пожаловать",
                        "start_time": 0.5,
                        "end_time": 1.2,
                        "confidence": 0.97
                    },
                    {
                        "id": "word_3",
                        "text": "в",
                        "start_time": 1.2,
                        "end_time": 1.4,
                        "confidence": 0.99
                    },
                    {
                        "id": "word_4",
                        "text": "наш",
                        "start_time": 1.4,
                        "end_time": 1.8,
                        "confidence": 0.96
                    },
                    {
                        "id": "word_5",
                        "text": "новый",
                        "start_time": 1.8,
                        "end_time": 2.3,
                        "confidence": 0.98
                    },
                    {
                        "id": "word_6",
                        "text": "дом!",
                        "start_time": 2.3,
                        "end_time": 2.8,
                        "confidence": 0.99
                    }
                ],
                "segments": [
                    {
                        "start_time": 0.0,
                        "end_time": 2.8,
                        "text": "Добро пожаловать в наш новый дом!"
                    }
                ]
            },
            "ai_analysis": {
                "summary": "Видео-тур по новому дому с презентацией основных комнат и особенностей",
                "key_topics": ["недвижимость", "дом", "тур", "презентация"],
                "sentiment": "positive",
                "energy_level": "high"
            },
            "highlights": [
                {
                    "clip_id": "highlight_1",
                    "start_time": 0.0,
                    "end_time": 15.0,
                    "title": "Вступление и приветствие",
                    "description": "Энергичное начало с приветствием",
                    "score": 87,
                    "categories": {
                        "hook": 90,
                        "flow": 85,
                        "value": 80,
                        "trend": 92
                    },
                    "suggested_caption_style": "beasty"
                },
                {
                    "clip_id": "highlight_2", 
                    "start_time": 45.0,
                    "end_time": 75.0,
                    "title": "Главная спальня",
                    "description": "Презентация главной спальни с особенностями",
                    "score": 92,
                    "categories": {
                        "hook": 85,
                        "flow": 95,
                        "value": 95,
                        "trend": 88
                    },
                    "suggested_caption_style": "deep_diver"
                }
            ]
        }
        
        task["status"] = "completed"
        task["progress"] = 100
        task["result"] = result
        task["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"Ошибка при анализе видео {task_id}: {str(e)}")
        task["status"] = "failed"
        task["error"] = str(e)

@app.get("/api/videos/{task_id}/status")
async def get_analysis_status(task_id: str):
    """Получение статуса анализа видео"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "created_at": task["created_at"],
        "result": task["result"] if task["status"] == "completed" else None,
        "error": task["error"] if task["status"] == "failed" else None
    }

@app.get("/api/videos/{task_id}/transcript")
async def get_transcript(task_id: str):
    """Получение транскрипта видео"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Анализ еще не завершен")
    
    return task["result"]["transcript"]

@app.post("/api/videos/{task_id}/transcript/edit")
async def edit_transcript(task_id: str, edits: List[TranscriptEdit]):
    """Редактирование транскрипта"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Анализ еще не завершен")
    
    # Применение изменений к транскрипту
    transcript = task["result"]["transcript"]
    for edit in edits:
        for word in transcript["words"]:
            if word["id"] == edit.word_id:
                word["text"] = edit.new_text
                word["start_time"] = edit.start_time
                word["end_time"] = edit.end_time
                break
    
    # Пересборка сегментов
    # Здесь должна быть логика пересборки сегментов на основе измененных слов
    
    return {"message": "Транскрипт обновлен", "transcript": transcript}

# ==================== AI ГЕНЕРАЦИЯ КЛИПОВ ====================

@app.post("/api/clips/generate")
async def generate_clips(
    background_tasks: BackgroundTasks,
    request: ClipGenerationRequest
):
    """Генерация AI клипов из видео"""
    
    if request.video_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    
    video_task = tasks_storage[request.video_id]
    if video_task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Анализ видео еще не завершен")
    
    clip_task_id = str(uuid.uuid4())
    
    tasks_storage[clip_task_id] = {
        "status": "processing",
        "progress": 0,
        "video_id": request.video_id,
        "clip_model": request.clip_model,
        "genre": request.genre,
        "length_range": request.length_range,
        "custom_prompt": request.custom_prompt,
        "max_clips": request.max_clips,
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(process_clip_generation, clip_task_id)
    
    return {
        "task_id": clip_task_id,
        "status": "processing",
        "message": "Генерация клипов запущена"
    }

async def process_clip_generation(task_id: str):
    """Фоновая генерация клипов"""
    try:
        task = tasks_storage[task_id]
        video_task = tasks_storage[task["video_id"]]
        highlights = video_task["result"]["highlights"]
        
        # Симуляция генерации клипов
        stages = [
            ("Анализ лучших моментов", 25),
            ("Применение AI модели", 50),
            ("Генерация клипов", 75),
            ("Финализация", 100)
        ]
        
        for stage_name, progress in stages:
            task["status"] = f"processing: {stage_name}"
            task["progress"] = progress
            await asyncio.sleep(1.5)
        
        # Генерация результата на основе highlights
        clips = []
        for i, highlight in enumerate(highlights[:task["max_clips"]]):
            clip = {
                "clip_id": f"clip_{i+1}",
                "title": highlight["title"],
                "description": highlight["description"],
                "start_time": highlight["start_time"],
                "end_time": highlight["end_time"],
                "duration": highlight["end_time"] - highlight["start_time"],
                "score": highlight["score"],
                "categories": highlight["categories"],
                "suggested_style": highlight["suggested_caption_style"],
                "preview_url": f"/api/clips/{task_id}/preview/{i+1}",
                "download_url": f"/api/clips/{task_id}/download/{i+1}",
                "formats": ["mp4", "mov", "gif"],
                "resolutions": ["1080p", "720p", "480p"],
                "aspect_ratios": ["16:9", "9:16", "1:1"]
            }
            clips.append(clip)
        
        result = {
            "clips": clips,
            "total_clips": len(clips),
            "generation_settings": {
                "model": task["clip_model"],
                "genre": task["genre"],
                "length_range": task["length_range"]
            }
        }
        
        task["status"] = "completed"
        task["progress"] = 100
        task["result"] = result
        task["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"Ошибка при генерации клипов {task_id}: {str(e)}")
        task["status"] = "failed"
        task["error"] = str(e)

@app.get("/api/clips/{task_id}/status")
async def get_clips_status(task_id: str):
    """Получение статуса генерации клипов"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return tasks_storage[task_id]

# ==================== СТИЛИ КЕПШЕНОВ ====================

@app.get("/api/captions/styles")
async def get_caption_styles():
    """Получение всех стилей кепшенов"""
    return {
        "styles": list(caption_styles.values()),
        "total": len(caption_styles)
    }

@app.get("/api/captions/styles/{style_id}")
async def get_caption_style(style_id: str):
    """Получение конкретного стиля кепшенов"""
    if style_id not in caption_styles:
        raise HTTPException(status_code=404, detail="Стиль не найден")
    
    return caption_styles[style_id]

@app.post("/api/captions/styles")
async def create_caption_style(style: CaptionStyle):
    """Создание нового стиля кепшенов"""
    caption_styles[style.style_id] = style
    return {"message": "Стиль создан", "style": style}

# ==================== БИБЛИОТЕКА ПЕРЕХОДОВ ====================

@app.get("/api/transitions")
async def get_transitions():
    """Получение всех переходов"""
    return {
        "transitions": list(transitions_library.values()),
        "categories": {
            "fade": [t for t in transitions_library.values() if t.type == "fade"],
            "zoom": [t for t in transitions_library.values() if t.type == "zoom"],
            "slide": [t for t in transitions_library.values() if t.type == "slide"],
            "wipe": [t for t in transitions_library.values() if t.type == "wipe"]
        }
    }

@app.get("/api/transitions/{transition_id}")
async def get_transition(transition_id: str):
    """Получение конкретного перехода"""
    if transition_id not in transitions_library:
        raise HTTPException(status_code=404, detail="Переход не найден")
    
    return transitions_library[transition_id]

# ==================== МУЗЫКАЛЬНАЯ БИБЛИОТЕКА ====================

@app.get("/api/music")
async def get_music_library(
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    bpm_min: Optional[int] = None,
    bpm_max: Optional[int] = None
):
    """Получение музыкальной библиотеки с фильтрами"""
    tracks = list(music_library.values())
    
    # Применение фильтров
    if genre:
        tracks = [t for t in tracks if t.genre.lower() == genre.lower()]
    if mood:
        tracks = [t for t in tracks if t.mood.lower() == mood.lower()]
    if bpm_min:
        tracks = [t for t in tracks if t.bpm >= bpm_min]
    if bpm_max:
        tracks = [t for t in tracks if t.bpm <= bpm_max]
    
    return {
        "tracks": tracks,
        "total": len(tracks),
        "genres": list(set(t.genre for t in music_library.values())),
        "moods": list(set(t.mood for t in music_library.values()))
    }

@app.get("/api/music/{track_id}")
async def get_music_track(track_id: str):
    """Получение конкретного музыкального трека"""
    if track_id not in music_library:
        raise HTTPException(status_code=404, detail="Трек не найден")
    
    return music_library[track_id]

@app.get("/api/music/{track_id}/preview")
async def preview_music_track(track_id: str):
    """Превью музыкального трека (30 секунд)"""
    if track_id not in music_library:
        raise HTTPException(status_code=404, detail="Трек не найден")
    
    # Здесь должна быть логика генерации превью
    return {"preview_url": f"/music/previews/{track_id}_preview.mp3"}

# ==================== ПРОФЕССИОНАЛЬНЫЙ ВИДЕОРЕДАКТОР ====================

@app.post("/api/editor/projects")
async def create_editor_project(
    name: str = Form(...),
    template: Optional[str] = Form(None)
):
    """Создание нового проекта в видеоредакторе"""
    
    project_id = str(uuid.uuid4())
    
    # Базовые настройки проекта
    project = {
        "project_id": project_id,
        "name": name,
        "template": template,
        "timeline": {
            "tracks": [
                {"id": "video_1", "type": "video", "clips": []},
                {"id": "audio_1", "type": "audio", "clips": []},
                {"id": "text_1", "type": "text", "clips": []},
                {"id": "effects_1", "type": "effects", "clips": []}
            ],
            "duration": 0,
            "fps": 30
        },
        "settings": {
            "resolution": "1920x1080",
            "fps": 30,
            "aspect_ratio": "16:9",
            "background_color": "#000000"
        },
        "assets": {
            "videos": [],
            "images": [],
            "audio": [],
            "fonts": []
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    projects_storage[project_id] = project
    
    return {
        "project_id": project_id,
        "message": "Проект создан",
        "project": project
    }

@app.get("/api/editor/projects/{project_id}")
async def get_editor_project(project_id: str):
    """Получение проекта видеоредактора"""
    if project_id not in projects_storage:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    return projects_storage[project_id]

@app.put("/api/editor/projects/{project_id}")
async def update_editor_project(project_id: str, updates: Dict[str, Any]):
    """Обновление проекта видеоредактора"""
    if project_id not in projects_storage:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    project = projects_storage[project_id]
    
    # Обновление полей проекта
    for key, value in updates.items():
        if key in project:
            project[key] = value
    
    project["updated_at"] = datetime.now().isoformat()
    
    return {
        "message": "Проект обновлен",
        "project": project
    }

@app.post("/api/editor/projects/{project_id}/assets")
async def upload_project_asset(
    project_id: str,
    file: UploadFile = File(...),
    asset_type: str = Form(...)
):
    """Загрузка ассета в проект"""
    if project_id not in projects_storage:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    # Сохранение файла
    asset_id = str(uuid.uuid4())
    file_extension = file.filename.split('.')[-1]
    filename = f"{asset_id}.{file_extension}"
    
    # Здесь должна быть логика сохранения файла
    asset = {
        "asset_id": asset_id,
        "filename": file.filename,
        "type": asset_type,
        "size": 0,  # Размер файла
        "duration": 0,  # Для видео/аудио
        "url": f"/assets/{filename}",
        "uploaded_at": datetime.now().isoformat()
    }
    
    project = projects_storage[project_id]
    if asset_type not in project["assets"]:
        project["assets"][asset_type] = []
    
    project["assets"][asset_type].append(asset)
    project["updated_at"] = datetime.now().isoformat()
    
    return {
        "message": "Ассет загружен",
        "asset": asset
    }

@app.post("/api/editor/projects/{project_id}/render")
async def render_project(
    background_tasks: BackgroundTasks,
    project_id: str,
    settings: RenderSettings
):
    """Рендеринг проекта видеоредактора"""
    if project_id not in projects_storage:
        raise HTTPException(status_code=404, detail="Проект не найден")
    
    render_task_id = str(uuid.uuid4())
    
    tasks_storage[render_task_id] = {
        "status": "processing",
        "progress": 0,
        "project_id": project_id,
        "render_settings": settings.dict(),
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(process_project_render, render_task_id)
    
    return {
        "task_id": render_task_id,
        "status": "processing",
        "message": "Рендеринг запущен"
    }

async def process_project_render(task_id: str):
    """Фоновый рендеринг проекта"""
    try:
        task = tasks_storage[task_id]
        
        # Симуляция рендеринга
        stages = [
            ("Подготовка ассетов", 20),
            ("Обработка видео", 40),
            ("Применение эффектов", 60),
            ("Наложение аудио", 80),
            ("Финальный рендеринг", 100)
        ]
        
        for stage_name, progress in stages:
            task["status"] = f"processing: {stage_name}"
            task["progress"] = progress
            await asyncio.sleep(3)  # Симуляция времени рендеринга
        
        # Результат рендеринга
        result = {
            "output_file": f"/renders/{task_id}.mp4",
            "duration": 120.5,
            "size_mb": 45.2,
            "resolution": task["render_settings"]["resolution"],
            "fps": task["render_settings"]["fps"],
            "format": task["render_settings"]["format"],
            "download_url": f"/api/renders/{task_id}/download"
        }
        
        task["status"] = "completed"
        task["progress"] = 100
        task["result"] = result
        task["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"Ошибка при рендеринге {task_id}: {str(e)}")
        task["status"] = "failed"
        task["error"] = str(e)

@app.get("/api/editor/renders/{task_id}/status")
async def get_render_status(task_id: str):
    """Получение статуса рендеринга"""
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return tasks_storage[task_id]

# ==================== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ====================

@app.get("/api/templates")
async def get_project_templates():
    """Получение шаблонов проектов"""
    templates = {
        "real_estate": {
            "name": "Недвижимость",
            "description": "Шаблон для презентации недвижимости",
            "duration": 60,
            "tracks": 4,
            "preset_styles": ["professional", "modern"]
        },
        "social_media": {
            "name": "Социальные сети",
            "description": "Шаблон для контента в соцсетях",
            "duration": 30,
            "tracks": 3,
            "preset_styles": ["viral", "trendy"]
        },
        "presentation": {
            "name": "Презентация",
            "description": "Шаблон для бизнес-презентаций",
            "duration": 180,
            "tracks": 5,
            "preset_styles": ["corporate", "clean"]
        }
    }
    
    return {"templates": templates}

@app.get("/api/stats")
async def get_platform_stats():
    """Статистика платформы"""
    return {
        "total_videos_processed": len([t for t in tasks_storage.values() if "video_id" in t]),
        "total_clips_generated": len([t for t in tasks_storage.values() if "clip_model" in t]),
        "total_projects": len(projects_storage),
        "active_tasks": len([t for t in tasks_storage.values() if t["status"] == "processing"]),
        "caption_styles": len(caption_styles),
        "transitions": len(transitions_library),
        "music_tracks": len(music_library)
    }

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

