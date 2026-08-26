import re
import json
from pathlib import Path
from config import OUTPUT_DIR, PARSED_OUTPUT_DIR

def parse_gamess(job_name):

    # Read GAMESS Output

    output_file = OUTPUT_DIR / f"{job_name}.txt"

    if not output_file.exists():
        raise FileNotFoundError(
            f"GAMESS output file not found:\n{output_file}"
        )

    text = output_file.read_text(
        encoding="utf-8",
        errors="replace"
    )

    # Result Structure

    results = {
        "method": None,
        "basis": None,

        "scf_converged": False,
        "scf_iterations": None,

        "total_energy": None,
        "nuclear_repulsion_energy": None,
        "exchange_correlation_energy": None,

        "energy_components": {},

        "electron_number": None,

        "orbital_energies": [],
        "occupied_orbital_energies": [],
        "virtual_orbital_energies": [],

        "homo_energy": None,
        "lumo_energy": None,
        "homo_lumo_gap": None,

        "geometry": [],

        "mulliken_charges": {},

        "dipole_x": None,
        "dipole_y": None,
        "dipole_z": None,
        "dipole_magnitude": None
    }


    # Method

    match = re.search(
        r"DFTTYP=([A-Z0-9]+)",
        text,
        re.IGNORECASE
    )

    if match:
        results["method"] = match.group(1).upper()


    # Basis

    basis_match = re.search(
        r"GBASIS=N31\s+IGAUSS=\s*(\d+)"
        r"\s+POLAR=\S+\s+NDFUNC=\s*(\d+)"
        r"\s+NFFUNC=\s*(\d+)\s+DIFFSP=\s*([TF])"
        r"\s+NPFUNC=\s*(\d+)\s+DIFFS=\s*([TF])",
        text,
        re.IGNORECASE
    )

    if basis_match:

        ngauss = int(basis_match.group(1))
        ndfunc = int(basis_match.group(2))
        npfunc = int(basis_match.group(5))

        basis = f"6-{ngauss}1G"

        if ndfunc:
            basis += "(d"

            if npfunc:
                basis += ",p"

            basis += ")"

        elif npfunc:
            basis += "(p)"

        results["basis"] = basis


    # SCF Iterations

    match = re.search(
        r"FINAL\s+R-[A-Z0-9]+\s+ENERGY\s+IS\s+"
        r"[-+0-9.DE]+\s+AFTER\s+(\d+)\s+ITERATIONS",
        text,
        re.IGNORECASE
    )

    if match:

        results["scf_iterations"] = int(match.group(1))
        results["scf_converged"] = True


    # Total Energy

    match = re.search(
        r"FINAL\s+R-[A-Z0-9]+\s+ENERGY\s+IS\s+"
        r"([-+0-9.DE]+)",
        text,
        re.IGNORECASE
    )

    if match:

        results["total_energy"] = float(
            match.group(1).replace("D", "E")
        )


    # Nuclear Repulsion Energy

    match = re.search(
        r"NUCLEAR\s+REPULSION\s+ENERGY\s*=\s*"
        r"([-+0-9.DE]+)",
        text,
        re.IGNORECASE
    )

    if match:

        results["nuclear_repulsion_energy"] = float(
            match.group(1).replace("D", "E")
        )


    # Exhchange-Correlation Energy

    match = re.search(
        r"DFT\s+EXCHANGE\s*\+\s*CORRELATION\s+ENERGY\s*=\s*"
        r"([-+0-9.DE]+)",
        text,
        re.IGNORECASE
    )

    if match:

        results["exchange_correlation_energy"] = float(
            match.group(1).replace("D", "E")
        )


    # Electron Number

    match = re.search(
        r"TOTAL\s+ELECTRON\s+NUMBER\s*=\s*"
        r"([-+0-9.DE]+)",
        text,
        re.IGNORECASE
    )

    if match:

        results["electron_number"] = float(
            match.group(1).replace("D", "E")
        )


    # Energy Components

    energy_patterns = {

        "one_electron_energy":
            r"ONE\s+ELECTRON\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "two_electron_energy":
            r"TWO\s+ELECTRON\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "electron_electron_potential_energy":
            r"ELECTRON-ELECTRON\s+POTENTIAL\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "nucleus_electron_potential_energy":
            r"NUCLEUS-ELECTRON\s+POTENTIAL\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "nucleus_nucleus_potential_energy":
            r"NUCLEUS-NUCLEUS\s+POTENTIAL\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "total_potential_energy":
            r"TOTAL\s+POTENTIAL\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "total_kinetic_energy":
            r"TOTAL\s+KINETIC\s+ENERGY\s*=\s*([-+0-9.DE]+)",

        "virial_ratio":
            r"VIRIAL\s+RATIO\s+\(V/T\)\s*=\s*([-+0-9.DE]+)"
    }

    for name, pattern in energy_patterns.items():

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            results["energy_components"][name] = float(
                match.group(1).replace("D", "E")
            )


    # Number of Occupied Orbitals

    occupied_match = re.search(
        r"NUMBER\s+OF\s+OCCUPIED\s+ORBITALS\s+\(ALPHA\)\s*=\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if occupied_match:
        n_occupied = int(occupied_match.group(1))
    else:
        n_occupied = None


    # Orbital Energies

    orbital_energies = []

    eigenvector_section = re.search(
        r"\n\s*EIGENVECTORS\s*\n(.*?)(?=\n\s*\.*\s*END OF RHF CALCULATION)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if eigenvector_section:

        section = eigenvector_section.group(1)

        lines = section.splitlines()

        i = 0

        while i < len(lines):

            line = lines[i]

            # GAMESS orbital-energy header.
            # Example:
            #
            # 1  2  3  4  5
            # -18.9161 -0.9346 -0.4743 -0.3215 -0.2422

            if re.match(
                r"^\s*\d+(?:\s+\d+)+\s*$",
                line
            ):

                if i + 1 < len(lines):

                    energy_line = lines[i + 1]

                    values = re.findall(
                        r"[-+]?\d+\.\d+(?:[DE][+-]?\d+)?",
                        energy_line
                    )

                    if values:

                        orbital_energies.extend(
                            float(v.replace("D", "E"))
                            for v in values
                        )

                        i += 2
                        continue

            i += 1


    results["orbital_energies"] = orbital_energies


    # Occupied Virtual Orbitals

    if n_occupied is not None and orbital_energies:

        results["occupied_orbital_energies"] = (
            orbital_energies[:n_occupied]
        )

        results["virtual_orbital_energies"] = (
            orbital_energies[n_occupied:]
        )


        # HOMO
        if results["occupied_orbital_energies"]:

            results["homo_energy"] = (
                results["occupied_orbital_energies"][-1]
            )


        # LUMO
        if results["virtual_orbital_energies"]:

            results["lumo_energy"] = (
                results["virtual_orbital_energies"][0]
            )


        # HOMO-LUMO gap
        if (
            results["homo_energy"] is not None
            and results["lumo_energy"] is not None
        ):

            results["homo_lumo_gap"] = (
                results["lumo_energy"]
                - results["homo_energy"]
            )


    # Geometry

    geometry_section = re.search(
        r"ATOMIC\s+COORDINATES\s+\(BOHR\)(.*?)(?=\n\s*INTERNUCLEAR\s+DISTANCES)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if geometry_section:

        pattern = re.compile(
            r"^\s*([A-Z][A-Za-z]?)\s+"
            r"([-+0-9.]+)\s+"
            r"([-+0-9.DE]+)\s+"
            r"([-+0-9.DE]+)\s+"
            r"([-+0-9.DE]+)",
            re.MULTILINE
        )

        for match in pattern.finditer(
            geometry_section.group(1)
        ):

            results["geometry"].append({
                "atom": match.group(1),
                "x": float(match.group(3).replace("D", "E")),
                "y": float(match.group(4).replace("D", "E")),
                "z": float(match.group(5).replace("D", "E"))
            })


    # Mulliken Atomic Charges

    mulliken_section = re.search(
        r"TOTAL\s+MULLIKEN\s+AND\s+LOWDIN\s+ATOMIC\s+POPULATIONS"
        r"(.*?)(?=\n\s*-{5,})",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if mulliken_section:

        pattern = re.compile(
            r"^\s*(\d+)\s+"
            r"([A-Z][A-Za-z]?)\s+"
            r"([-+0-9.]+)\s+"
            r"([-+0-9.]+)\s+"
            r"([-+0-9.]+)\s+"
            r"([-+0-9.]+)",
            re.MULTILINE
        )

        for match in pattern.finditer(
            mulliken_section.group(1)
        ):

            atom_number = match.group(1)
            atom = match.group(2)
            charge = float(match.group(4))

            results["mulliken_charges"][
                f"{atom}{atom_number}"
            ] = charge


    # Dipole

    dipole_match = re.search(
        r"DX\s+DY\s+DZ\s+/D/\s+\(DEBYE\)"
        r"\s*"
        r"([-+0-9.]+)\s+"
        r"([-+0-9.]+)\s+"
        r"([-+0-9.]+)\s+"
        r"([-+0-9.]+)",
        text,
        re.IGNORECASE
    )

    if dipole_match:

        results["dipole_x"] = float(
            dipole_match.group(1)
        )

        results["dipole_y"] = float(
            dipole_match.group(2)
        )

        results["dipole_z"] = float(
            dipole_match.group(3)
        )

        results["dipole_magnitude"] = float(
            dipole_match.group(4)
        )


    # Save JSON

    parsed_file = PARSED_OUTPUT_DIR / f"{job_name}.json"

    with open(
        parsed_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=4
        )


    return results