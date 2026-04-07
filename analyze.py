from pathlib import Path
import sys

# ensure local scraper package is importable
sys.path.insert(0, str(Path(__file__).parent / "otomoto-scraper"))

from analytics import save_query_analysis


def run_all():
    data_dir = Path("data/otomoto")
    csvs = list(data_dir.glob("*.csv"))
    if not csvs:
        print("No CSV files found in data/otomoto")
        return

    for csv_file in csvs:
        query_name = csv_file.stem
        print("---\nAnalysing:", csv_file)
        out_path, results = save_query_analysis(query_name, str(csv_file))
        print("Saved analysis:", out_path)
        print(f"Total results: {len(results)}")
        for r in results[:10]:
            print(f'{r.listing_id} | {r.final_score} | {r.market_score} | {r.decision_bucket} | {r.title}')


if __name__ == "__main__":
    run_all()
