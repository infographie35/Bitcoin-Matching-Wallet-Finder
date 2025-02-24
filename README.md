# Bitcoin Matching Wallet Finder

A lightweight Python tool that monitor cuda Bitcoin generator address starting with 1, and checks them against a predefined address list. 

It automatically terminates the external process when the file reaches a set size and updates three live statistics:

- **Cycle Wallets:** Wallets processed in the current cycle.
- **File Progress:** A progress bar showing how close the file is to the maximum allowed size.
- **Total Wallets:** Overall count of processed wallets since the script started.

## Features

- Real-time file tailing and block processing.
- Automatic process termination when the file exceeds a specified size (before starting over)
- Dynamic display of processing statistics.
- Graceful shutdown on keyboard interruption.

## Requirements

- Python 3.x
- `tqdm` package (for progress bar)
- copy VanitySearch.exe in script folder - https://github.com/JeanLucPons/VanitySearch/releases

## How to start

- Fill one per line with bitcoin addresses (starting with 1) you search in addresses_list.txt
- Python Matching.py
- If you have a match, it will output to Matching.txt all 3 lines from result.txt (PubAddress, Priv (WIF), Priv (HEX))

Use for educational purpose only
