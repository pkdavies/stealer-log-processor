import argparse
import os
import sys
import time
import concurrent.futures
from processes.password_process import process_passwords_in_folder
from processes.autofill_process import process_autofills_in_folder

def main(root_folder, output_folder, verbose, max_workers=None):
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    start_time = time.time()

    # Use a shared ProcessPoolExecutor for both tasks
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_passwords_in_folder, root_folder, output_folder, 'credentials.csv', verbose),
            executor.submit(process_autofills_in_folder, root_folder, output_folder, 'autofills.csv', verbose)
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
    args = parser.parse_args()

    if not os.path.isdir(args.root_folder):
        print(f"Error: {args.root_folder} is not a valid directory.")
        sys.exit(1)

    # Default output to ./output if not specified
    output_folder = args.output

    main(args.root_folder, output_folder, args.verbose, args.workers)
