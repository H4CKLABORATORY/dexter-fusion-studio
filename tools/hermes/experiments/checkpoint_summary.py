def summarize_checkpoint(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError('Input must be a dictionary')
    if 'task_id' not in record or 'project' not in record or 'status' not in record or 'next_action' not in record or 'blockers' not in record or 'last_observed_commit' not in record or 'last_verified_commit' not in record:
        raise ValueError('Missing required fields in the checkpoint')
    return {'task_id': record['task_id'], 'project': record['project'], 'status': record['status'], 'next_action': record['next_action'], 'blockers_count': len(record['blockers']), 'verification_pending': record['last_verified_commit'] is None}
