def summarize_checkpoint(record: dict) -> dict:
    """Return a small, validated view of a DEXTER HERMES task checkpoint.

    ``verification_pending`` compares the verified SHA with the last observed
    SHA. It does not validate CI and cannot account for a newer Git HEAD.
    The function does not change ``record`` or reveal the contents of blockers.
    """
    if not isinstance(record, dict):
        raise ValueError("Checkpoint must be a dictionary")
    required = (
        "task_id", "project", "status", "next_action", "blockers",
        "last_observed_commit", "last_verified_commit",
    )
    for field in required:
        if field not in record:
            raise ValueError("Missing checkpoint field: " + field)
    for field in ("task_id", "project", "next_action"):
        value = record[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError("Invalid checkpoint text field: " + field)
    if record["status"] not in ("planned", "in_progress", "blocked", "completed"):
        raise ValueError("Invalid checkpoint status")
    blockers = record["blockers"]
    if not isinstance(blockers, list) or not all(isinstance(item, str) for item in blockers):
        raise ValueError("Blockers must be a list of strings")
    commits = {}
    for field in ("last_observed_commit", "last_verified_commit"):
        value = record[field]
        if value is None or value == "":
            commits[field] = None
        elif (
            not isinstance(value, str) or len(value) < 7 or len(value) > 64
            or not all(char in "0123456789abcdefABCDEF" for char in value)
        ):
            raise ValueError("Invalid checkpoint commit: " + field)
        else:
            commits[field] = value.lower()
    return {
        "task_id": record["task_id"].strip(),
        "project": record["project"].strip(),
        "status": record["status"],
        "next_action": record["next_action"].strip(),
        "blockers_count": len(blockers),
        "verification_pending": (
            commits["last_verified_commit"] != commits["last_observed_commit"]
        ),
    }
