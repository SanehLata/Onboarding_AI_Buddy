pip install -r requirements.txt
python data/seeds/gen_docs.py       # validate all 21 docs exist
python data/seeds/gen_db.py         # create SQLite DB + seed developers
python data/seeds/embed_docs.py     # chunk → embed → store in ChromaDB
streamlit run app/main.py           # launch the app
```

One dependency note — `embed_docs.py` needs these packages in your `requirements.txt`:
```
langchain
langchain-text-splitters
langchain-huggingface
langchain-chroma
chromadb
sentence-transformers