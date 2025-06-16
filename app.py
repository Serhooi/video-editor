import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const RENDER_API_URL = "https://agentflow-video-service.onrender.com";
// Используем переменную окружения для API ключа
const API_KEY = Deno.env.get("VIDEO_API_KEY") || "xgSmPQwDwE0nQ9mHfOX9hB37fTSQ7FOGb93UJ1v5PXg";

console.log("Video API Proxy Function started");

serve(async (req) => {
  try {
    // Добавляем CORS заголовки для всех запросов
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    // Обрабатываем preflight OPTIONS запросы
    if (req.method === "OPTIONS") {
      return new Response(null, {
        status: 200,
        headers: corsHeaders,
      });
    }

    // Получаем путь из URL запроса
    const url = new URL(req.url);
    let path = url.pathname.replace(/^\/video-api-proxy/, "");
    
    console.log(`Received request: ${req.method} ${path}`);
    
    // Специальная обработка для /health
    if (path === "/health" || path === "") {
      return new Response(JSON.stringify({
        status: "ok",
        service: "video-api-proxy",
        target: RENDER_API_URL,
        timestamp: new Date().toISOString()
      }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders
        }
      });
    }
    
    // Формируем URL для проксирования
    const targetUrl = `${RENDER_API_URL}${path}`;
    console.log(`Proxying ${req.method} request to: ${targetUrl}`);
    
    // Копируем заголовки и добавляем авторизацию
    const headers = new Headers();
    
    // Копируем важные заголовки из оригинального запроса
    if (req.headers.get("content-type")) {
      headers.set("Content-Type", req.headers.get("content-type")!);
    }
    
    // Добавляем авторизацию для API
    headers.set("Authorization", `Bearer ${API_KEY}`);
    
    console.log("Request headers:", Object.fromEntries([...headers.entries()]));
    
    // Проксируем запрос
    const response = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: req.body,
    });
    
    console.log(`Response status: ${response.status}`);
    
    // Получаем тело ответа
    const responseBody = await response.text();
    
    // Возвращаем ответ с CORS заголовками
    return new Response(responseBody, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
        ...corsHeaders
      },
    });
    
  } catch (error) {
    console.error("Error in video-api-proxy:", error);
    
    return new Response(JSON.stringify({ 
      error: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    }), {
      status: 500,
      headers: { 
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      }
    });
  }
});

