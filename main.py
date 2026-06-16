from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from db import get_connection
import random, string

app = FastAPI()


class UrlRequest(BaseModel):
    url: str


def generate_short_code(length: int =5):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

@app.post("/shorten")
def shorten_url(data: UrlRequest):
    conn = get_connection()
    cur = conn.cursor()
    url = data.url

    if not url.startswith(("http://", "https://")):
        url = "https://"+url

    while True:
        short_code = generate_short_code()
        cur.execute("""INSERT INTO urls (short_code, original_url)
                    VALUES (%s, %s)
                    ON CONFLICT (short_code) DO NOTHING""",
                    (short_code, url))
        
        if cur.rowcount == 1:
            conn.commit()
            break
        else:
            print("rollingback")
            conn.rollback()
            continue

    cur.close()
    conn.close()

    return {
        "short_code": short_code,
        "short_url": f"http://localhost:8000/{short_code}"
    }

@app.get("/{short_code}")
def redirect_to_url(short_code: str):
    print("SHORT CODE RECEIVED =", repr(short_code), flush=True)
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
        return RedirectResponse(url=row[0])