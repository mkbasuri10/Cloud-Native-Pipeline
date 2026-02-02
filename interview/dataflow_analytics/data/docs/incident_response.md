# Incident Response Runbook

If ingestion latency exceeds 15 minutes, verify the streaming backlog and check the Spark job logs.
Restart the transformer if the job is stuck, then reprocess the latest raw events from S3.
Escalate to the on-call engineer if error rates exceed 2% for more than 10 minutes.
