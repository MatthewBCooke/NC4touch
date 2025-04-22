import time
import subprocess

def wait_for_dmesg(msg="", timeout=30):
    msg_line = None
    start_time = time.mktime(time.localtime())
    timeout = start_time + timeout

    print(f"Waiting for {msg}...")
    waiting = True
    while waiting:
        time.sleep(0.1)

        dmesg = subprocess.check_output("dmesg -T | tail", shell=True).decode("utf-8")
        dmesg = dmesg.split("\n")[:-1]

        timestamps = [line.split("]")[0][1:] for line in dmesg]
        timestamps = [time.mktime(time.strptime(ts, "%a %b %d %H:%M:%S %Y")) for ts in timestamps]

        # Filter for timestamps after start time
        dmesg = [line for line, ts in zip(dmesg, timestamps) if ts > start_time]
        # print(dmesg)

        if dmesg:
            msg_line = [line for line in dmesg if msg in line]
            if msg_line:
                waiting = False
                msg_line = msg_line[0]
                print(f"Found message: {msg_line}")

        if time.mktime(time.localtime()) > timeout:
            print("Timeout reached.")
            break

    return msg_line

if __name__ == "__main__":
    wait_for_dmesg("ttyACM")
    