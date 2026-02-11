# Agent Lighthouse Frontend

The visual dashboard for the Agent Lighthouse observability platform.

Built with:
- **React 18** + **Vite**
- **React Flow** (Trace visualization)
- **Recharts** (Token metrics)
- **Monaco Editor** (State inspection)

## Prerequisites

- Node.js 18+
- Backend running on `http://localhost:8000` (by default)

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment (optional):
   - Copy `.env.example` to `.env`
   - `VITE_API_URL`: Backend URL (default: `http://localhost:8000`)

## Development

Start the development server:

```bash
npm run dev
```

Visit `http://localhost:5173` to see the dashboard.

## Production Build

Build for production:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

## Project Structure

- `src/components/TraceGraph`: React Flow graph visualization
- `src/components/TokenMonitor`: Token usage and cost charts
- `src/components/StateInspector`: JSON editor for agent state
- `src/components/Sidebar`: Trace list and filtering

## Key Features

- **Real-time Updates**: Uses WebSockets to stream span events.
- **Interactive Graph**: Click nodes to see details.
- **State Control**: Pause, resume, and modify agent state on the fly.
