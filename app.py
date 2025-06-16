"""
Прототип системы для выделения лучших моментов из видео
и создания коротких клипов (аналог Opus.pro)

Основные функции:
1. Анализ видео для поиска интересных моментов
2. Транскрибация речи и определение ключевых фраз
3. Нарезка видео на короткие клипы
4. Добавление субтитров и эффектов

Автор: Manus AI
Дата: Июнь 2025
"""

import os
import sys
import time
import json
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Union

# Необходимые библиотеки (требуется установка)
try:
    import numpy as np
    import cv2
    import torch
    import whisper
    import moviepy.editor as mp
    from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
    from pydantic import BaseModel
    from transformers import pipeline, AutoProcessor, AutoModel
except ImportError:
    print("Необходимо установить зависимости:")
    print("pip install numpy opencv-python torch whisper moviepy fastapi uvicorn transformers")
    sys.exit(1)

# Проверка доступности GPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Используется устройство: {DEVICE}")

# Конфигурация
OUTPUT_DIR = "output"
TEMP_DIR = "temp"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

class VideoAnalyzer:
    """
    Класс для анализа видео и выделения интересных моментов
    """
    
    def __init__(self):
        """Инициализация моделей и ресурсов"""
        print("Инициализация VideoAnalyzer...")
        
        # Загрузка модели для транскрибации речи
        self.whisper_model = whisper.load_model("base", device=DEVICE)
        
        # Загрузка CLIP для анализа видео
        self.clip_processor = AutoProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_model = AutoModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE)
        
        # Загрузка модели для анализа эмоций
        self.emotion_classifier = pipeline("text-classification", 
                                          model="j-hartmann/emotion-english-distilroberta-base", 
                                          device=0 if DEVICE == "cuda" else -1)
        
        print("VideoAnalyzer инициализирован")
    
    def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        Полный анализ видео для выделения интересных моментов
        
        Args:
            video_path: Путь к видеофайлу
            
        Returns:
            Dict с результатами анализа:
            - segments: список сегментов с временными метками
            - transcript: полная транскрипция
            - highlights: список лучших моментов
        """
        print(f"Анализ видео: {video_path}")
        
        # Извлечение аудио из видео
        audio_path = self._extract_audio(video_path)
        
        # Транскрибация речи
        transcript_result = self._transcribe_audio(audio_path)
        
        # Анализ видеокадров
        frame_analysis = self._analyze_frames(video_path)
        
        # Определение ключевых моментов на основе аудио и видео
        highlights = self._detect_highlights(transcript_result, frame_analysis)
        
        # Оценка "вирусности" каждого момента
        scored_highlights = self._score_virality(highlights)
        
        # Формирование итогового результата
        result = {
            "video_path": video_path,
            "duration": self._get_video_duration(video_path),
            "transcript": transcript_result,
            "frame_analysis": frame_analysis,
            "highlights": scored_highlights
        }
        
        print(f"Анализ завершен, найдено {len(scored_highlights)} интересных моментов")
        return result
    
    def _extract_audio(self, video_path: str) -> str:
        """Извлечение аудио из видео"""
        print("Извлечение аудио...")
        
        audio_path = os.path.join(TEMP_DIR, f"{Path(video_path).stem}_audio.wav")
        
        # Используем MoviePy для извлечения аудио
        video = mp.VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path, codec='pcm_s16le')
        
        print(f"Аудио извлечено: {audio_path}")
        return audio_path
    
    def _transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Транскрибация аудио с помощью Whisper"""
        print("Транскрибация аудио...")
        
        # Транскрибация с помощью Whisper
        result = self.whisper_model.transcribe(audio_path)
        
        # Анализ эмоций для каждого сегмента
        for segment in result["segments"]:
            # Анализ эмоций в тексте
            emotion_result = self.emotion_classifier(segment["text"])
            segment["emotion"] = emotion_result[0]["label"]
            segment["emotion_score"] = emotion_result[0]["score"]
        
        print(f"Транскрибация завершена: {len(result['segments'])} сегментов")
        return result
    
    def _analyze_frames(self, video_path: str, sample_rate: int = 1) -> List[Dict[str, Any]]:
        """
        Анализ ключевых кадров видео
        
        Args:
            video_path: Путь к видео
            sample_rate: Частота выборки кадров (1 = каждый кадр)
            
        Returns:
            Список результатов анализа кадров
        """
        print(f"Анализ видеокадров (частота выборки: {sample_rate})...")
        
        results = []
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Для демонстрации анализируем только часть кадров
        frames_to_analyze = min(100, frame_count)
        step = max(1, frame_count // frames_to_analyze)
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % step == 0:
                # Конвертация кадра для CLIP
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Анализ кадра с помощью CLIP
                inputs = self.clip_processor(images=frame_rgb, return_tensors="pt").to(DEVICE)
                
                with torch.no_grad():
                    image_features = self.clip_model.get_image_features(**inputs)
                    
                # Нормализация признаков
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
                # Определение времени кадра
                timestamp = frame_idx / fps
                
                # Сохранение результатов
                results.append({
                    "frame_idx": frame_idx,
                    "timestamp": timestamp,
                    "features": image_features.cpu().numpy().tolist()[0][:10],  # Сохраняем только первые 10 признаков для краткости
                    "time_str": self._format_timestamp(timestamp)
                })
                
                if len(results) % 10 == 0:
                    print(f"Проанализировано {len(results)} кадров...")
            
            frame_idx += 1
        
        cap.release()
        print(f"Анализ кадров завершен: {len(results)} кадров")
        return results
    
    def _detect_highlights(self, transcript: Dict[str, Any], frame_analysis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Определение ключевых моментов на основе аудио и видео
        
        Стратегия:
        1. Ищем сегменты с высокой эмоциональной окраской
        2. Ищем ключевые фразы и утверждения
        3. Ищем визуально интересные моменты
        4. Комбинируем результаты
        """
        print("Определение ключевых моментов...")
        
        highlights = []
        
        # Анализ транскрипции для поиска интересных сегментов
        for segment in transcript["segments"]:
            is_highlight = False
            highlight_reasons = []
            
            # Проверка на эмоциональную окраску
            if segment["emotion"] in ["joy", "surprise", "anger"] and segment["emotion_score"] > 0.7:
                is_highlight = True
                highlight_reasons.append(f"Высокая эмоциональная окраска: {segment['emotion']} ({segment['emotion_score']:.2f})")
            
            # Проверка на ключевые фразы
            key_phrases = ["amazing", "incredible", "best", "worst", "never", "always", "must", "should", "important"]
            for phrase in key_phrases:
                if phrase in segment["text"].lower():
                    is_highlight = True
                    highlight_reasons.append(f"Содержит ключевую фразу: '{phrase}'")
            
            # Проверка на длину сегмента (короткие и емкие фразы часто интересны)
            word_count = len(segment["text"].split())
            if 5 <= word_count <= 15:
                is_highlight = True
                highlight_reasons.append(f"Оптимальная длина фразы: {word_count} слов")
            
            if is_highlight:
                # Находим ближайший проанализированный кадр
                nearest_frame = min(frame_analysis, 
                                   key=lambda x: abs(x["timestamp"] - segment["start"]))
                
                highlights.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "emotion": segment["emotion"],
                    "emotion_score": segment["emotion_score"],
                    "reasons": highlight_reasons,
                    "nearest_frame_idx": nearest_frame["frame_idx"],
                    "time_str": self._format_timestamp(segment["start"])
                })
        
        # Объединение близких моментов
        merged_highlights = self._merge_close_highlights(highlights)
        
        print(f"Определено {len(merged_highlights)} ключевых моментов")
        return merged_highlights
    
    def _merge_close_highlights(self, highlights: List[Dict[str, Any]], max_gap: float = 2.0) -> List[Dict[str, Any]]:
        """Объединение близких моментов"""
        if not highlights:
            return []
        
        # Сортировка по времени начала
        sorted_highlights = sorted(highlights, key=lambda x: x["start"])
        
        merged = []
        current = sorted_highlights[0]
        
        for next_highlight in sorted_highlights[1:]:
            # Если следующий момент начинается вскоре после окончания текущего
            if next_highlight["start"] - current["end"] <= max_gap:
                # Объединяем моменты
                current["end"] = next_highlight["end"]
                current["text"] += " " + next_highlight["text"]
                current["reasons"].extend(next_highlight["reasons"])
            else:
                # Добавляем текущий момент и переходим к следующему
                merged.append(current)
                current = next_highlight
        
        # Добавляем последний момент
        merged.append(current)
        
        return merged
    
    def _score_virality(self, highlights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Оценка 'вирусности' каждого момента"""
        print("Оценка вирусности моментов...")
        
        for highlight in highlights:
            # Базовая оценка
            score = 50
            
            # Факторы, влияющие на оценку
            
            # 1. Эмоциональная окраска
            emotion_bonus = {
                "joy": 15,
                "surprise": 20,
                "anger": 10,
                "fear": 5,
                "sadness": 0,
                "neutral": -5
            }
            score += emotion_bonus.get(highlight["emotion"], 0)
            
            # 2. Сила эмоции
            score += int(highlight["emotion_score"] * 10)
            
            # 3. Оптимальная длительность (10-15 секунд идеально для соцсетей)
            duration = highlight["end"] - highlight["start"]
            if 8 <= duration <= 15:
                score += 15
            elif 5 <= duration < 8 or 15 < duration <= 20:
                score += 5
            elif duration > 30:
                score -= 10
            
            # 4. Количество причин для выделения
            score += len(highlight["reasons"]) * 5
            
            # Нормализация оценки (0-100)
            score = max(0, min(100, score))
            
            highlight["virality_score"] = score
        
        # Сортировка по оценке вирусности (от высокой к низкой)
        scored_highlights = sorted(highlights, key=lambda x: x["virality_score"], reverse=True)
        
        return scored_highlights
    
    def _get_video_duration(self, video_path: str) -> float:
        """Получение длительности видео"""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        cap.release()
        return duration
    
    def _format_timestamp(self, seconds: float) -> str:
        """Форматирование временной метки"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{seconds:.2f}"


class VideoEditor:
    """
    Класс для редактирования видео и создания клипов
    """
    
    def __init__(self):
        """Инициализация редактора"""
        print("Инициализация VideoEditor...")
        print("VideoEditor инициализирован")
    
    def create_highlight_clip(self, 
                             video_path: str, 
                             highlight: Dict[str, Any], 
                             output_path: Optional[str] = None) -> str:
        """
        Создание клипа на основе выделенного момента
        
        Args:
            video_path: Путь к исходному видео
            highlight: Информация о выделенном моменте
            output_path: Путь для сохранения результата (опционально)
            
        Returns:
            Путь к созданному клипу
        """
        print(f"Создание клипа для момента {highlight['time_str']}...")
        
        # Определение имени выходного файла
        if output_path is None:
            output_filename = f"highlight_{Path(video_path).stem}_{int(highlight['start'])}_{int(highlight['end'])}.mp4"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Загрузка видео
        video = mp.VideoFileClip(video_path)
        
        # Вырезание нужного фрагмента
        start_time = max(0, highlight["start"] - 0.5)  # Добавляем небольшой отступ
        end_time = min(video.duration, highlight["end"] + 0.5)
        
        clip = video.subclip(start_time, end_time)
        
        # Добавление субтитров
        if highlight.get("text"):
            txt_clip = mp.TextClip(
                highlight["text"], 
                fontsize=24, 
                color='white',
                bg_color='black',
                font='Arial-Bold',
                method='caption',
                size=(clip.w * 0.9, None),
                stroke_color='black',
                stroke_width=1
            )
            
            # Позиционирование текста внизу
            txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(clip.duration)
            
            # Композиция видео и текста
            clip = mp.CompositeVideoClip([clip, txt_clip])
        
        # Сохранение результата
        clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        print(f"Клип создан: {output_path}")
        return output_path
    
    def create_compilation(self, 
                          video_path: str, 
                          highlights: List[Dict[str, Any]], 
                          max_duration: float = 60.0,
                          output_path: Optional[str] = None) -> str:
        """
        Создание компиляции из лучших моментов
        
        Args:
            video_path: Путь к исходному видео
            highlights: Список выделенных моментов
            max_duration: Максимальная длительность компиляции
            output_path: Путь для сохранения результата (опционально)
            
        Returns:
            Путь к созданной компиляции
        """
        print(f"Создание компиляции из {len(highlights)} моментов...")
        
        # Определение имени выходного файла
        if output_path is None:
            output_filename = f"compilation_{Path(video_path).stem}.mp4"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Загрузка видео
        video = mp.VideoFileClip(video_path)
        
        # Сортировка моментов по оценке вирусности
        sorted_highlights = sorted(highlights, key=lambda x: x.get("virality_score", 0), reverse=True)
        
        # Выбор лучших моментов в пределах максимальной длительности
        clips = []
        total_duration = 0
        
        for highlight in sorted_highlights:
            start_time = max(0, highlight["start"] - 0.5)
            end_time = min(video.duration, highlight["end"] + 0.5)
            duration = end_time - start_time
            
            if total_duration + duration > max_duration:
                continue
            
            # Вырезание фрагмента
            clip = video.subclip(start_time, end_time)
            
            # Добавление субтитров
            if highlight.get("text"):
                txt_clip = mp.TextClip(
                    highlight["text"], 
                    fontsize=24, 
                    color='white',
                    bg_color='black',
                    font='Arial-Bold',
                    method='caption',
                    size=(clip.w * 0.9, None)
                )
                
                txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(clip.duration)
                clip = mp.CompositeVideoClip([clip, txt_clip])
            
            clips.append(clip)
            total_duration += duration
            
            if total_duration >= max_duration:
                break
        
        if not clips:
            raise ValueError("Не удалось создать компиляцию: нет подходящих моментов")
        
        # Добавление переходов между клипами
        final_clips = []
        for i, clip in enumerate(clips):
            if i > 0:
                # Добавление простого перехода (затухание)
                clip = clip.crossfadein(0.5)
            final_clips.append(clip)
        
        # Объединение клипов
        final_video = mp.concatenate_videoclips(final_clips)
        
        # Сохранение результата
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        print(f"Компиляция создана: {output_path}, длительность: {total_duration:.2f} сек.")
        return output_path


class VideoProcessor:
    """
    Основной класс для обработки видео, объединяющий анализ и редактирование
    """
    
    def __init__(self):
        """Инициализация процессора"""
        print("Инициализация VideoProcessor...")
        self.analyzer = VideoAnalyzer()
        self.editor = VideoEditor()
        print("VideoProcessor инициализирован")
    
    def process_video(self, video_path: str) -> Dict[str, Any]:
        """
        Полная обработка видео: анализ и создание клипов
        
        Args:
            video_path: Путь к видеофайлу
            
        Returns:
            Dict с результатами обработки
        """
        print(f"Обработка видео: {video_path}")
        
        # Анализ видео
        analysis_result = self.analyzer.analyze_video(video_path)
        
        # Создание клипов для топ-3 моментов
        top_highlights = analysis_result["highlights"][:3]
        
        clip_paths = []
        for highlight in top_highlights:
            clip_path = self.editor.create_highlight_clip(video_path, highlight)
            clip_paths.append(clip_path)
        
        # Создание компиляции
        compilation_path = self.editor.create_compilation(video_path, analysis_result["highlights"])
        
        # Формирование итогового результата
        result = {
            "video_path": video_path,
            "analysis": analysis_result,
            "clips": clip_paths,
            "compilation": compilation_path
        }
        
        print(f"Обработка завершена: создано {len(clip_paths)} клипов и 1 компиляция")
        return result


# API для интеграции с AgentFlow
app = FastAPI(title="Video Highlight API", description="API для выделения лучших моментов из видео")

# Модели данных
class VideoAnalysisRequest(BaseModel):
    video_url: str

class VideoAnalysisResponse(BaseModel):
    task_id: str
    status: str

class HighlightResult(BaseModel):
    start: float
    end: float
    text: str
    virality_score: float
    clip_url: Optional[str] = None

class VideoAnalysisResult(BaseModel):
    video_url: str
    duration: float
    highlights: List[HighlightResult]
    compilation_url: Optional[str] = None

# Хранилище задач (в реальном приложении использовать базу данных)
tasks = {}

@app.post("/api/videos/analyze", response_model=VideoAnalysisResponse)
async def analyze_video(request: VideoAnalysisRequest, background_tasks: BackgroundTasks):
    """Запуск анализа видео"""
    task_id = f"task_{int(time.time())}"
    
    tasks[task_id] = {
        "status": "pending",
        "video_url": request.video_url,
        "created_at": time.time()
    }
    
    # Запуск задачи в фоновом режиме
    background_tasks.add_task(process_video_task, task_id, request.video_url)
    
    return VideoAnalysisResponse(task_id=task_id, status="pending")

@app.get("/api/tasks/{task_id}", response_model=dict)
async def get_task_status(task_id: str):
    """Получение статуса задачи"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    return tasks[task_id]

@app.get("/api/videos/{task_id}/highlights", response_model=VideoAnalysisResult)
async def get_video_highlights(task_id: str):
    """Получение результатов анализа видео"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    task = tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Задача в статусе {task['status']}")
    
    return task["result"]

async def process_video_task(task_id: str, video_url: str):
    """Фоновая задача для обработки видео"""
    try:
        tasks[task_id]["status"] = "processing"
        
        # Загрузка видео
        video_path = download_video(video_url)
        
        # Обработка видео
        processor = VideoProcessor()
        result = processor.process_video(video_path)
        
        # Преобразование результата для API
        api_result = {
            "video_url": video_url,
            "duration": result["analysis"]["duration"],
            "highlights": [
                {
                    "start": h["start"],
                    "end": h["end"],
                    "text": h["text"],
                    "virality_score": h["virality_score"],
                    "clip_url": f"/api/clips/{Path(clip_path).name}" if i < len(result["clips"]) else None
                }
                for i, (h, clip_path) in enumerate(zip(result["analysis"]["highlights"], result["clips"] + [None] * 100))
            ],
            "compilation_url": f"/api/clips/{Path(result['compilation']).name}"
        }
        
        # Обновление статуса задачи
        tasks[task_id].update({
            "status": "completed",
            "result": api_result,
            "completed_at": time.time()
        })
        
    except Exception as e:
        tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time()
        })

def download_video(video_url: str) -> str:
    """
    Загрузка видео по URL
    
    В реальном приложении здесь будет код для загрузки видео.
    Для прототипа предполагаем, что URL - это локальный путь.
    """
    # Для прототипа просто возвращаем URL как путь
    return video_url


# Пример использования
if __name__ == "__main__":
    # Проверка наличия аргументов командной строки
    if len(sys.argv) < 2:
        print("Использование: python video_highlight_prototype.py <путь_к_видео>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"Ошибка: файл {video_path} не найден")
        sys.exit(1)
    
    # Создание процессора
    processor = VideoProcessor()
    
    # Обработка видео
    result = processor.process_video(video_path)
    
    # Вывод результатов
    print("\n=== Результаты обработки ===")
    print(f"Исходное видео: {result['video_path']}")
    print(f"Длительность: {result['analysis']['duration']:.2f} сек.")
    print(f"Найдено {len(result['analysis']['highlights'])} интересных моментов")
    print(f"Создано {len(result['clips'])} отдельных клипов")
    print(f"Компиляция: {result['compilation']}")
    
    # Сохранение результатов анализа в JSON
    analysis_path = os.path.join(OUTPUT_DIR, f"analysis_{Path(video_path).stem}.json")
    with open(analysis_path, 'w') as f:
        # Преобразуем numpy массивы в списки для сериализации
        analysis_copy = result["analysis"].copy()
        if "frame_analysis" in analysis_copy:
            for frame in analysis_copy["frame_analysis"]:
                if isinstance(frame.get("features"), np.ndarray):
                    frame["features"] = frame["features"].tolist()
        
        json.dump(analysis_copy, f, indent=2)
    
    print(f"Результаты анализа сохранены в {analysis_path}")
    print("\nГотово!")
