import re
import sys
from pathlib import Path

def clean_text(text):
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    
    text = re.sub(r'[ \t]+', ' ', text)
    
    text = re.sub(r'\n\n+', '\n\n', text)
    
    text = text.replace(" ;", ";")

    return text