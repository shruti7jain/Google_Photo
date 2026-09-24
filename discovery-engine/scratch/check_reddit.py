import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))

df = pd.read_sql("SELECT count(*) as count FROM raw_documents WHERE source = 'reddit'", engine)
print("Reddit records in raw_documents:", df.iloc[0]['count'])
