import argparse
import os
import sys
import time
import concurrent.futures
from processes.password_process import process_passwords_in_folder
from processes.autofill_process import process_autofills_in_folder

def main(root_folder, output_folder, verbose, max_workers=None, enable_opensearch=False, save_csv=True):
    """
    Main function to process stealer logs.

    Args:
        root_folder (str): Path to the root folder containing log files.
        output_folder (str): Path to the folder where output files will be saved.
        verbose (bool): Enable verbose logging.
        max_workers (int): Maximum number of worker processes.
        enable_opensearch (bool): Whether to send data to OpenSearch.
        save_csv (bool): Whether to save extracted data to CSV files.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    start_time = time.time()

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_passwords_in_folder, root_folder, output_folder, 'credentials.csv', verbose, enable_opensearch, save_csv),
            executor.submit(process_autofills_in_folder, root_folder, output_folder, 'autofills.csv', verbose, enable_opensearch, save_csv)
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error during processing: {str(e)}")

    if verbose:
        elapsed = time.time() - start_time
        print(f"Total processing time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stealer Log Processor')
    parser.add_argument('root_folder', type=str, nargs='?', default='./data', 
                        help='The root folder path to process. Defaults to ./data.')
    parser.add_argument('--output', type=str, default='./output', 
                        help='Output folder for processed files. Defaults to ./output.')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output.')
    parser.add_argument('--workers', type=int, default=None,
                        help='Maximum number of worker processes. Default is CPU count.')
    parser.add_argument('--enable-opensearch', action='store_true', 
                        help='Enable OpenSearch integration. Disabled by default.')
    parser.add_argument('--disable-csv', action='store_true', 
                        help='Disable saving extracted data to CSV files. Enabled by default.')
    args = parser.parse_args()

    if not os.path.isdir(args.root_folder):
        print(f"Error: {args.root_folder} is not a valid directory.")
        sys.exit(1)

    output_folder = args.output
    save_csv = not args.disable_csv
    main(args.root_folder, output_folder, args.verbose, args.workers, args.enable_opensearch, save_csv)
