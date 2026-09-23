import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv('.env')
engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    print('--- ALL CLUSTERS WITH FAILURE MODES & DOC COUNTS ---')
    df_all = pd.read_sql('SELECT cluster_id, label, primary_failure_mode, doc_count, opportunity_score, severity_score, volume_score FROM clusters ORDER BY doc_count DESC', conn)
    for idx, row in df_all.iterrows():
        print(f"ID={row['cluster_id']:2d} | docs={row['doc_count']:3d} | opp={row['opportunity_score']:5.1f} | mode={row['primary_failure_mode']:25s} | label={row['label']}")

    print('--- REFINED TOP 5 SEARCH BREAKDOWN CLUSTERS ---')
    q = """
    SELECT 
        cluster_id, label, summary, primary_failure_mode, 
        doc_count, volume_score, severity_score, opportunity_score
    FROM clusters
    WHERE primary_failure_mode IN ('search_vocabulary_mismatch', 'no_album_structure', 'search_ux_breakdown', 'wrong_confidence_signal')
      AND label NOT ILIKE '%%positive%%'
      AND label NOT ILIKE '%%praise%%'
      AND label NOT ILIKE '%%filler%%'
      AND label NOT ILIKE '%%hindi%%'
      AND label NOT ILIKE '%%bot/spam%%'
    ORDER BY doc_count DESC
    LIMIT 5
    """
    df = pd.read_sql(q, conn)
    clusters = df.to_dict('records')
    total_breakdown = sum(c['doc_count'] for c in clusters)
    print(f"Total breakdown volume: {total_breakdown}")
    for idx, c in enumerate(clusters):
        share = (c['doc_count'] / total_breakdown) * 100
        print(f"#{idx+1}: {c['label']} | docs={c['doc_count']} | share={share:.1f}% | opp={c['opportunity_score']:.1f}")

    print('--- RAW_DOCUMENTS METADATA SAMPLES ---')
    r_meta = conn.execute(text("SELECT source, metadata FROM raw_documents WHERE metadata IS NOT NULL LIMIT 5")).fetchall()
    for row in r_meta:
        print(f"Source: {row[0]}, Meta: {row[1]}")
    
    print('\n--- RAW_DOCUMENTS COUNT BY SOURCE ---')
    df_s = pd.read_sql('SELECT source, COUNT(*), SUM(CASE WHEN is_duplicate = False THEN 1 ELSE 0 END) as non_dup FROM raw_documents GROUP BY source', conn)
    print(df_s.to_string())

    print('\n--- SEARCHING FOR SALT PATROL ---')
    res = conn.execute(text("SELECT id, source, text, date FROM raw_documents WHERE text ILIKE '%Salt Patrol%'")).fetchall()
    for r in res:
        print(f"ID={r[0]}, Source={r[1]}, Date={r[3]}")
        print(f"Text: {r[2][:200]}...")
