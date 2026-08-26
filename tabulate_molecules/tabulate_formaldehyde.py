import json
import re
import pandas as pd
from pathlib import Path

PARSED_OUTPUT_DIR = Path(
    r"D:\Quantum Computing\CDAC Internship 2026\Python GAMESS DFT Jupyter\Parsed Output Files")

def create_results_table_formaldehyde():
    rows = []
    for json_file in sorted(PARSED_OUTPUT_DIR.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        job_name = json_file.stem
        if bool(re.search(r"formaldehyde.*", job_name)):
            rows.append({
                "Job": job_name,
                "Method": data["method"],
                "Basis": data["basis"],
                "SCF Converged": data["scf_converged"],
                "SCF Iterations": data["scf_iterations"],
                "Total Energy (Hartree)": data["total_energy"],
                "Nuclear Repulsion (Hartree)": data["nuclear_repulsion_energy"],
                "Exchange-Correlation (Hartree)": data["exchange_correlation_energy"],
                "Electron Number": data["electron_number"]
            })
    df = pd.DataFrame(rows)
    return df