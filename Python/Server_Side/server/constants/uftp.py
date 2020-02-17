import server.constants.paths as paths

PORT_NUMBER = '1044'  # Default from the UFTP manual
PUB_MULTICAST_ADDR = '230.4.4.1'  # Default from the UFTP manual
# Default from the UFTP manual, the 'x' will be randomized
PRIV_MULTICAST_ADDR = '230.5.5.x'
END_DEVICE_MULTICAST_ADDR = '230.6.6.1'

# UFTP Manual defaults to IPv4 address (converted to Hex) or last 4 bytes of IPv6 address
SERVER_UID = '0xABCDABCD'
TRANSFER_RATE = '1024'

TTL_VALUE = '3'

ROBUSTNESS = '20'
MAX_LOG_SIZE = '2'
MAX_LOG_COUNT = '5'

# How long to wait (seconds) before declaring the UFTP Process to be timed out
PROCESS_TIMEOUT = 30

# Still need to append client list and file list/target direactory
UFTP_SERVER_CMD = [str(paths.UFTP_SERVER_EXE_PATH),
                    '-l',  # Unravel Symbolic Links
                    '-z',  # Run the Server in Sync Mode, so clients will only receive new/updated files
                    '-t', TTL_VALUE,  # TTL value for Multicast Packets, by default is 1 so we turn it up a little
                    '-U', SERVER_UID,  # Server UID for identification purposes.
                    # Transfer rate (Kbps), defaults to 1000 Kbps. 1024 Kbps = 128KB/s
                    '-R', TRANSFER_RATE,
                    # Base directory for the files, for client-side directory management
                    '-E', str(paths.BASE_DIR),
                    # Output for status file, to confirm the file transfer result.
                    '-S', str(paths.STATUS_FILE_PATH),
                    # The log file output. If undefined, defaults to printing logs to stderr
                    '-L', str(paths.LOG_FILE_PATH),
                    '-g', MAX_LOG_SIZE,  # in MB, specifies limit size before a log file is backed up
                    '-n', MAX_LOG_COUNT,  # Default UFTP Value, keeps max 5 iterations of log backups
                    '-p', PORT_NUMBER,  # The port number the server will be listening from
                    '-M', PUB_MULTICAST_ADDR,  # The Initial Public Multicast Address for the ANNOUNCE phase
                    '-P', PRIV_MULTICAST_ADDR,  # The Private Multicast Address for FILE TRANSFER phase
                    # The number of times a message will be repeated (10-50). defaults to 20
                    '-s', ROBUSTNESS,
                    '-H']  # List of comma separated target client IDs, enclosed in "" if more than one
