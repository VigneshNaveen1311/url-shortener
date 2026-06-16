from db import get_connection

conn = get_connection()

cur = conn.cursor()

cur.execute("""
create table if not exists urls(
            id serial primary key,
            short_code varchar(10) unique not null,
            original_url text not null,
            created_at timestamp default now()
)
""")
#added unique shortcode constraint in terminal for short_code
#ALTER TABLE urls ADD CONSTRAINT unique_short_code UNIQUE(short_code);
conn.commit()
cur.close()
conn.close()

print("urls Table created")