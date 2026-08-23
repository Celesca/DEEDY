# FastAPI Migration Design Spec

## Architecture & Goal
Migrate MiroFish backend from Flask to FastAPI for async I/O performance and WebSocket readiness.

## Decisions Made
- **Approach:** 1:1 REST Migration (Option A) to ensure core stability before introducing WebSockets.
- **Entry Point:** Use `backend/run.py` to programmatically launch Uvicorn. Clean up `backend/main.py`.

## Proposed Changes
1. **`backend/run.py`:** Update to launch Uvicorn (`uvicorn.run("app:app")`).
2. **`backend/app/__init__.py`:** Initialize `FastAPI()` instance and include `CORSMiddleware`.
3. **`backend/app/api/`:** Replace Flask `Blueprint` with FastAPI `APIRouter`. Refactor endpoints.
4. **`backend/app/utils/locale.py`:** Adapt locale logic to FastAPI Dependencies.

## Verification
- Start FastAPI server using `python backend/run.py`.
- Verify HTTP requests succeed without 500 errors.
- Confirm Swagger UI is accessible at `http://localhost:5001/docs`.
