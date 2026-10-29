from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import db_pool
from app.routers import (
    auth,
    get_actions,
    get_all_users,
    get_approvals,
    get_roles,
    get_user,
    grants_create,
    grants_revoke,
    jobs_action,
    jobs_approvals,
    jobs_history,
    jobs_waiting,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the database connection pool."""
    db_pool.open()
    yield
    db_pool.close()


app = FastAPI(
    title="NFPL Access Control API",
    version="1.0.0",
    description="Role-based access control service with scoped grants, SoD, and approvals.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(auth.router)
app.include_router(get_user.router)
app.include_router(get_all_users.router)
app.include_router(jobs_waiting.router)
app.include_router(jobs_action.router)
app.include_router(jobs_approvals.router)
app.include_router(jobs_history.router)
app.include_router(grants_create.router)
app.include_router(grants_revoke.router)
app.include_router(get_roles.router)
app.include_router(get_actions.router)
app.include_router(get_approvals.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Access Control Service Running"}
