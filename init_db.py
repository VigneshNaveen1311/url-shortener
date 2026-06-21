import time
from db import get_connection

for i in range(20):
    try:
        conn = get_connection()
        break
    except Exception as e:
        print(f"Waiting for Postgres... ({i+1}/20)")
        time.sleep(2)
else:
    raise Exception("Could not connect to Postgres")

cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS urls(
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    click_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW()
);
""")

conn.commit()
cur.close()
conn.close()

print("urls table ready")