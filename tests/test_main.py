import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "otomoto-scraper"))

import main


def test_main_dry_run_does_not_call_process_query_or_enrichment(monkeypatch):
    called = {"process": 0, "enrichment": 0}

    monkeypatch.setattr(sys, "argv", ["main.py", "--dry-run", "--run-enrichment"])
    monkeypatch.setattr(main, "QUERIES", [{"name": "q1", "start_url": "u", "max_pages": 1}])
    monkeypatch.setattr(main, "process_query", lambda *args, **kwargs: called.__setitem__("process", called["process"] + 1))
    monkeypatch.setattr(main, "run_enrichment_worker", lambda **kwargs: called.__setitem__("enrichment", called["enrichment"] + 1))

    main.main()

    assert called["process"] == 0
    assert called["enrichment"] == 0


def test_main_runs_enrichment_when_flag_is_set(monkeypatch):
    called = {"process": 0, "enrichment": None}

    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "--run-enrichment", "--retry-failed-enrichment"],
    )
    monkeypatch.setattr(main, "QUERIES", [{"name": "q1", "start_url": "u", "csv_file": "x.csv", "max_pages": 1}])
    monkeypatch.setattr(main, "process_query", lambda *args, **kwargs: called.__setitem__("process", called["process"] + 1))

    def fake_enrichment(**kwargs):
        called["enrichment"] = kwargs
        return [{"status": "fetched"}]

    monkeypatch.setattr(main, "run_enrichment_worker", fake_enrichment)

    main.main()

    assert called["process"] == 1
    assert called["enrichment"] == {"retry_failed": True}
