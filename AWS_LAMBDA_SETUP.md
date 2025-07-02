# 🚀 AWS Lambda Setup Guide

## ✅ Что уже готово:

1. **AWS IAM пользователь создан** ✅
2. **Access Keys получены** ✅  
3. **Environment Variables добавлены на Vercel** ✅
4. **Все файлы конфигурации созданы** ✅

## 🔧 Что нужно сделать:

### **Шаг 1: Клонируйте проект локально**

```bash
git clone https://github.com/Serhooi/video-editor.git
cd video-editor
```

### **Шаг 2: Установите зависимости**

```bash
npm install
```

### **Шаг 3: Создайте .env.local файл**

```bash
echo "REMOTION_AWS_ACCESS_KEY_ID=AKIAW3ZSVALBWY2GJVO5" > .env.local
echo "REMOTION_AWS_SECRET_ACCESS_KEY=hZ7OOWvgs1XKLeoh+HTExR3RVLuyNism+bc20Pv" >> .env.local
echo "REMOTION_AWS_REGION=us-east-1" >> .env.local
```

### **Шаг 4: Запустите деплой AWS Lambda**

```bash
npm run deploy
```

Эта команда:
- ✅ Создаст S3 bucket для хранения видео
- ✅ Развернет Lambda функцию для рендера
- ✅ Загрузит Remotion композиции
- ✅ Выдаст новые environment variables

### **Шаг 5: Добавьте новые переменные на Vercel**

После успешного деплоя вы получите:

```
REMOTION_AWS_BUCKET_NAME=remotion-video-renders-xxxxx
REMOTION_AWS_FUNCTION_NAME=remotion-video-render
REMOTION_AWS_SITE_NAME=video-editor-site
```

**Добавьте их в Vercel Environment Variables!**

### **Шаг 6: Redeploy на Vercel**

После добавления всех переменных сделайте Redeploy в Vercel.

## 🎉 Готово!

После этого рендер видео будет работать через AWS Lambda:
- ⚡ Быстрый рендер (2-8GB RAM)
- 💰 Дешево (~$0.01-0.05 за видео)
- 🔄 Автомасштабирование
- ☁️ Надежное хранение в S3

## 🔧 Troubleshooting

### Ошибка "AccessDenied":
- Проверьте AWS credentials в .env.local
- Убедитесь, что IAM пользователь имеет нужные права

### Ошибка "FunctionNotFound":
- Запустите `npm run deploy` еще раз
- Проверьте, что деплой завершился успешно

### Ошибка "BucketNotFound":
- S3 bucket создается автоматически при деплое
- Проверьте логи деплоя на наличие ошибок

## 💡 Альтернатива

Если AWS кажется сложным, можно создать упрощенный рендер без AWS, но он будет менее надежным.

