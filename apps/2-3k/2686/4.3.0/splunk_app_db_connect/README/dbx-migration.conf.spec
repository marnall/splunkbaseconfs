[encryption]

upgrade = [NONE|PENDING|DONE]
# Defines the migration action (upgrading) for encryption algorithms
# PENDING: migration will take place after the server starts
# NONE: migration is not needed
# DONE: migration was done previously, it is skipped

downgrade = [NONE|PENDING|DONE]
# Defines the migration action (downgrading) for encryption algorithms
# PENDING: migration will take place after the server starts
# NONE: migration is not needed
# DONE: migration was done previously, it is skipped

onError = [FAIL_FAST|FAIL_SAFE]
# Defines how it behaves in case of failures during the migration
# FAIL_FAST: if there is a failure, the migration is stopped and the changes are rolled back
# FAIL_SAFE: if there is a failure, the migration continues and the changes remain
