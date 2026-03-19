# Dependency Size Optimization Notes

## Current Status
After removing BM25, PDF loading, and langchain-community, the application is still ~607 MB, exceeding Lambda's 500 MB limit.

## Removed Dependencies
- ✅ `langchain-community` (~200-300 MB) - Not used in production code
- ✅ `langsmith` (~50 MB) - Made optional (commented out in requirements.txt)
- ✅ `langgraph-checkpoint-redis` (~20 MB) - Made optional (only needed if REDIS_URL is set)
- ✅ `rank-bm25` and `rapidfuzz` - Removed with BM25
- ✅ `pypdf` - No longer needed (no PDF loading at runtime)

## Remaining Large Dependencies
The following packages are likely the main contributors to size:

1. **langchain** (~100-150 MB) - Core framework, required
2. **langgraph** (~50-100 MB) - Agent orchestration, required
3. **qdrant-client** (~30-50 MB) - Vector database client, required
4. **pydantic** (~20-30 MB) - Data validation, required by FastAPI
5. **fastapi + uvicorn** (~20-30 MB) - Web framework, required
6. **langchain-qdrant** (~10-20 MB) - Qdrant integration, required
7. **langchain-classic** (~10-20 MB) - Parent-child retriever, required
8. **tavily** (~10-20 MB) - Web search, required

## Potential Solutions

### Option 1: Verify langchain-qdrant doesn't require langchain-community
If `langchain-qdrant` has `langchain-community` as a dependency, removing it from requirements.txt won't help - it will be installed anyway. Check with:
```bash
pip show langchain-qdrant
```

### Option 2: Use Vercel Build Optimization
Vercel might be installing all dependencies including dev ones. Ensure:
- `.vercelignore` is properly configured
- Only `requirements.txt` is used (not `pyproject.toml`)
- Build logs show what's being installed

### Option 3: Split Application
- Deploy backend separately (Railway, Render, Fly.io)
- Use Vercel only for frontend
- Connect via API calls

### Option 4: Use Lambda Layers
Split dependencies across multiple Lambda layers (if using AWS Lambda directly, not Vercel)

### Option 5: Container Deployment
Use Vercel's container support (if available) which has higher limits than serverless functions

## Next Steps
1. Check if `langchain-qdrant` requires `langchain-community` as a dependency
2. Review Vercel build logs to see actual package sizes
3. Consider if any remaining packages can be replaced with lighter alternatives
4. If still over limit, consider splitting the application architecture
