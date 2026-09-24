import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import json

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

df = pd.read_sql("SELECT raw_text, search_behavior, failure_modes FROM tagged_documents", engine)
vague_cases = []
for row in df.to_dict('records'):
    # Look for indications of vague memory or complex retrieval in the tagged JSON
    is_vague = False
    try:
        behavior = json.loads(row['search_behavior']) if isinstance(row['search_behavior'], str) else row['search_behavior']
        failures = json.loads(row['failure_modes']) if isinstance(row['failure_modes'], str) else row['failure_modes']
        
        # Check if they mention remembering or complex filters
        if behavior:
            for b in behavior:
                if b in ['natural_language', 'keyword', 'date_filter', 'timeline_scrolling', 'album_browsing']:
                    pass # these are common
        
        text = str(row['raw_text']).lower()
        if 'remember' in text or 'years ago' in text or 'old photo' in text or 'find a specific' in text:
            is_vague = True
            
        if is_vague:
            vague_cases.append(row['raw_text'])
    except Exception as e:
        pass

print("Total tagged documents:", len(df))
print("Found vague cases in tagged set:", len(vague_cases))
if vague_cases:
    print(vague_cases[:3])
