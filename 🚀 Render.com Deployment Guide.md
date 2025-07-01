# 🚀 Render.com Deployment Guide

## ✅ **Да, можно просто нажать "Redeploy"!**

Теперь когда Dockerfile добавлен в репозиторий, Render.com автоматически:
1. Обнаружит Dockerfile
2. Соберет Docker образ
3. Развернет приложение

## 🔧 **Настройка на Render.com**

### **1. Автоматическое развертывание:**
- Зайдите в ваш сервис на Render.com
- Нажмите **"Manual Deploy"** → **"Deploy latest commit"**
- Или настройте **Auto-Deploy** для автоматического развертывания при push

### **2. Environment Variables:**
Добавьте в Render.com Dashboard:
```
NEXT_PUBLIC_OPENAI_API_KEY=sk-your-api-key-here
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
```

### **3. Build Settings:**
Render автоматически определит:
- **Build Command:** `docker build`
- **Start Command:** `docker run`
- **Port:** `3000`

## 🎯 **Проверка развертывания:**

### **Health Check:**
```bash
curl https://your-app.onrender.com/api/health
```

Ответ должен быть:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "service": "React Video Editor Pro",
  "version": "7.0.0"
}
```

### **Основные страницы:**
- `https://your-app.onrender.com/` - Главная страница
- `https://your-app.onrender.com/versions/7.0.0` - Видеоредактор

## 🔧 **Troubleshooting**

### **Если сборка не удалась:**
1. Проверьте логи в Render Dashboard
2. Убедитесь что Dockerfile в корне репозитория
3. Проверьте что все зависимости в package.json

### **Если приложение не запускается:**
1. Проверьте Environment Variables
2. Убедитесь что порт 3000 открыт
3. Проверьте логи приложения

## 🚀 **Готово!**

После успешного развертывания:
- ✅ Видеоредактор доступен онлайн
- ✅ AI субтитры работают (с API ключом)
- ✅ Все функции протестированы
- ✅ Готов к интеграции в AgentFlow

