import os
import subprocess
import sys
import time
import mmap

# Configuration
BATCH_FILE = "VanitySearch.bat"           # Batch file that starts vanitysearch.exe
RESULT_FILE = "result.txt"               # Output file produced by vanitysearch.exe
MATCH_FILE = "match.txt"                 # File to append matching blocks
ADDRESS_LIST_FILE = "addresses_list.txt" # File containing one public address per line
MAX_SIZE = 10 * 1024 * 1024              # 10 MB in bytes
CHECK_INTERVAL = 0.1                     # Time (in seconds) between polling for new lines
READ_TIMEOUT = 5                         # Time (in seconds) to wait after kill for pending writes

# Global total wallet counter
total_wallets = 0

def load_addresses():
    """Load addresses from addresses_list.txt into a set for fast lookup."""
    with open(ADDRESS_LIST_FILE, "r") as f:
        addresses = {line.strip() for line in f if line.strip()}
    print(f"Loaded {len(addresses)} addresses from {ADDRESS_LIST_FILE}")
    return addresses

def kill_process(proc):
    """
    Terminate the batch process (if still running) and explicitly kill any vanitysearch.exe processes.
    """
    if proc and proc.poll() is None:  # If the batch process is still running
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    
    # Explicitly kill any running vanitysearch.exe processes.
    try:
        subprocess.run('taskkill /F /IM vanitysearch.exe', shell=True, check=True)
        print("vanitysearch.exe process terminated.")
    except subprocess.CalledProcessError as e:
        print("Could not terminate vanitysearch.exe or it was not running:", e)

def process_block(block, addresses_set):
    """
    Given a block (list of lines), extract the public address and if it matches an address in addresses_set,
    append the block to match.txt.
    Assumes block[0] starts with "PubAddress:".
    """
    if not block:
        return
    pub_line = block[0].strip()
    if pub_line.startswith("PubAddress:"):
        pub_addr = pub_line.split(":", 1)[-1].strip()
        if pub_addr in addresses_set:
            with open(MATCH_FILE, "a") as mf:
                mf.write("\n".join(block))
                mf.write("\n\n")
            # Uncomment below if you want a log for a found match:
            # print(f"Match found for address: {pub_addr}")

def update_display(cycle_wallets, total_wallets, file_size, first_update):
    """
    Updates the three static lines:
      1. Cycle Processed Wallets.
      2. File Progress bar (percentage).
      3. Total Wallets Processed.
    
    If first_update is True, simply prints three new lines.
    Otherwise, moves the cursor up 3 lines to update.
    """
    percent = min((file_size / MAX_SIZE) * 100, 100)
    progress_bar_length = 30  # Length of the bar in characters
    filled_length = int(progress_bar_length * percent // 100)
    bar = "=" * filled_length + "-" * (progress_bar_length - filled_length)
    
    output = (f"Cycle Processed Wallets: {cycle_wallets}\n"
              f"File Progress: |{bar}| {percent:6.2f}%\n"
              f"Total Wallets Processed: {total_wallets}\n")
    
    if first_update:
        sys.stdout.write(output)
        sys.stdout.flush()
        return False  # first_update is now False
    else:
        sys.stdout.write("\033[3F")  # Move cursor up 3 lines
        sys.stdout.write("\033[K" + output)
        sys.stdout.flush()
        return False

def tail_and_process(addresses_set, proc):
    """
    Tails RESULT_FILE on the fly, processing blocks as they are completed.
    Uses mmap to efficiently check for new lines.
    Monitors file size and terminates the external process if MAX_SIZE is reached.
    Updates three static display lines:
      - Cycle wallet count (resets each cycle)
      - File progress (resets each cycle)
      - Total wallet count (accumulative)
    """
    global total_wallets
    cycle_wallets = 0  # Reset for new cycle
    first_update = True  # For display update on first iteration
    pos = 0            # Current file position
    block = []         # Current block of lines
    start_time = time.time()
    terminated = False

    while True:
        try:
            size = os.path.getsize(RESULT_FILE)
        except OSError:
            size = 0

        first_update = update_display(cycle_wallets, total_wallets, size, first_update)

        if not terminated and size >= MAX_SIZE:
            print(f"\nFile reached {size} bytes. Terminating vanitysearch process...")
            kill_process(proc)
            terminated = True
            start_time = time.time()  # Reset timeout for pending writes

        # Open the file in read mode and create an mmap of the new data
        with open(RESULT_FILE, "r") as rf:
            # Only map the file if new data is available
            if size > pos:
                mm = mmap.mmap(rf.fileno(), length=0, access=mmap.ACCESS_READ)
                mm.seek(pos)
                while True:
                    line = mm.readline()
                    if not line:
                        break
                    # Decode the bytes to a string (assuming UTF-8 encoding)
                    line = line.decode('utf-8').rstrip("\n")
                    if line.startswith("PubAddress:") and block:
                        process_block(block, addresses_set)
                        cycle_wallets += 1
                        total_wallets += 1
                        block = [line]
                    else:
                        block.append(line)
                        # Assuming a block is 3 lines long.
                        if len(block) == 3:
                            process_block(block, addresses_set)
                            cycle_wallets += 1
                            total_wallets += 1
                            block = []
                pos = mm.tell()
                mm.close()

        # If the process has been terminated and no new data arrives for READ_TIMEOUT seconds, exit.
        if terminated and (time.time() - start_time) > READ_TIMEOUT:
            if block:
                process_block(block, addresses_set)
                cycle_wallets += 1
                total_wallets += 1
            break

        time.sleep(CHECK_INTERVAL)
        # Small delay to reduce CPU usage and update display more smoothly.
        time.sleep(0.05)

def main():
    addresses_set = load_addresses()

    while True:
        print("Starting VanitySearch.bat in a new window...")
        proc = subprocess.Popen(BATCH_FILE, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        try:
            while not os.path.exists(RESULT_FILE):
                time.sleep(0.2)
            
            print("Tailing result.txt for new entries...")
            tail_and_process(addresses_set, proc)
        
        except KeyboardInterrupt:
            print("KeyboardInterrupt detected. Cleaning up...")
            kill_process(proc)
            break
        
        if os.path.exists(RESULT_FILE):
            try:
                os.remove(RESULT_FILE)
                print("Deleted result.txt.")
            except Exception as e:
                print("Error deleting result.txt:", e)
        
        print("Cycle complete. Restarting...\n")
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Script terminated by user.")