from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from db import get_connection
from redis import Redis
import random, string
import os

SERVER = os.getenv("SERVER", "Unknown")

app = FastAPI()
r = Redis(host="redis", port=6379, db=0, decode_responses=True)


class UrlRequest(BaseModel):
    url: str
    custom_alias: str | None = Field(default=None, example=None)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "server": SERVER
    }

def generate_short_code(length: int =5):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def update_analytics(short_code):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
                UPDATE urls
                SET click_count = click_count+1,
                    last_accessed = NOW()
                WHERE short_code = %s;
                """, (short_code,))
    conn.commit()
    cur.close()
    conn.close()

@app.post("/shorten")
def shorten_url(data: UrlRequest):
    conn = get_connection()
    cur = conn.cursor()
    url = data.url

    if not url.startswith(("http://", "https://")):
        url = "https://"+url

    while True:
        if data.custom_alias and data.custom_alias != "string":
            short_code = data.custom_alias
        else:
            short_code = generate_short_code()
        cur.execute("""INSERT INTO urls (short_code, original_url)
                    VALUES (%s, %s)
                    ON CONFLICT (short_code) DO NOTHING""",
                    (short_code, url))
        
        if cur.rowcount == 1:
            conn.commit()
            break
        elif data.custom_alias:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=409,
                detail="Alias already exists"
            )

    cur.close()
    conn.close()

    return {
        "short_code": short_code,
        "short_url": f"http://localhost:8000/{short_code}"
    }

@app.get("/{short_code}")
def redirect_to_url(short_code: str):
    print("SHORT CODE RECEIVED =", repr(short_code), flush=True)
    cached_url = r.get(short_code)
    if  cached_url is not None:
        print("CACHE HIT")
        update_analytics(short_code)
        return RedirectResponse(url = cached_url)
    print("CACHE MISS")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("select current_database()")
    print(cur.fetchone())

    cur.execute("SELECT original_url FROM urls WHERE short_code = %s",
                (short_code,))
    
    row = cur.fetchone()

    cur.close()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Short url not found")
    else:
        r.set(short_code, row[0], ex=60)
        update_analytics(short_code)
        return RedirectResponse(url=row[0])
