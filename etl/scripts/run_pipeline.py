"""
ETL pipeline entry point.

    python etl/scripts/run_pipeline.py                              # initial load from etl/data/raw
    python etl/scripts/run_pipeline.py --data-dir etl/data/incremental
    python etl/scripts/run_pipeline.py --data-dir etl/data/bad_batch --jobs load_customers

For each job (in etl_jobs order):
  EXTRACT   read the CSV as text                         (extract.py)
  TRANSFORM clean formatting                             (transform.py)
  VALIDATE  row-level rules -> issues + rejected rows    (validate.py)
  LOAD      staging -> SQL reference checks -> production (load.py)
  LOG       one row in etl_execution_logs with the counts

Afterwards it calls the stored procedure sp_run_data_quality_checks for
business rules that span several tables.
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import text

from config import DEFAULT_DATA_DIR, LOG_DIR, REJECTED_DIR, get_engine
from extract import read_csv
from load import finish_execution, load_to_production, load_to_staging, save_issues, start_execution
from transform import clean
from validate import missing_columns, validate

# Which dataset rules/SQL each job uses
JOB_DATASETS = {
    "load_customers": "customers",
    "load_products": "products",
    "load_orders": "orders",
    "load_order_items": "order_items",
    "load_payments": "payments",
}

log = logging.getLogger("etl")


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_DIR / "etl.log")],
    )


def write_rejected_file(rejected, issues, dataset, execution_id):
    """Save rejected rows with their reasons so the source team can fix them."""
    if rejected.empty:
        return None
    reasons = {}
    for issue in issues:
        reasons.setdefault(issue["source_row"], []).append(issue["description"])
    out = rejected.copy()
    out["rejection_reasons"] = out["source_row"].map(lambda r: " | ".join(reasons.get(r, [])))
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    path = REJECTED_DIR / f"{dataset}_execution_{execution_id}.csv"
    out.to_csv(path, index=False)
    return path


def run_job(engine, job, data_dir: Path) -> dict:
    dataset = JOB_DATASETS[job.job_name]
    stats = {"read": 0, "inserted": 0, "updated": 0, "rejected": 0, "errors": 0}

    # Committed straight away so a RUNNING row is visible while the job works.
    with engine.begin() as conn:
        execution_id = start_execution(conn, job.job_id)
    log.info("[%s] execution %s started", job.job_name, execution_id)

    try:
        # ---------- EXTRACT ----------
        path = data_dir / job.source_file
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {path}")
        df = read_csv(path)
        stats["read"] = len(df)

        # ---------- SCHEMA CHECK: a missing column fails the whole job ----------
        missing = missing_columns(df, dataset)
        if missing:
            stats["errors"] = len(missing)
            stats["rejected"] = len(df)
            with engine.begin() as conn:
                save_issues(conn, execution_id, job.source_id, job.target_table, [{
                    "record_identifier": job.source_file, "column_name": col,
                    "rule_name": "required_columns", "issue_type": "MISSING_COLUMN",
                    "severity": "CRITICAL",
                    "description": f"File {job.source_file} has no '{col}' column - whole file rejected",
                } for col in missing])
                finish_execution(conn, execution_id, stats, "FAILED", f"Missing columns: {', '.join(missing)}")
            log.error("[%s] FAILED - missing columns %s", job.job_name, missing)
            return {**stats, "job": job.job_name, "status": "FAILED", "execution_id": execution_id}

        # ---------- TRANSFORM + VALIDATE ----------
        df, cleaned = clean(df, dataset)
        valid, rejected, issues = validate(df, dataset)
        log.info("[%s] read=%d cleaned_values=%d valid=%d rejected_by_rules=%d",
                 job.job_name, len(df), cleaned, len(valid), len(rejected))
        rejected_file = write_rejected_file(rejected, issues, dataset, execution_id)
        if rejected_file:
            log.info("[%s] rejected rows written to %s", job.job_name, rejected_file)

        # ---------- LOAD (one transaction: all or nothing) ----------
        with engine.begin() as conn:
            conn.execute(text("SET @app_user = 'etl_pipeline'"))   # shows up in audit_logs.changed_by
            save_issues(conn, execution_id, job.source_id, job.target_table, issues)
            load_to_staging(conn, dataset, valid, execution_id)
            result = load_to_production(conn, dataset, execution_id, job.source_id)

            stats["inserted"] = result["inserted"]
            stats["updated"] = result["updated"]
            stats["rejected"] = len(rejected) + result["rejected"]
            stats["errors"] = len(issues) + result["errors"]
            status = "SUCCESS" if stats["rejected"] == 0 else "PARTIAL_SUCCESS"
            finish_execution(conn, execution_id, stats, status)

        log.info("[%s] %s inserted=%d updated=%d rejected=%d issues=%d", job.job_name, status,
                 stats["inserted"], stats["updated"], stats["rejected"], stats["errors"])
        return {**stats, "job": job.job_name, "status": status, "execution_id": execution_id}

    except Exception as exc:  # anything unexpected: the load transaction was rolled back
        log.exception("[%s] FAILED", job.job_name)
        with engine.begin() as conn:
            finish_execution(conn, execution_id, stats, "FAILED", str(exc))
        return {**stats, "job": job.job_name, "status": "FAILED", "execution_id": execution_id}


def run_quality_checks(engine) -> int:
    with engine.begin() as conn:
        conn.execute(text("CALL sp_run_data_quality_checks(@issues_found)"))
        return conn.execute(text("SELECT @issues_found")).scalar()


def main():
    parser = argparse.ArgumentParser(description="Run the ETL pipeline")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="folder with the CSV files")
    parser.add_argument("--jobs", nargs="*", help="run only these jobs, e.g. load_customers load_orders")
    parser.add_argument("--skip-dq-checks", action="store_true", help="do not call sp_run_data_quality_checks")
    args = parser.parse_args()

    setup_logging()
    engine = get_engine()
    log.info("Pipeline started, data folder: %s", args.data_dir)

    with engine.connect() as conn:
        jobs = conn.execute(text(
            "SELECT job_id, job_name, source_id, source_file, target_table "
            "FROM etl_jobs WHERE is_active = TRUE ORDER BY job_id")).all()
    if args.jobs:
        jobs = [j for j in jobs if j.job_name in args.jobs]

    results = [run_job(engine, job, args.data_dir) for job in jobs]

    if not args.skip_dq_checks:
        found = run_quality_checks(engine)
        log.info("sp_run_data_quality_checks found %s new business-rule issue(s)", found)

    print("\n{:<18} {:>5} {:<16} {:>6} {:>8} {:>8} {:>8} {:>6}".format(
        "job", "exec", "status", "read", "inserted", "updated", "rejected", "issues"))
    for r in results:
        print("{job:<18} {execution_id:>5} {status:<16} {read:>6} {inserted:>8} {updated:>8} "
              "{rejected:>8} {errors:>6}".format(**r))

    return 1 if any(r["status"] == "FAILED" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
