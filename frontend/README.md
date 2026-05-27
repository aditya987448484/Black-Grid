# Axiom Terminal - Frontend

Next.js 14+ powered frontend for the Axiom Terminal financial research platform.

## Tech Stack

- **Framework**: Next.js 14+
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Animations**: Framer Motion
- **Charts**: Recharts
- **HTTP Client**: Axios
- **State Management**: React Hooks

## Project Structure

```
frontend/
├── app/                    # Next.js app directory
│   ├── (dashboard)/       # Dashboard layout group
│   │   ├── dashboard/     # Dashboard page
│   │   └── layout.tsx
│   ├── asset/             # Asset detail pages
│   │   └── [ticker]/page.tsx
│   ├── report/            # Analyst report page
│   ├── backtest/          # Backtest lab page
│   ├── portfolio/         # Portfolio monitoring page
│   ├── layout.tsx
│   └── page.tsx           # Home page
├── components/            # React components
│   ├── ui/               # Shadcn UI components
│   ├── common/           # Reusable common components
│   ├── charts/           # Chart-specific components
│   ├── dashboard/        # Dashboard-specific components
│   └── asset/            # Asset-specific components
├── lib/                   # Utility functions and hooks
│   ├── api/              # API client and endpoints
│   ├── hooks/            # Custom React hooks
│   ├── types/            # TypeScript type definitions
│   └── utils/            # Helper functions
├── styles/               # Global CSS and Tailwind
├── public/               # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── next.config.js
```

## Getting Started

### Prerequisites

- Node.js 18+ or npm 9+
- Backend API running on `localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create `.env.local` from `.env.local.example`:
```bash
cp .env.local.example .env.local
```

3. Update `.env.local` with your configuration:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Build

```bash
npm run build
npm start
```

### Type Checking

```bash
npm run type-check
```

## Pages

- **Dashboard** (`/dashboard`) - Market overview and portfolio monitoring
- **Asset Detail** (`/asset/[ticker]`) - Individual asset analysis
- **Analyst Report** (`/report`) - AI-generated analysis
- **Backtest Lab** (`/backtest`) - Strategy backtesting
- **Portfolio Monitor** (`/portfolio`) - Watchlist management

## API Integration

All API calls are made through the `/lib/api/client.ts` file:

```typescript
// Market API
market.getOverview()

// Asset API
asset.getDetail(ticker)
asset.getTechnicals(ticker)
asset.getForecast(ticker)

// Report API
report.getAnalystReport(ticker)

// Backtest API
backtest.getSummary()

// Portfolio API
portfolio.getWatchlist()
portfolio.addToWatchlist(ticker)
portfolio.removeFromWatchlist(ticker)
```

## Features

- Dark-themed premium UI
- Responsive design
- Real-time market data integration
- Interactive charts with Recharts
- Technical analysis visualizations
- AI analyst report display
- Backtest result visualization
- Portfolio watchlist management

## Component Structure

Components are organized by domain:

- **common/** - MetricCard, LoadingState, etc.
- **charts/** - Chart wrappers for Recharts
- **dashboard/** - Dashboard-specific components
- **asset/** - Asset detail components
- **ui/** - Base UI components (buttons, cards, etc.)

## Styling

The project uses Tailwind CSS with dark mode support by default. Colors are defined in `tailwind.config.js`.

## Future Enhancements

- Real-time WebSocket integration
- Advanced technical indicators
- Portfolio tracking system
- User authentication
- Data export functionality
- Mobile app version
