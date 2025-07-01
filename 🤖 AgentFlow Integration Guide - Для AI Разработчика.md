# 🤖 AgentFlow Integration Guide - Для AI Разработчика

## 🎯 **Цель интеграции**
Встроить React Video Editor Pro в AgentFlow как полнофункциональный видеоредактор с AI субтитрами.

## 📋 **Архитектура интеграции**

### **1. Frontend Integration (React Component)**
```typescript
// AgentFlow компонент
import { VideoEditor } from '@/components/video-editor';

const AgentFlowVideoEditor = () => {
  return (
    <div className="video-editor-container">
      <VideoEditor 
        apiKey={process.env.NEXT_PUBLIC_OPENAI_API_KEY}
        onProjectSave={handleProjectSave}
        onVideoExport={handleVideoExport}
        userId={currentUser.id}
      />
    </div>
  );
};
```

### **2. Backend API Endpoints**

#### **Проекты пользователей:**
```typescript
// /api/video-projects
POST   /api/video-projects          // Создать проект
GET    /api/video-projects          // Получить проекты пользователя  
GET    /api/video-projects/:id      // Получить конкретный проект
PUT    /api/video-projects/:id      // Обновить проект
DELETE /api/video-projects/:id      // Удалить проект
```

#### **Медиа файлы:**
```typescript
// /api/media
POST   /api/media/upload           // Загрузка видео/аудио/изображений
GET    /api/media/:id              // Получить медиа файл
DELETE /api/media/:id              // Удалить медиа файл
POST   /api/media/process          // Обработка медиа (сжатие, конвертация)
```

#### **AI Субтитры:**
```typescript
// /api/ai-subtitles
POST   /api/ai-subtitles/generate  // Генерация субтитров через Whisper+ChatGPT
GET    /api/ai-subtitles/:id       // Получить сгенерированные субтитры
POST   /api/ai-subtitles/enhance   // Улучшение существующих субтитров
```

#### **Рендеринг видео:**
```typescript
// /api/video-render
POST   /api/video-render/start     // Запуск рендеринга
GET    /api/video-render/:id       // Статус рендеринга
GET    /api/video-render/:id/download // Скачать готовое видео
```

## 🗄️ **База данных (Prisma Schema)**

```prisma
// schema.prisma
model User {
  id            String    @id @default(cuid())
  email         String    @unique
  name          String?
  videoProjects VideoProject[]
  mediaFiles    MediaFile[]
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
}

model VideoProject {
  id          String    @id @default(cuid())
  title       String
  description String?
  data        Json      // Данные проекта (timeline, overlays, etc.)
  thumbnail   String?   // URL превью
  duration    Int?      // Длительность в секундах
  status      ProjectStatus @default(DRAFT)
  userId      String
  user        User      @relation(fields: [userId], references: [id])
  mediaFiles  MediaFile[]
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
}

model MediaFile {
  id          String    @id @default(cuid())
  filename    String
  originalName String
  mimeType    String
  size        Int
  url         String
  type        MediaType
  projectId   String?
  project     VideoProject? @relation(fields: [projectId], references: [id])
  userId      String
  user        User      @relation(fields: [userId], references: [id])
  createdAt   DateTime  @default(now())
}

model AISubtitle {
  id          String    @id @default(cuid())
  projectId   String
  language    String
  style       SubtitleStyle
  segments    Json      // Массив сегментов субтитров
  confidence  Float
  status      ProcessingStatus @default(PROCESSING)
  createdAt   DateTime  @default(now())
}

enum ProjectStatus {
  DRAFT
  PUBLISHED
  ARCHIVED
}

enum MediaType {
  VIDEO
  AUDIO
  IMAGE
}

enum SubtitleStyle {
  CASUAL
  FORMAL
  SOCIAL_MEDIA
  EDUCATIONAL
}

enum ProcessingStatus {
  PROCESSING
  COMPLETED
  FAILED
}
```

## 🔧 **API Implementation Examples**

