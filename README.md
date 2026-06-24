# OpenCrime

Open-source platform for public crime intelligence — transforming fragmented FIRs and police records into structured, searchable, privacy-preserving data.

## Architecture

| Component | Technology |
|-----------|-----------|
| Backend API | Python 3.11, FastAPI |
| Database | PostgreSQL 16 + pgvector |
| Task Queue | Celery + Redis |
| OCR | Tesseract + pdf2image |
| AI Processing | Anthropic Claude (claude-sonnet-4-6) |
| Full-text Search | PostgreSQL tsvector |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Charts | Recharts |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Anthropic API key (optional but required for AI extraction)

### 1. Clone and configure

```bash
git clone https://github.com/meranamvarun/opencrime
cd opencrime
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### 2. Start all services

```bash
docker-compose up -d
```

Services:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs

### 3. Seed sample data (optional)

```bash
docker-compose exec backend python seed.py
```

## API Endpoints

### Documents
- `POST /api/v1/documents/upload` — Upload a crime document (PDF/image)
- `GET /api/v1/documents/{id}` — Get document processing status
- `GET /api/v1/documents/{id}/record` — Get the extracted crime record

### Search
- `GET /api/v1/search?q=cyber+fraud` — Full-text search
- Query params: `crime_category`, `state`, `district`, `date_from`, `date_to`, `min_amount`, `max_amount`, `page`, `page_size`

### Analytics
- `GET /api/v1/analytics/summary` — Aggregate statistics
- `GET /api/v1/analytics/records` — Paginated record list
- `GET /api/v1/analytics/records/{id}` — Single record detail
- `GET /api/v1/analytics/map` — Records with coordinates for map view

## Document Processing Pipeline

```
Upload PDF/Image
      ↓
   Tesseract OCR
      ↓
 Claude AI Extraction
 (crime category, FIR number, location,
  legal sections, amount, modus operandi)
      ↓
   PII Redaction
 (names, phones, Aadhaar, addresses)
      ↓
 Summary Generation
      ↓
 Index for Search
      ↓
 Publish Record
```

## Privacy Principles

OpenCrime redacts all PII before publishing:
- Personal names (victims, accused, witnesses)
- Phone numbers
- Aadhaar / PAN / Passport numbers
- Physical addresses
- Bank account numbers
- Minor identities
- Sexual assault victim identities

## Development

### Backend only (without Docker)

```bash
cd backend
pip install -r requirements.txt
# Set DATABASE_URL and REDIS_URL in environment
uvicorn app.main:app --reload
```

### Frontend only

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## License

MIT
