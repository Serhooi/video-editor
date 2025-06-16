from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import uuid
from typing import Optional, Dict, Any
import json
from datetime import datetime

app = FastAPI(
    title="AgentFlow Video Highlight API",
    description="API для анализа видео и создания хайлайтов",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище задач (в продакшене используйте базу данных)
tasks_storage: Dict[str, Dict[str, Any]] = {}

# Добавляем эндпоинт для проверки здоровья
@app.get("/health")
def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "ok",
        "service": "video-highlight-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
def root():
    """Корневой эндпоинт"""
    return {
        "message": "AgentFlow Video Highlight API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.post("/api/videos/analyze")
async def analyze_video(
    background_tasks: BackgroundTasks,
    video_file: UploadFile = File(...),
    duration: Optional[int] = Form(30),
    style: Optional[str] = Form("dynamic")
):
    """
    Анализ видео и создание хайлайтов
    """
    try:
        # Генерируем уникальный ID задачи
        task_id = str(uuid.uuid4())
        
        # Проверяем тип файла
        if not video_file.content_type or not video_file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="Файл должен быть видео")
        
        # Сохраняем информацию о задаче
        tasks_storage[task_id] = {
            "id": task_id,
            "status": "processing",
            "filename": video_file.filename,
            "duration": duration,
            "style": style,
            "created_at": datetime.now().isoformat(),
            "progress": 0
        }
        
        # Запускаем обработку в фоне
        background_tasks.add_task(process_video, task_id, video_file, duration, style)
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Видео принято в обработку"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке видео: {str(e)}")

@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """
    Получение статуса задачи
    """
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return tasks_storage[task_id]

@app.get("/api/videos/{task_id}/highlights")
def get_video_highlights(task_id: str):
    """
    Получение результатов анализа видео
    """
    if task_id not in tasks_storage:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks_storage[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Обработка видео еще не завершена")
    
    return task.get("results", {})

async def process_video(task_id: str, video_file: UploadFile, duration: int, style: str):
    """
    Фоновая обработка видео (заглушка)
    """
    try:
        # Обновляем прогресс
        tasks_storage[task_id]["progress"] = 25
        
        # Имитируем обработку видео
        import asyncio
        await asyncio.sleep(2)
        
        tasks_storage[task_id]["progress"] = 50
        await asyncio.sleep(2)
        
        tasks_storage[task_id]["progress"] = 75
        await asyncio.sleep(2)
        
        # Завершаем обработку
        tasks_storage[task_id].update({
            "status": "completed",
            "progress": 100,
            "completed_at": datetime.now().isoformat(),
            "results": {
                "highlights": [
                    {
                        "id": "highlight_1",
                        "start_time": 10.5,
                        "end_time": 25.3,
                        "description": "Интересный момент в видео",
                        "score": 0.85
                    },
                    {
                        "id": "highlight_2", 
                        "start_time": 45.2,
                        "end_time": 62.1,
                        "description": "Ключевая сцена",
                        "score": 0.92
                    }
                ],
                "summary": f"Создано 2 хайлайта длительностью {duration} секунд в стиле {style}",
                "total_highlights": 2,
                "processing_time": "6 секунд"
            }
        })
        
    except Exception as e:
        tasks_storage[task_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

