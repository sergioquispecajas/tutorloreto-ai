from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.adapters.entrada.api import router
from app.adapters.entrada.auth_api import router as auth_router

app=FastAPI(title="TutorLoreto AI - PMV1, PMV2 y PMV3")
app.include_router(router,prefix="/api")
app.include_router(auth_router,prefix="/api/auth")


@app.get("/healthz", include_in_schema=False)
def health_check():
    """Endpoint liviano para comprobar que el proceso web está activo."""
    return {"status": "ok"}


app.mount("/",StaticFiles(directory="frontend",html=True),name="frontend")
