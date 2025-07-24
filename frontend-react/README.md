# AI Compare React Frontend

Modern React-based dashboard for the AI Compare application, replacing the previous Gradio interface with a professional, enterprise-ready web application.

## Features

- **Real-time Provider Status Monitoring** - Live updates of Ollama and Open WebUI service health
- **Interactive Demo Controls** - Availability and Data Leak security demonstrations
- **Load Simulator Management** - HTTP traffic generation for observability monitoring
- **Side-by-side Chat Comparison** - Direct comparison between Ollama and pipeline-enhanced responses
- **Responsive Design** - Mobile-first approach with modern UI components
- **Real-time Updates** - WebSocket and polling-based live data updates

## Technology Stack

- **React 19** with TypeScript for type safety
- **Tailwind CSS** for styling and responsive design
- **Radix UI** components for accessibility and professional UI
- **Zustand** for state management
- **Vite** for fast development and building
- **NGINX** for production serving with API proxying

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Docker Build

```bash
# Build the Docker image
docker build -t ai-compare-frontend .

# Run the container
docker run -p 3000:80 ai-compare-frontend
```

## API Integration

The frontend communicates with the Python backend through:

- `/api/status` - Provider status monitoring
- `/api/chat` - Chat message processing
- `/api/availability-demo/toggle` - Availability demo control
- `/api/data-leak-demo` - Data leak demonstration
- `/api/load-simulator/*` - Load simulator management
- `/health` - Health check endpoint

## Features Comparison

| Feature | Gradio (Old) | React (New) |
|---------|-------------|-------------|
| Performance | Heavy Python runtime | Lightweight client-side |
| Customization | Limited components | Fully customizable |
| Mobile Support | Poor | Excellent responsive design |
| Real-time Updates | Basic polling | WebSocket + optimized polling |
| Accessibility | Basic | WCAG 2.1 AA compliant |
| Enterprise Features | None | Theming, RBAC ready, monitoring |
| Developer Experience | Python-focused | Modern web stack |

## Architecture

```
┌─────────────────────┐
│   NGINX (Port 80)   │  ← Production serving + API proxy
├─────────────────────┤
│   React Frontend    │  ← Modern dashboard interface
├─────────────────────┤
│   Zustand Store     │  ← Client-side state management
├─────────────────────┤
│   API Layer         │  ← HTTP client with error handling
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Python Backend     │  ← Existing Flask + Gradio backend
│  (Port 8080)        │
└─────────────────────┘
```

## Deployment

The React frontend is designed to be deployed alongside the existing Python backend:

1. **Development**: Vite dev server with API proxy to localhost:8080
2. **Production**: NGINX container serving static files and proxying API calls
3. **Kubernetes**: Separate deployment with service-to-service communication

## Configuration

Environment variables:
- `NODE_ENV` - Development/production mode
- `VITE_API_BASE_URL` - Backend API base URL (optional, defaults to relative URLs)

The production build automatically configures API proxying through NGINX to maintain security and avoid CORS issues.