import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("Falta DATABASE_URL en .env")
        # Algunos alojamientos entregan MySQL como mysql://...; el proyecto
        # usa PyMySQL, así que especificamos el driver sin alterar la URL local.
        if url.startswith("mysql://"):
            url = "mysql+pymysql://" + url[len("mysql://"):]
        _engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800)
    return _engine
