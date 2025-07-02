# Гайд по интеграции Video Editor в AgentFlow

## Быстрый старт для разработчика

### Шаг 1: Добавить кнопку в AgentFlow

В вашем React компоненте AgentFlow добавьте кнопку:

```tsx
// В вашем компоненте AgentFlow
<button 
  onClick={() => openVideoEditor()}
  className="bg-blue-600 text-white px-4 py-2 rounded"
>
  Video Editor - Get Started
</button>
```

### Шаг 2: Функция открытия редактора

```tsx
const openVideoEditor = () => {
  // Получаем токен пользователя из вашей системы аутентификации
  const userToken = getUserToken(); // ваша функция получения токена
  
  // URL видеоредактора с токеном
  const editorUrl = `https://video-editor-ten-sand.vercel.app/versions/7.0.0?token=${userToken}&user=${userId}`;
  
  // Открываем в новой вкладке или в iframe
  window.open(editorUrl, '_blank');
  
  // ИЛИ встраиваем в iframe:
  // setShowEditor(true);
};
```

### Шаг 3: Встраивание через iframe (рекомендуется)

```tsx
const [showEditor, setShowEditor] = useState(false);

return (
  <div>
    {showEditor ? (
      <div className="fixed inset-0 z-50 bg-black">
        <div className="flex justify-between items-center p-4 bg-gray-800">
          <h2 className="text-white">Video Editor</h2>
          <button 
            onClick={() => setShowEditor(false)}
            className="text-white bg-red-600 px-3 py-1 rounded"
          >
            Закрыть
          </button>
        </div>
        <iframe
          src={`https://video-editor-ten-sand.vercel.app/versions/7.0.0?token=${userToken}`}
          className="w-full h-full"
          frameBorder="0"
          allow="camera; microphone; fullscreen"
        />
      </div>
    ) : (
      <button onClick={() => setShowEditor(true)}>
        Video Editor - Get Started
      </button>
    )}
  </div>
);
```

## API для сохранения проектов (опционально)

### Шаг 4: Создание API endpoints в AgentFlow

```typescript
// pages/api/video-projects.ts
export default async function handler(req, res) {
  if (req.method === 'POST') {
    // Создание нового проекта
    const { name, userId } = req.body;
    
    const project = await createVideoProject({
      name,
      userId,
      status: 'created'
    });
    
    res.json({ projectId: project.id });
  }
  
  if (req.method === 'GET') {
    // Получение проектов пользователя
    const { userId } = req.query;
    const projects = await getUserVideoProjects(userId);
    res.json({ projects });
  }
}
```

### Шаг 5: Обработка завершенных видео

```typescript
// pages/api/video-completed.ts
export default async function handler(req, res) {
  const { projectId, videoUrl, userId } = req.body;
  
  // Сохраняем ссылку на готовое видео
  await saveCompletedVideo({
    projectId,
    videoUrl,
    userId,
    completedAt: new Date()
  });
  
  // Уведомляем пользователя (опционально)
  await notifyUser(userId, 'Ваше видео готово!');
  
  res.json({ success: true });
}
```

## Простая интеграция без API

### Вариант 1: Прямая ссылка

```tsx
// Самый простой способ
<a 
  href="https://video-editor-ten-sand.vercel.app/versions/7.0.0" 
  target="_blank"
  className="bg-blue-600 text-white px-4 py-2 rounded inline-block"
>
  Video Editor - Get Started
</a>
```

### Вариант 2: Popup окно

```tsx
const openEditor = () => {
  const popup = window.open(
    'https://video-editor-ten-sand.vercel.app/versions/7.0.0',
    'videoEditor',
    'width=1200,height=800,scrollbars=yes,resizable=yes'
  );
  
  // Слушаем сообщения от редактора (опционально)
  window.addEventListener('message', (event) => {
    if (event.origin === 'https://video-editor-ten-sand.vercel.app') {
      if (event.data.type === 'VIDEO_COMPLETED') {
        console.log('Видео готово:', event.data.videoUrl);
        popup.close();
      }
    }
  });
};
```

## Настройка аутентификации

### Шаг 6: Передача данных пользователя

```tsx
const openVideoEditor = () => {
  const userData = {
    userId: user.id,
    email: user.email,
    subscription: user.subscription, // free/premium
    token: getAuthToken()
  };
  
  const params = new URLSearchParams(userData);
  const editorUrl = `https://video-editor-ten-sand.vercel.app/versions/7.0.0?${params}`;
  
  window.open(editorUrl, '_blank');
};
```

## Готовый компонент для копирования

```tsx
import React, { useState } from 'react';

const VideoEditorIntegration = ({ user }) => {
  const [showEditor, setShowEditor] = useState(false);
  
  const openEditor = () => {
    setShowEditor(true);
  };
  
  const closeEditor = () => {
    setShowEditor(false);
  };
  
  return (
    <>
      {/* Кнопка запуска */}
      <button
        onClick={openEditor}
        className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all"
      >
        🎬 Video Editor - Get Started
      </button>
      
      {/* Полноэкранный редактор */}
      {showEditor && (
        <div className="fixed inset-0 z-50 bg-black">
          {/* Заголовок с кнопкой закрытия */}
          <div className="flex justify-between items-center p-4 bg-gray-900 border-b border-gray-700">
            <div className="flex items-center gap-3">
              <h2 className="text-white text-lg font-semibold">Video Editor Pro</h2>
              <span className="text-gray-400 text-sm">by AgentFlow</span>
            </div>
            <button
              onClick={closeEditor}
              className="text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 px-3 py-1 rounded transition-colors"
            >
              ✕ Закрыть
            </button>
          </div>
          
          {/* Iframe с редактором */}
          <iframe
            src={`https://video-editor-ten-sand.vercel.app/versions/7.0.0?user=${user.id}&token=${user.token}`}
            className="w-full h-full"
            frameBorder="0"
            allow="camera; microphone; fullscreen; clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"
          />
        </div>
      )}
    </>
  );
};

export default VideoEditorIntegration;
```

## Использование компонента

```tsx
// В вашем главном компоненте AgentFlow
import VideoEditorIntegration from './VideoEditorIntegration';

function AgentFlowDashboard() {
  const user = getCurrentUser(); // ваша функция получения пользователя
  
  return (
    <div className="dashboard">
      <h1>AgentFlow Dashboard</h1>
      
      {/* Ваш существующий контент */}
      
      {/* Интеграция видеоредактора */}
      <div className="video-editor-section">
        <h2>Создание видео</h2>
        <p>Создавайте профессиональные видео с AI субтитрами</p>
        <VideoEditorIntegration user={user} />
      </div>
    </div>
  );
}
```

## Итого: что нужно сделать

1. **Скопировать готовый компонент** `VideoEditorIntegration`
2. **Добавить в нужное место** в AgentFlow
3. **Передать данные пользователя** (id, token)
4. **Готово!** Видеоредактор работает

**Время интеграции: 15-30 минут**

Видеоредактор уже полностью готов и работает по ссылке:
`https://video-editor-ten-sand.vercel.app/versions/7.0.0`

