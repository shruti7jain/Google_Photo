import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # 1. Clean up irrelevant reddit documents
    print("Marking irrelevant reddit documents as is_duplicate = True...")
    res = conn.execute(text("UPDATE raw_documents SET is_duplicate = True WHERE source = 'reddit'"))
    conn.commit()
    print(f"Updated {res.rowcount} reddit documents to is_duplicate = True.")

    # Also delete or clean any processed or tagged documents linked to reddit spam
    for tbl in ['processed_documents', 'tagged_documents']:
        try:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tbl} WHERE source = 'reddit'")).scalar()
            print(f"Table {tbl} has {cnt} reddit records.")
            if cnt > 0:
                conn.execute(text(f"DELETE FROM {tbl} WHERE source = 'reddit'"))
                conn.commit()
                print(f"Cleaned reddit records from {tbl}.")
        except Exception as e:
            print(f"Error checking {tbl}: {e}")

    # 3. Test genuine search reviews query
    query_search_reviews = """
    SELECT DISTINCT ON (text)
        source, text, rating, date
    FROM raw_documents
    WHERE is_duplicate = False
      AND rating IS NOT NULL
      AND (
          text ILIKE '%%search%%' OR text ILIKE '%%find%%' OR 
          text ILIKE '%%album%%' OR text ILIKE '%%face%%' OR 
          text ILIKE '%%date%%' OR text ILIKE '%%scroll%%' OR
          text ILIKE '%%tag%%' OR text ILIKE '%%photo%%'
      )
      AND LENGTH(text) >= 30
      AND text NOT ILIKE '%%guild%%'
      AND text NOT ILIKE '%%discord%%'
    ORDER BY text, date DESC NULLS LAST
    LIMIT 20
    """
    df_rev = pd.read_sql(query_search_reviews, conn)
    print(f"\nFetched {len(df_rev)} sample real search reviews:")
    for idx, r in df_rev.head(5).iterrows():
        print(f"[{idx+1}] [{r['source']}] {r['rating']}★ ({r['date']}): {r['text'][:120]}...")
