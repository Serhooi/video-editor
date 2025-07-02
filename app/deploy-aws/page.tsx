import { AWSDeployButton } from '@/components/editor/version-7.0.0/components/aws-deploy/deploy-button';

export default function DeployAWSPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            🚀 AWS Lambda Deployment
          </h1>
          <p className="text-xl text-gray-600">
            Автоматический деплой AWS Lambda для рендера видео
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold text-blue-800 mb-2">
            ℹ️ Информация о деплое
          </h2>
          <div className="text-blue-700 space-y-2">
            <p>• <strong>Время выполнения:</strong> 2-3 минуты</p>
            <p>• <strong>Что создается:</strong> Lambda функция + S3 bucket для рендера</p>
            <p>• <strong>Стоимость:</strong> ~$1-5/месяц при активном использовании</p>
            <p>• <strong>Free Tier:</strong> Первый год бесплатно</p>
          </div>
        </div>

        <AWSDeployButton />

        <div className="mt-12 bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">
            ⚠️ Важные моменты
          </h2>
          <div className="text-yellow-700 space-y-2">
            <p>• Убедитесь, что AWS credentials добавлены в Environment Variables на Vercel</p>
            <p>• После успешного деплоя обязательно добавьте новые переменные на Vercel</p>
            <p>• Сделайте Redeploy на Vercel после добавления переменных</p>
            <p>• Если что-то пошло не так, проверьте логи деплоя</p>
          </div>
        </div>

        <div className="mt-8 text-center">
          <a 
            href="/versions/7.0.0" 
            className="inline-block px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            ← Вернуться к видеоредактору
          </a>
        </div>
      </div>
    </div>
  );
}