### **1. Проекты пользователей**

```typescript
// /api/video-projects/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { getServerSession } from 'next-auth';

export async function GET(request: NextRequest) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const projects = await prisma.videoProject.findMany({
    where: { userId: session.user.id },
    include: {
      mediaFiles: true,
    },
    orderBy: { updatedAt: 'desc' },
  });

  return NextResponse.json(projects);
}

export async function POST(request: NextRequest) {
  const session = await getServerSession();
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { title, description, data } = await request.json();

  const project = await prisma.videoProject.create({
    data: {
      title,
      description,
      data,
      userId: session.user.id,
    },
  });

  return NextResponse.json(project);
}
```

### **2. AI Субтитры**

```typescript
// /api/ai-subtitles/generate/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { generateAutoSubtitles } from '@/lib/ai-subtitles';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const videoFile = formData.get('video') as File;
    const language = formData.get('language') as string;
    const style = formData.get('style') as string;
    const apiKey = process.env.OPENAI_API_KEY;

    if (!apiKey) {
      return NextResponse.json(
        { error: 'OpenAI API key not configured' },
        { status: 500 }
      );
    }

    const subtitles = await generateAutoSubtitles(videoFile, {
      openaiApiKey: apiKey,
      language,
      style: style as any,
      maxWordsPerSegment: 8,
    });

    // Сохранить в базу данных
    const aiSubtitle = await prisma.aiSubtitle.create({
      data: {
        projectId: formData.get('projectId') as string,
        language,
        style: style as any,
        segments: subtitles,
        confidence: 0.95,
        status: 'COMPLETED',
      },
    });

    return NextResponse.json({
      id: aiSubtitle.id,
      subtitles,
      confidence: aiSubtitle.confidence,
    });
  } catch (error) {
    console.error('AI subtitle generation failed:', error);
    return NextResponse.json(
      { error: 'Subtitle generation failed' },
      { status: 500 }
    );
  }
}
```

### **3. Медиа загрузка**

```typescript
// /api/media/upload/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { writeFile } from 'fs/promises';
import { join } from 'path';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;
    
    if (!file) {
      return NextResponse.json({ error: 'No file uploaded' }, { status: 400 });
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Сохранить файл
    const filename = `${Date.now()}-${file.name}`;
    const path = join(process.cwd(), 'uploads', filename);
    await writeFile(path, buffer);

    // Сохранить в базу данных
    const mediaFile = await prisma.mediaFile.create({
      data: {
        filename,
        originalName: file.name,
        mimeType: file.type,
        size: file.size,
        url: `/uploads/${filename}`,
        type: file.type.startsWith('video/') ? 'VIDEO' : 
              file.type.startsWith('audio/') ? 'AUDIO' : 'IMAGE',
        userId: session.user.id,
      },
    });

    return NextResponse.json(mediaFile);
  } catch (error) {
    return NextResponse.json(
      { error: 'Upload failed' },
      { status: 500 }
    );
  }
}
```

## 🎨 **Frontend Components**

### **1. Главный компонент редактора**

```typescript
// components/video-editor/VideoEditorWrapper.tsx
'use client';

import { useState, useEffect } from 'react';
import { VideoEditor } from './VideoEditor';
import { ProjectManager } from './ProjectManager';
import { useVideoProjects } from '@/hooks/useVideoProjects';

interface VideoEditorWrapperProps {
  userId: string;
  apiKey?: string;
}

export const VideoEditorWrapper = ({ userId, apiKey }: VideoEditorWrapperProps) => {
  const [currentProject, setCurrentProject] = useState(null);
  const [showProjectManager, setShowProjectManager] = useState(true);
  const { projects, createProject, updateProject, deleteProject } = useVideoProjects(userId);

  const handleCreateProject = async (title: string) => {
    const project = await createProject(title);
    setCurrentProject(project);
    setShowProjectManager(false);
  };

  const handleOpenProject = (project: any) => {
    setCurrentProject(project);
    setShowProjectManager(false);
  };

  const handleSaveProject = async (projectData: any) => {
    if (currentProject) {
      await updateProject(currentProject.id, projectData);
    }
  };

  if (showProjectManager) {
    return (
      <ProjectManager
        projects={projects}
        onCreateProject={handleCreateProject}
        onOpenProject={handleOpenProject}
        onDeleteProject={deleteProject}
      />
    );
  }

  return (
    <VideoEditor
      project={currentProject}
      onSave={handleSaveProject}
      onBack={() => setShowProjectManager(true)}
      apiKey={apiKey}
    />
  );
};
```

