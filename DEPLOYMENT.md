# 🚀 React Video Editor Pro - Deployment Guide

## 🐳 Docker Deployment

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Serhooi/video-editor.git
cd video-editor

# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t video-editor .
docker run -p 3000:3000 video-editor
```

### Environment Variables

Create a `.env.local` file:

```env
# OpenAI API Key for AI Subtitles
NEXT_PUBLIC_OPENAI_API_KEY=sk-your-api-key-here

# Optional: Disable telemetry
NEXT_TELEMETRY_DISABLED=1
```

### Production Deployment

#### Option 1: Docker Compose (Recommended)

```bash
# Production deployment
docker-compose -f docker-compose.yml up -d

# Check logs
docker-compose logs -f video-editor

# Stop services
docker-compose down
```

#### Option 2: Manual Docker Build

```bash
# Build production image
docker build -t video-editor:latest .

# Run container
docker run -d \
  --name video-editor \
  -p 3000:3000 \
  -e NEXT_PUBLIC_OPENAI_API_KEY=your-api-key \
  --restart unless-stopped \
  video-editor:latest
```

#### Option 3: Vercel Deployment

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy to Vercel
vercel --prod

# Set environment variables in Vercel dashboard
# NEXT_PUBLIC_OPENAI_API_KEY=your-api-key
```

#### Option 4: Netlify Deployment

```bash
# Build the project
npm run build

# Deploy to Netlify
# Upload the .next folder to Netlify
# Set environment variables in Netlify dashboard
```

## 🔧 Configuration

### Next.js Configuration

The project uses `output: 'standalone'` for Docker optimization:

```javascript
// next.config.mjs
const nextConfig = {
  output: 'standalone',
  // ... other config
};
```

### Health Check

Health check endpoint available at `/api/health`:

```bash
curl http://localhost:3000/api/health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "service": "React Video Editor Pro",
  "version": "7.0.0"
}
```

## 🌐 Reverse Proxy Setup

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Apache Configuration

```apache
<VirtualHost *:80>
    ServerName your-domain.com
    ProxyPreserveHost On
    ProxyPass / http://localhost:3000/
    ProxyPassReverse / http://localhost:3000/
</VirtualHost>
```

## 📊 Monitoring

### Docker Health Checks

```bash
# Check container health
docker ps

# View health check logs
docker inspect video-editor | grep Health -A 10
```

### Application Logs

```bash
# Docker Compose logs
docker-compose logs -f video-editor

# Docker logs
docker logs -f video-editor
```

## 🔒 Security

### Environment Variables

Never commit API keys to version control:

```bash
# Add to .gitignore
.env.local
.env.production
```

### HTTPS Setup

Use Let's Encrypt with Certbot:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 🚀 Performance Optimization

### Docker Multi-stage Build

The Dockerfile uses multi-stage builds for optimization:

1. **deps**: Install dependencies
2. **builder**: Build the application
3. **runner**: Production runtime

### Caching

Enable Docker BuildKit for better caching:

```bash
export DOCKER_BUILDKIT=1
docker build -t video-editor .
```

## 🔧 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>
```

#### Docker Build Fails
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t video-editor .
```

#### Memory Issues
```bash
# Increase Docker memory limit
# Docker Desktop > Settings > Resources > Memory
```

### Logs and Debugging

```bash
# Application logs
docker logs video-editor

# Container shell access
docker exec -it video-editor sh

# Check container resources
docker stats video-editor
```

## 📈 Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
version: '3.8'
services:
  video-editor:
    build: .
    deploy:
      replicas: 3
    ports:
      - "3000-3002:3000"
```

### Load Balancer

Use Nginx or HAProxy for load balancing:

```nginx
upstream video_editor {
    server localhost:3000;
    server localhost:3001;
    server localhost:3002;
}

server {
    location / {
        proxy_pass http://video_editor;
    }
}
```

## 🎯 Production Checklist

- [ ] Set production environment variables
- [ ] Configure HTTPS/SSL
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Test health checks
- [ ] Set up reverse proxy
- [ ] Configure firewall rules
- [ ] Test AI subtitle functionality
- [ ] Verify video upload/processing
- [ ] Test mobile responsiveness

## 📞 Support

For deployment issues:

1. Check this deployment guide
2. Review Docker logs
3. Verify environment variables
4. Test health check endpoint
5. Create GitHub issue if needed

---

**🎬 Your professional video editor is ready for production!**

