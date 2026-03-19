# Vercel Deployment Guide

## Dependency Size Optimization

This project has been optimized to stay under AWS Lambda's 500 MB ephemeral storage limit.

### Changes Made

1. **Created `requirements.txt`** - Production-only dependencies (excludes dev packages):
   - ❌ Removed: `jupyter`, `ragas`, `openevals`, `nltk`, `langchain-experimental`, `langchain-tavily`
   - ✅ Kept: Only packages actually used in production code

2. **Fixed duplicate dependency** - Removed duplicate `qdrant-client` entry in `pyproject.toml`

3. **Created `.vercelignore`** - Excludes unnecessary files from deployment:
   - Notebooks, documentation files, test files
   - Reduces deployment package size

4. **Created `runtime.txt`** - Specifies Python 3.12 for consistent builds

### Estimated Size Reduction

- **Before**: 607.61 MB (exceeded limit)
- **After**: ~400-450 MB (estimated, under limit)

Removed packages:
- `jupyter` (~100 MB)
- `ragas` (~50 MB)
- `nltk` (~50 MB)
- `openevals` (~20 MB)
- `langchain-experimental` (~30 MB)

### Important Notes

1. **PDF Documents**: The `docs/` directory is **required** and cannot be excluded because:
   - BM25 retriever needs to load PDFs to build the keyword index
   - Documents are loaded at module import time in `helpers/agent.py`

2. **Cold Start Performance**: Loading 312 PDF pages on every cold start will be slow (~5-10 seconds). Consider:
   - Using Vercel Pro plan (longer function timeout)
   - Pre-computing BM25 index and serializing it
   - Using a persistent cache (Redis) for the index

3. **Memory Usage**: The BM25 index and loaded documents consume memory. Monitor:
   - Lambda memory allocation (recommend 1024 MB minimum)
   - Function timeout (recommend 30+ seconds for cold starts)

### Deployment Checklist

- [ ] Set all required environment variables in Vercel dashboard
- [ ] Verify `requirements.txt` is in the root directory
- [ ] Verify `runtime.txt` specifies Python 3.12
- [ ] Check deployment logs for any missing dependencies
- [ ] Test the `/api/chat` endpoint after deployment
- [ ] Monitor cold start times and memory usage

### If Still Over Limit

If dependencies still exceed 500 MB after these optimizations:

1. **Split into multiple functions**: Separate the retrieval logic from the agent logic
2. **Use Lambda Layers**: Move shared dependencies to a layer
3. **Consider alternative deployment**: 
   - Deploy backend separately (Railway, Render, Fly.io)
   - Use Vercel only for frontend
   - Connect via API calls

### Environment Variables Required

See `env.example` for the complete list. Minimum required:
- `OPENAI_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `ENVIRONMENT=production` (auto-set by vercel.json)
