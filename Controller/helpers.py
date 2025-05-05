import time
import subprocess
import netifaces

import logging
session_logger = logging.getLogger('session_logger')
logger = session_logger.getChild(__name__)
logger.setLevel(logging.DEBUG)

def get_ip_address(interface="eth0"):
    """
    Get the IP address of the machine.
    Returns:
        str: The IP address of the machine.
    """
    try:
        # Get the IP address of the interface
        ip_address = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
        return ip_address
    except Exception as e:
        logger.error(f"Error getting IP address for {interface}: {e}")
        return None

def wait_for_dmesg(msg="", timeout=30):
    msg_line = None
    start_time = time.mktime(time.localtime())
    timeout = start_time + timeout

    logger.debug(f"Waiting for dmesg message: {msg}...")
    waiting = True
    while waiting:
        time.sleep(0.1)

        dmesg = subprocess.check_output("dmesg -T | tail", shell=True).decode("utf-8")
        dmesg = dmesg.split("\n")[:-1]

        timestamps = [line.split("]")[0][1:] for line in dmesg]
        timestamps = [time.mktime(time.strptime(ts, "%a %b %d %H:%M:%S %Y")) for ts in timestamps]

        # Filter for timestamps after start time
        dmesg = [line for line, ts in zip(dmesg, timestamps) if ts > start_time]

        if dmesg:
            msg_line = [line for line in dmesg if msg in line]
            if msg_line:
                waiting = False
                msg_line = msg_line[0]
                logger.debug(f"Found message: {msg_line}")

        if time.mktime(time.localtime()) > timeout:
            logger.info("Timeout reached.")
            break

    return msg_line

if __name__ == "__main__":
    wait_for_dmesg("ttyACM")
    