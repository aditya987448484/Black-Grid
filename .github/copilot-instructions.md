# Axiom Terminal - Development Instructions

This is a full-stack AI-powered financial research platform for stocks, ETFs, bond proxies, and commodities.

## Project Structure
- **Frontend**: Next.js 14+ with TypeScript, Tailwind CSS, shadcn/ui, Framer Motion
- **Backend**: FastAPI (Python) with pandas, numpy, ML-ready structure
- **Charts**: Recharts
- **Database**: PostgreSQL (production), SQLite (dev)

## Tech Stack

### Frontend
- Next.js 14+
- TypeScript
- Tailwind CSS
- shadcn/ui components
- Framer Motion for animations
- Recharts for visualizations
- Axios for API calls

### Backend
- FastAPI
- Pydantic for validation
- SQLAlchemy for ORM
- pandas & numpy for data processing
- Python 3.10+

## Key Features
- Dark-themed premium UI
- Real-time market data dashboards
- AI-generated analyst reports
- Backtesting engine
- Portfolio monitoring
- Technical analysis tools

## Development Workflow
1. Frontend runs on `localhost:3000`
2. Backend API runs on `localhost:8000`
3. All API calls proxied through Next.js during development
4. Mock data available for rapid iteration

## Important Notes
- Production-style architecture
- Modular, reusable components
- Clean separation of concerns
- Type-safe throughout
- ML integration ready for future PyTorch models
