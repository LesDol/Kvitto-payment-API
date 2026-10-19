from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, SessionLocal, engine
from app.routers import router
from app.services import seed_tariffs


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_tariffs(session)
    yield


app = FastAPI(title="Kvitto Payments API", lifespan=lifespan)
app.include_router(router)
