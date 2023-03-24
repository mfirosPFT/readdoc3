"""
This file contains the error codes and error messages for ExpeDat .
For more information, see the ExpeDat documentation at https://www.dataexpedition.com/expedat/Docs/movedat/exit-codes.html .

"""
error_dict = {
    0: "Success: all requested operations completed successfully",
    1: "Could not determine the nature of the error",
    4: "An unsupported feature was requested",
    5: "Invalid address",
    8: "Object too large to be delivered",
    9: "Object unavailable",
    10: "Bad Credentials (username or password)",
    11: "Object is busy or locked - try again later",
    13: "Operation timed out",
    14: "A requested condition was not met",
    17: "Unsupported application version",
    18: "Invalid Argument",
    20: "Transaction lost or unrecognized",
    21: "Encryption required",
    22: "Requested encryption is not supported",
    23: "Requested key is not valid or not supported",
    24: "Request denied by configuration or user input",
    25: "Invalid pathname",
    26: "A server name is invalid or no server could be reached",
    27: "Insufficient privileges for requested action",
    28: "Requested feature not supported",
    29: "Operating system error",
    30: "Server capacity has been exceeded",
    31: "Exceeded resource limit based on credentials",
    32: "Session aborted",
    33: "Out of memory",
    34: "Directory already exists or requested state already set",
    36: "A partial upload was detected and resumption was not selected",
    37: "A partial upload was detected, but the file or meta data appears to be corrupted",
    38: "A partial upload was detected, but the source and destination files appear to be different",
    43: "A feature was requested which is not supported by the software license",
    66: "Error in network system call",
    69: "Network buffer overflow",
    71: "Request expired because network connectivity was lost",
    72: "Address is not valid",
    74: "Port is not valid (out of range)",
    76: "ICMP Network is down",
    77: "ICMP Host is down",
    78: "ICMP No application on given port",
    80: "ICMP Network unknown",
    81: "ICMP Host unknown",
    82: "ICMP Net/Host/Filter Prohibited",
    248: "Problem with command line or configuration file",
    249: "Error accessing a local file",
    250: "An error occurred with the DEI toolkit",
    251: "An error occurred with the SEQ module",
    252: "An error occurred with the DOC module",
    253: "An error occurred with the MTP module",
    254: "License/registration problem",
    255: "Multiple actions were requested and some failed"
}


def get_error_message(error_message):
    # "failed to run commands: exit status 255"
    # extract the exit code from the error message string
    exit_code = None
    try:
        if error_message and isinstance(error_message, str):
            exit_code_start_index = error_message.find(
                'exit status ') + len('exit status ')
            if exit_code_start_index >= len('exit status '):
                exit_code_str = error_message[exit_code_start_index:].split()[
                    0]
                if exit_code_str.isdigit():
                    exit_code = int(exit_code_str)
    except Exception as e:
        print(f"Exception in get_error_message: {e}")
    if exit_code is not None:
        return error_dict.get(exit_code, "Could not determine the nature of the error")
    else:
        return error_message
