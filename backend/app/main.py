from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import db_pool
from app.routers import (
    auth,
    jobs_waiting,
    jobs_action,
    jobs_approvals,
    jobs_history,
    grants_create,
    grants_revoke,
)


# Manage the lifecycle of the DB connection pool
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Open the connection pool before the app starts accepting requests
    db_pool.open()
    yield
    # Close the pool when the app shuts down
    db_pool.close()

app = FastAPI(
    title="NFPL Access Control API", 
    version="1.0.0",
    lifespan=lifespan
)

# Register routers
app.include_router(auth.router)
app.include_router(jobs_waiting.router)
app.include_router(jobs_action.router)
app.include_router(jobs_approvals.router)
app.include_router(jobs_history.router)
app.include_router(grants_create.router)
app.include_router(grants_revoke.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Access Control Service Running"}