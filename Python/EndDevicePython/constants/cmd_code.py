"""
    Initialization Code:
    -> INIT: Initialize device with these parameters

    Reply Codes to send:
    -> Main Phase:
        OK : Ready for file transfer (sufficient free space)
        FA : Failed somehow (find use for this)
        NO : Not enough disk space

    -> End Phase:
        ACK : Files received successfully (hashsum matches)
        NEQ : Files hashsum doesn't match
"""

INIT = 'INIT'

OK = 'OK'
FAILED = 'FA'
INSUFFICIENT_DISK = 'NO'

ACK = 'ACK'
HASHSUM_MISMATCH = 'NEQ'
