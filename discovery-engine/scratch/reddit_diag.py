import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

# 1. Total raw documents in the database
total_raw = pd.read_sql("SELECT COUNT(*) FROM raw_documents", engine).iloc[0,0]

# 2. Raw Reddit records
raw_reddit = pd.read_sql("SELECT COUNT(*) FROM raw_documents WHERE source = 'reddit'", engine).iloc[0,0]

# 3. Clean Reddit records (is_duplicate = False)
clean_reddit = pd.read_sql("SELECT COUNT(*) FROM raw_documents WHERE source = 'reddit' AND is_duplicate = False", engine).iloc[0,0]

# 4. Search-relevant Reddit records (using the pipeline logic, or just checking what made it through if we have a table for it)
# The pipeline filters search-relevant by looking for keywords like 'search', 'find', 'album', 'face', 'date' etc.
search_relevant_query = """
SELECT COUNT(*) FROM raw_documents 
WHERE source = 'reddit' AND is_duplicate = False 
  AND rating <= 3 
  AND rating >= 1 
  AND (text ILIKE '%%search%%' OR text ILIKE '%%find%%' OR text ILIKE '%%album%%')
"""
# Note: rating for reddit in our pipeline might be null or default to 1. Let's see if rating filter excludes them.
reddit_ratings = pd.read_sql("SELECT DISTINCT rating FROM raw_documents WHERE source = 'reddit'", engine)

# Let's get Reddit URLs or context
reddit_sample = pd.read_sql("SELECT text FROM raw_documents WHERE source = 'reddit' LIMIT 5", engine)
subreddits = []
for text in reddit_sample['text']:
    # The text we saw earlier had "[link]" and "/u/something"
    pass

# 5 & 6. Retrieval-relevant and vague memory
retrieval_reddit = pd.read_sql("SELECT COUNT(*) FROM tagged_documents WHERE source = 'reddit'", engine).iloc[0,0]

print(f"Total raw in DB: {total_raw}")
print(f"Raw Reddit: {raw_reddit}")
print(f"Clean Reddit: {clean_reddit}")
print(f"Reddit ratings present: {reddit_ratings['rating'].tolist()}")
print(f"Retrieval relevant Reddit (in tagged_documents): {retrieval_reddit}")

# Print samples to identify subreddit/URL format
print("\nSample snippets:")
for t in reddit_sample['text'].tolist():
    print(t[:100].encode('ascii', 'ignore').decode('ascii'))
