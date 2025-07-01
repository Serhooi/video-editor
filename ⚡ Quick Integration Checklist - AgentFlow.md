# ⚡ Quick Integration Checklist - AgentFlow

## 🚀 **Render.com - Быстрый старт**

### ✅ **Да, можно просто нажать "Redeploy"!**
1. Зайти в Render.com Dashboard
2. Найти ваш сервис
3. Нажать **"Manual Deploy"** → **"Deploy latest commit"**
4. Добавить Environment Variable: `NEXT_PUBLIC_OPENAI_API_KEY=sk-your-key`
5. Дождаться завершения сборки

### 🔗 **Проверить работу:**
- `https://your-app.onrender.com/api/health` - должен вернуть `{"status":"ok"}`
- `https://your-app.onrender.com/versions/7.0.0` - видеоредактор

---

## 🤖 **Для AI Разработчика - Пошаговый план**

### **Шаг 1: База данных (30 мин)**
```bash
# Добавить в schema.prisma
npx prisma db push
```
Модели: `VideoProject`, `MediaFile`, `AISubtitle`

### **Шаг 2: API Endpoints (2 часа)**
Создать файлы:
- `/api/video-projects/route.ts` - CRUD проектов
- `/api/media/upload/route.ts` - загрузка файлов  
- `/api/ai-subtitles/generate/route.ts` - AI субтитры

### **Шаг 3: Frontend Components (3 часа)**
- `VideoEditorWrapper.tsx` - главный компонент
- `ProjectManager.tsx` - управление проектами
- `useVideoProjects.ts` - хук для API

### **Шаг 4: Интеграция в AgentFlow (1 час)**
- Добавить в навигацию
- Создать страницу `/video-editor`
- Настроить middleware

### **Шаг 5: Тестирование (1 час)**
- Создание проекта
- Загрузка видео
- AI субтитры
- Сохранение/загрузка

---

## 📋 **Готовые файлы для копирования**

### **1. Prisma Schema** ✅
```prisma
model VideoProject {
  id          String    @id @default(cuid())
  title       String
  data        Json      // Данные проекта
  userId      String
  user        User      @relation(fields: [userId], references: [id])
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
}
```

### **2. API Route Example** ✅
```typescript
// /api/video-projects/route.ts
export async function GET() {
  const projects = await prisma.videoProject.findMany({
    where: { userId: session.user.id },
  });
  return NextResponse.json(projects);
}
```

### **3. React Component** ✅
```typescript
// components/VideoEditorWrapper.tsx
export const VideoEditorWrapper = ({ userId }) => {
  const { projects, createProject } = useVideoProjects(userId);
  // ... логика компонента
};
```

---

## 🎯 **Ключевые эндпоинты**

### **Проекты:**
- `POST /api/video-projects` - создать
- `GET /api/video-projects` - список
- `PUT /api/video-projects/:id` - обновить

### **Медиа:**
- `POST /api/media/upload` - загрузка
- `GET /api/media/:id` - получить

### **AI Субтитры:**
- `POST /api/ai-subtitles/generate` - генерация
- `GET /api/ai-subtitles/:id` - получить

---

## ⏱️ **Время выполнения: ~7 часов**

1. **База данных** - 30 мин
2. **API** - 2 часа  
3. **Frontend** - 3 часа
4. **Интеграция** - 1 час
5. **Тестирование** - 30 мин

---

## 🔑 **Environment Variables**

```env
DATABASE_URL="postgresql://..."
OPENAI_API_KEY="sk-your-key"
NEXT_PUBLIC_OPENAI_API_KEY="sk-your-key"
NEXTAUTH_SECRET="your-secret"
```

---

## 🎉 **Результат**

После интеграции пользователи AgentFlow смогут:
- ✅ Создавать и сохранять видеопроекты
- ✅ Генерировать AI субтитры одним кликом
- ✅ Редактировать видео с профессиональными инструментами
- ✅ Возвращаться к проектам через несколько дней

**Полнофункциональный видеоредактор с AI в AgentFlow! 🚀**

