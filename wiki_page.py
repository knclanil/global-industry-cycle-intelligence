"""Retained documentation browser for aggregate market intelligence."""
from pathlib import Path
import streamlit as st
ROOT=Path(__file__).resolve().parent/'wiki'
DOCS={{'Overview': 'WIKI_HOME.md', 'Knowledge Graphs': 'KNOWLEDGE_GRAPH_WIKI.md', 'Global Countries': 'COUNTRIES_WIKI.md', 'Global Assets': 'GLOBAL_ASSET_WIKI.md', 'Global Sectors': 'GLOBAL_WIKI.md', 'Global Factors': 'GLOBAL_FACTORS_WIKI.md', 'USA Assets': 'USA_ASSET_WIKI.md', 'USA Sectors': 'WIKI.md', 'USA Factors': 'USA_FACTORS_WIKI.md', 'India Assets': 'INDIA_ASSET_WIKI.md', 'India Sectors': 'INDIA_WIKI.md', 'India Factors': 'INDIA_FACTORS_WIKI.md'}}
def render_wiki():
 st.title('Market Intelligence Wiki')
 selection=st.selectbox('Documentation for',list(DOCS),key='wiki_section')
 path=ROOT/DOCS[selection]
 if path.is_file():
  st.markdown(path.read_text(encoding='utf-8'))
 else:
  st.warning(f'Documentation unavailable: {DOCS[selection]}')
