import csv


def fix_text(s: str) -> str:
    try:
        return s.encode("cp1252").decode("utf-8")
    except Exception:
        return s


def fix_csv(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.reader(f_in)
        rows = []

        for row in reader:
            fixed_row = [fix_text(cell) for cell in row]
            rows.append(fixed_row)

    with open(output_file, "w", encoding="utf-8-sig", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerows(rows)

fix_csv("data/mitsubishi-asx.csv", "data/mitsubishi-asx-fixed.csv")