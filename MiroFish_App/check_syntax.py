import ast
import glob
import sys
import traceback

def check_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code, filename=filepath)
        print(f"Syntax OK: {filepath}")
        return True
    except SyntaxError as e:
        print(f"Syntax ERROR in {filepath}:")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Other ERROR in {filepath}: {e}")
        return False

files = [
    "backend/core/agent.py",
    "backend/core/environment.py",
    "backend/core/population.py",
    "backend/app/api/simulation.py",
    "backend/scripts/run_thai_society_simulation.py"
]

all_ok = True
for f in files:
    if not check_file(f):
        all_ok = False

sys.exit(0 if all_ok else 1)