### **2. Менеджер проектов**

```typescript
// components/video-editor/ProjectManager.tsx
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Plus, Play, Trash2 } from 'lucide-react';

interface ProjectManagerProps {
  projects: any[];
  onCreateProject: (title: string) => void;
  onOpenProject: (project: any) => void;
  onDeleteProject: (projectId: string) => void;
}

export const ProjectManager = ({
  projects,
  onCreateProject,
  onOpenProject,
  onDeleteProject,
}: ProjectManagerProps) => {
  const [newProjectTitle, setNewProjectTitle] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);

  const handleCreate = () => {
    if (newProjectTitle.trim()) {
      onCreateProject(newProjectTitle.trim());
      setNewProjectTitle('');
      setShowCreateForm(false);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Мои видеопроекты</h1>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Новый проект
        </Button>
      </div>

      {showCreateForm && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Создать новый проект</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder="Название проекта"
                value={newProjectTitle}
                onChange={(e) => setNewProjectTitle(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleCreate()}
              />
              <Button onClick={handleCreate}>Создать</Button>
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                Отмена
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <Card key={project.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="text-lg">{project.title}</CardTitle>
              <p className="text-sm text-gray-500">
                Обновлен: {new Date(project.updatedAt).toLocaleDateString()}
              </p>
            </CardHeader>
            <CardContent>
              {project.thumbnail && (
                <img
                  src={project.thumbnail}
                  alt={project.title}
                  className="w-full h-32 object-cover rounded mb-4"
                />
              )}
              <div className="flex gap-2">
                <Button
                  onClick={() => onOpenProject(project)}
                  className="flex-1"
                >
                  <Play className="mr-2 h-4 w-4" />
                  Открыть
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onDeleteProject(project.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {projects.length === 0 && !showCreateForm && (
        <div className="text-center py-12">
          <h3 className="text-xl font-semibold mb-2">Нет проектов</h3>
          <p className="text-gray-500 mb-4">Создайте свой первый видеопроект</p>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Создать проект
          </Button>
        </div>
      )}
    </div>
  );
};
```

## 🔗 **Hooks для работы с API**

### **1. useVideoProjects**

```typescript
// hooks/useVideoProjects.ts
import { useState, useEffect } from 'react';

export const useVideoProjects = (userId: string) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, [userId]);

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/video-projects');
      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const createProject = async (title: string) => {
    try {
      const response = await fetch('/api/video-projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, data: {} }),
      });
      const project = await response.json();
      setProjects(prev => [project, ...prev]);
      return project;
    } catch (error) {
      console.error('Failed to create project:', error);
      throw error;
    }
  };

  const updateProject = async (projectId: string, data: any) => {
    try {
      const response = await fetch(`/api/video-projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data }),
      });
      const updatedProject = await response.json();
      setProjects(prev => 
        prev.map(p => p.id === projectId ? updatedProject : p)
      );
      return updatedProject;
    } catch (error) {
      console.error('Failed to update project:', error);
      throw error;
    }
  };

  const deleteProject = async (projectId: string) => {
    try {
      await fetch(`/api/video-projects/${projectId}`, {
        method: 'DELETE',
      });
      setProjects(prev => prev.filter(p => p.id !== projectId));
    } catch (error) {
      console.error('Failed to delete project:', error);
      throw error;
    }
  };

  return {
    projects,
    loading,
    createProject,
    updateProject,
    deleteProject,
    refetch: fetchProjects,
  };
};
```

### **2. useAISubtitles**

```typescript
// hooks/useAISubtitles.ts
import { useState } from 'react';

