from app.db.session import SessionLocal
from sqlalchemy import text

q = """
SELECT tag, COUNT(*) AS c
FROM (
  SELECT unnest(COALESCE(normalized_gameplay_tags, ARRAY[]::text[])) AS tag
  FROM games
) t
WHERE tag IS NOT NULL AND length(tag) > 0
GROUP BY tag
ORDER BY c DESC, tag ASC
LIMIT 80
"""

with SessionLocal() as s:
    rows = s.execute(text(q)).all()
    for tag, c in rows:
        print(f"{tag}\t{c}")
