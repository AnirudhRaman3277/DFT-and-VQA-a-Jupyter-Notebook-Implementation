import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GAMESS_DIR = Path(os.getenv("GAMESS_DIR"))
INPUT_DIR = Path(os.getenv("INPUT_DIR"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR"))
PARSED_OUTPUT_DIR = Path(os.getenv("PARSED_OUTPUT_DIR"))