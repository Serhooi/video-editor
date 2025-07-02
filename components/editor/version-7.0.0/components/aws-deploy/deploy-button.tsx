'use client';

import React, { useState } from 'react';

interface DeploymentResult {
  success: boolean;
  message?: string;
  deploymentInfo?: {
    bucketName: string;
    siteName: string;
    functionName: string;
    region: string;
  };
  environmentVariables?: {
    REMOTION_AWS_BUCKET_NAME: string;
    REMOTION_AWS_SITE_NAME: string;
    REMOTION_AWS_FUNCTION_NAME: string;
    REMOTION_AWS_REGION: string;
  };
  error?: string;
  stdout?: string;
  stderr?: string;
}

export const AWSDeployButton: React.FC = () => {
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState<DeploymentResult | null>(null);
  const [showLogs, setShowLogs] = useState(false);

  const handleDeploy = async () => {
    setIsDeploying(true);
    setDeployResult(null);
    
    try {
      console.log('🚀 Starting AWS Lambda deployment...');
      
      const response = await fetch('/api/deploy-aws', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result: DeploymentResult = await response.json();
      setDeployResult(result);

      if (result.success) {
        console.log('✅ Deployment successful!', result);
        alert('🎉 AWS Lambda deployed successfully!\n\nНовые environment variables созданы. Добавьте их на Vercel и сделайте Redeploy.');
      } else {
        console.error('❌ Deployment failed:', result.error);
        alert(`❌ Deployment failed: ${result.error}`);
      }
    } catch (error) {
      console.error('❌ Deployment request failed:', error);
      setDeployResult({
        success: false,
        error: `Request failed: ${error}`
      });
      alert(`❌ Deployment request failed: ${error}`);
    } finally {
      setIsDeploying(false);
    }
  };

  const copyEnvVars = () => {
    if (deployResult?.environmentVariables) {
      const envText = Object.entries(deployResult.environmentVariables)
        .map(([key, value]) => `${key}=${value}`)
        .join('\n');
      
      navigator.clipboard.writeText(envText);
      alert('📋 Environment variables copied to clipboard!\n\nПерейдите на Vercel → Settings → Environment Variables и вставьте их.');
    }
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-4 text-gray-800">
        🚀 AWS Lambda Deployment
      </h2>
      
      <div className="mb-4">
        <p className="text-gray-600 mb-2">
          Нажмите кнопку ниже, чтобы автоматически развернуть AWS Lambda функцию для рендера видео.
        </p>
        <p className="text-sm text-gray-500">
          Процесс займет 2-3 минуты. После завершения вы получите новые environment variables для Vercel.
        </p>
      </div>

      <button
        onClick={handleDeploy}
        disabled={isDeploying}
        className={`w-full py-3 px-6 rounded-lg font-semibold text-white transition-all ${
          isDeploying
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
        }`}
      >
        {isDeploying ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Deploying AWS Lambda...
          </span>
        ) : (
          '🚀 Deploy AWS Lambda'
        )}
      </button>

      {deployResult && (
        <div className={`mt-6 p-4 rounded-lg ${
          deployResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          <h3 className={`font-semibold mb-2 ${
            deployResult.success ? 'text-green-800' : 'text-red-800'
          }`}>
            {deployResult.success ? '✅ Deployment Successful!' : '❌ Deployment Failed'}
          </h3>
          
          {deployResult.success && deployResult.environmentVariables && (
            <div className="mb-4">
              <p className="text-green-700 mb-2">
                Новые environment variables созданы:
              </p>
              <div className="bg-gray-100 p-3 rounded text-sm font-mono">
                {Object.entries(deployResult.environmentVariables).map(([key, value]) => (
                  <div key={key}>{key}={value}</div>
                ))}
              </div>
              <button
                onClick={copyEnvVars}
                className="mt-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                📋 Copy to Clipboard
              </button>
            </div>
          )}

          {deployResult.error && (
            <p className="text-red-700 mb-2">
              Error: {deployResult.error}
            </p>
          )}

          {(deployResult.stdout || deployResult.stderr) && (
            <div className="mt-4">
              <button
                onClick={() => setShowLogs(!showLogs)}
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {showLogs ? 'Hide' : 'Show'} Deployment Logs
              </button>
              
              {showLogs && (
                <div className="mt-2 bg-gray-100 p-3 rounded text-xs font-mono max-h-64 overflow-y-auto">
                  {deployResult.stdout && (
                    <div>
                      <strong>Output:</strong>
                      <pre>{deployResult.stdout}</pre>
                    </div>
                  )}
                  {deployResult.stderr && (
                    <div className="mt-2">
                      <strong>Errors:</strong>
                      <pre className="text-red-600">{deployResult.stderr}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-6 text-sm text-gray-500">
        <h4 className="font-semibold mb-2">После успешного деплоя:</h4>
        <ol className="list-decimal list-inside space-y-1">
          <li>Скопируйте новые environment variables</li>
          <li>Перейдите на Vercel → Settings → Environment Variables</li>
          <li>Добавьте новые переменные</li>
          <li>Нажмите Redeploy на Vercel</li>
          <li>Протестируйте рендер видео</li>
        </ol>
      </div>
    </div>
  );
};

