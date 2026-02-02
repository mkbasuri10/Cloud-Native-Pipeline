from __future__ import annotations

import argparse
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import approx_count_distinct, col, count, to_date, to_timestamp

from dataflow_analytics.config import settings
from dataflow_analytics.storage import S3Storage


def build_spark(app_name: str = "dataflow-transform") -> SparkSession:
    return (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        # Workaround for Java 21+ security manager restriction in Hadoop/Spark
        .config("spark.driver.extraJavaOptions", "-Djava.security.manager=allow")
        .config("spark.executor.extraJavaOptions", "-Djava.security.manager=allow")
        .getOrCreate()
    )


def transform_events(spark: SparkSession, input_path: Path):
    df = spark.read.json(str(input_path))
    df = df.withColumn("event_ts", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ssX"))
    df = df.withColumn("event_date", to_date(col("event_ts")))
    agg = (
        df.groupBy("event_date", "event_type")
        .agg(
            count("*").alias("event_count"),
            approx_count_distinct("user_id").alias("unique_users"),
        )
        .orderBy("event_date", "event_type")
    )
    return agg


def write_metrics_jsonl(agg_df, output_dir: Path) -> Path:
    metrics_dir = output_dir / "metrics_by_day"
    agg_df.coalesce(1).write.mode("overwrite").json(str(metrics_dir))
    part_files = list(metrics_dir.glob("part-*.json"))
    if not part_files:
        raise FileNotFoundError("Spark did not output any part files")
    return part_files[0]


def run_job(input_path: Path, output_dir: Path, storage: S3Storage) -> Path:
    spark = build_spark()
    try:
        agg_df = transform_events(spark, input_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        part_file = write_metrics_jsonl(agg_df, output_dir)
        storage.upload_file(part_file, storage.key("metrics_by_day.jsonl"))
        return part_file
    finally:
        spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform raw event data into aggregated metrics.")
    parser.add_argument("--input", type=Path, default=settings.raw_events_path)
    parser.add_argument("--output-dir", type=Path, default=settings.tmp_dir / "spark-output")
    parser.add_argument("--bucket", type=str, default=settings.s3_bucket)
    parser.add_argument("--prefix", type=str, default=settings.s3_prefix)
    args = parser.parse_args()

    storage = S3Storage(bucket=args.bucket, prefix=args.prefix)
    part_file = run_job(args.input, args.output_dir, storage)
    print(f"Uploaded metrics from {part_file} to s3://{storage.bucket}/{storage.key('metrics_by_day.jsonl')}")


if __name__ == "__main__":
    main()
