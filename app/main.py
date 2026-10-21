from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import db_pool
from app.scripts import auth, jobs
from app.scripts import grants

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

# Register routers from the scripts directory
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(grants.router)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Access Control Service Running"}