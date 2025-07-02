# 🚀 Руководство по деплою AWS Lambda для рендера видео

## ✅ Что уже готово:
- AWS аккаунт создан
- IAM пользователь `remotion-video-render` настроен
- Access Keys получены: `AKIAW3ZSVALBWY2GJVO5`
- Environment Variables добавлены на Vercel
- Все файлы для AWS Lambda созданы в GitHub

## 📋 Финальные шаги (займет 3-5 минут):

### 1. Откройте терминал/командную строку

### 2. Клонируйте репозиторий:
```bash
git clone https://github.com/Serhooi/video-editor.git
```

### 3. Перейдите в папку проекта:
```bash
cd video-editor
```

### 4. Установите зависимости:
```bash
npm install
```

### 5. Создайте файл с AWS ключами:
```bash
echo "REMOTION_AWS_ACCESS_KEY_ID=AKIAW3ZSVALBWY2GJVO5" > .env.local
echo "REMOTION_AWS_SECRET_ACCESS_KEY=hZ7OOWvgs1XKLeoh+HTExR3RVLuyNism+bc20Pv" >> .env.local
echo "REMOTION_AWS_REGION=us-east-1" >> .env.local
```

### 6. Запустите деплой в AWS:
```bash
npm run deploy
```

## 🎯 Что произойдет после `npm run deploy`:

1. **Создастся Lambda функция** для рендера видео
2. **Создастся S3 bucket** для хранения результатов
3. **Настроятся все права доступа** автоматически
4. **Выведутся новые environment variables** для добавления на Vercel

## 📝 После успешного деплоя:

1. Скопируйте новые переменные из вывода команды
2. Добавьте их на Vercel в Environment Variables
3. Сделайте Redeploy на Vercel
4. Протестируйте рендер видео

## ❗ Возможные проблемы:

### Если команда `npm` не найдена:
- Установите Node.js с https://nodejs.org/
- Перезапустите терминал

### Если ошибка с AWS правами:
- Проверьте, что Access Keys правильно скопированы
- Убедитесь, что в .env.local нет лишних пробелов

### Если ошибка с регионом:
- Попробуйте изменить регион на `us-east-2` в .env.local

## 💰 Стоимость:
- Первый год AWS: бесплатно (Free Tier)
- После: ~$1-5 в месяц при активном использовании
- За каждый рендер: ~$0.01-0.05

## 🆘 Нужна помощь?
Если что-то не работает, пришлите скриншот ошибки!