export const useAISubtitles = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateSubtitles = async (
    videoFile: File,
    options: {
      language?: string;
      style?: string;
      projectId?: string;
    }
  ) => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('video', videoFile);
      formData.append('language', options.language || 'auto');
      formData.append('style', options.style || 'casual');
      if (options.projectId) {
        formData.append('projectId', options.projectId);
      }

      const response = await fetch('/api/ai-subtitles/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to generate subtitles');
      }

      const result = await response.json();
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    generateSubtitles,
    loading,
    error,
  };
};
```

## 🚀 **Интеграция в AgentFlow**

### **1. Добавить в главное меню AgentFlow:**

```typescript
// components/navigation/MainNav.tsx
const navigationItems = [
  // ... существующие пункты
  {
    title: 'Видеоредактор',
    href: '/video-editor',
    icon: Video,
    description: 'Создание и редактирование видео с AI субтитрами',
  },
];
```

### **2. Создать страницу редактора:**

```typescript
// app/video-editor/page.tsx
import { VideoEditorWrapper } from '@/components/video-editor/VideoEditorWrapper';
import { getServerSession } from 'next-auth';

export default async function VideoEditorPage() {
  const session = await getServerSession();
  
  if (!session?.user) {
    redirect('/auth/signin');
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <VideoEditorWrapper
        userId={session.user.id}
        apiKey={process.env.NEXT_PUBLIC_OPENAI_API_KEY}
      />
    </div>
  );
}
```

### **3. Добавить в middleware для защиты:**

```typescript
// middleware.ts
export const config = {
  matcher: [
    // ... существующие маршруты
    '/video-editor/:path*',
    '/api/video-projects/:path*',
    '/api/ai-subtitles/:path*',
  ],
};
```

## 📦 **Необходимые зависимости**

```json
{
  "dependencies": {
    "@prisma/client": "^5.0.0",
    "prisma": "^5.0.0",
    "next-auth": "^4.0.0",
    "formidable": "^3.0.0",
    "multer": "^1.4.5-lts.1",
    "@types/multer": "^1.4.7"
  }
}
```

## 🔐 **Environment Variables**

```env
# .env.local
DATABASE_URL="postgresql://..."
NEXTAUTH_SECRET="your-secret"
NEXTAUTH_URL="http://localhost:3000"
OPENAI_API_KEY="sk-your-openai-key"
NEXT_PUBLIC_OPENAI_API_KEY="sk-your-openai-key"
```

## ✅ **Чеклист интеграции**

### **Backend:**
- [ ] Настроить Prisma схему
- [ ] Создать API endpoints для проектов
- [ ] Реализовать загрузку медиа файлов
- [ ] Интегрировать AI субтитры API
- [ ] Добавить аутентификацию к API

### **Frontend:**
- [ ] Создать компонент VideoEditorWrapper
- [ ] Реализовать ProjectManager
- [ ] Добавить hooks для API
- [ ] Интегрировать в навигацию AgentFlow
- [ ] Настроить роутинг

### **Deployment:**
- [ ] Добавить environment variables
- [ ] Настроить файловое хранилище
- [ ] Протестировать AI функциональность
- [ ] Настроить мониторинг

## 🎯 **Результат интеграции**

После выполнения всех шагов пользователи AgentFlow смогут:

1. **Создавать видеопроекты** с автосохранением
2. **Загружать медиа файлы** через удобный интерфейс
3. **Генерировать AI субтитры** одним кликом
4. **Редактировать видео** с профессиональными инструментами
5. **Экспортировать готовые видео** в высоком качестве
6. **Управлять проектами** с возможностью возврата к работе

**Полная интеграция превратит AgentFlow в мощную платформу для создания видеоконтента с AI!** 🚀

