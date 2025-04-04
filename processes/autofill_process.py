import os
import concurrent.futures
from opensearch_client import OpenSearchClient
import datetime
import csv

def process_autofills_in_folder(root_folder, output_folder, autofill_file_name, verbose=False, enable_opensearch=False, save_csv=True):
    """
    Process all subfolders in the root folder to extract autofill data.

    Args:
        root_folder (str): Path to the root folder containing autofill files.
        output_folder (str): Path to the folder where output files will be saved.
        autofill_file_name (str): Name of the output file for combined autofill data.
        verbose (bool): Enable verbose logging.
        enable_opensearch (bool): Whether to send data to OpenSearch.
        save_csv (bool): Whether to save the data to a CSV file.
    """
    print(f"Processing autofills in folder: {root_folder}")

    autofill_files = [
        os.path.join(root, file_name)
        for root, _, files in os.walk(root_folder)
        for file_name in files
        if ('autofill' in os.path.basename(root).lower() or 'autofill' in file_name.lower()) and file_name.lower().endswith(('.csv', '.tsv', '.txt'))
    ]

    autofill_data = []
    if not autofill_files:
        if verbose:
            print("No autofill files found.")
        return

    # Use ThreadPoolExecutor for I/O-bound tasks
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_autofill_files_parallel, file_path, verbose) for file_path in autofill_files]
        for future in concurrent.futures.as_completed(futures):
            try:
                file_data = future.result()
                if file_data:
                    autofill_data.extend(file_data)
            except Exception as e:
                if verbose:
                    print(f"Error processing file: {str(e)}")

    write_autofill_data(autofill_data, output_folder, autofill_file_name, verbose, save_csv)

    if enable_opensearch:
        send_to_opensearch(autofill_data)

def process_autofill_files_parallel(file_path, verbose=False):
    """
    Extract autofill data from a single file.

    Args:
        file_path (str): Path to the autofill file.
        verbose (bool): Enable verbose logging.

    Returns:
        list[dict]: List of extracted autofill entries.
    """
    if verbose:
        print(f"Processing {file_path}")
    
    autofill_entries = []
    try:
        with open(file_path, 'rb') as file:
            current_key = None
            for line in file:
                try:
                    decoded_line = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    if verbose:
                        print(f"Skipping undecodable line in file {file_path}")
                    continue
                
                line_lower = decoded_line.lower()
                if line_lower.startswith(('name:', 'form:')):
                    current_key = decoded_line.split(':', 1)[1].strip()
                elif line_lower.startswith('value:') and current_key is not None:
                    current_value = decoded_line.split(':', 1)[1].strip()
                    autofill_entries.append({
                        "key": current_key,
                        "value": current_value,
                        "source_file": os.path.basename(file_path),
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "type": "autofill"
                    })
                    current_key = None
        return autofill_entries
    except IOError as e:
        if verbose:
            print(f"Error processing file {file_path}: {e}")
        return []

def write_autofill_data(autofill_data, output_folder, autofill_file_name, verbose=False, save_csv=True):
    """
    Write extracted autofill data to a CSV file.

    Args:
        autofill_data (list[dict]): List of autofill entries to write.
        output_folder (str): Path to the folder where the output file will be saved.
        autofill_file_name (str): Name of the output file.
        verbose (bool): Enable verbose logging.
        save_csv (bool): Whether to save the data to a CSV file.
    """
    if not autofill_data:
        if verbose:
            print("No autofill data to write.")
        return

    if not save_csv:
        if verbose:
            print("CSV saving is disabled. Skipping writing autofill data.")
        return

    if verbose:
        print(f"Writing autofill data to {autofill_file_name}")

    os.makedirs(output_folder, exist_ok=True)
    target_file_path = os.path.join(output_folder, autofill_file_name)

    try:
        with open(target_file_path, 'w', encoding='utf-8', newline='') as target_file:
            csv_writer = csv.DictWriter(
                target_file, 
                fieldnames=["key", "value", "source_file", "timestamp", "type"],
                quoting=csv.QUOTE_MINIMAL,
                escapechar='\\'
            )
            csv_writer.writeheader()
            csv_writer.writerows(autofill_data)
        if verbose:
            print(f"Wrote autofill data to: {target_file_path}")
    except IOError as e:
        if verbose:
            print(f"Error writing to file {target_file_path}: {e}")

def send_to_opensearch(data):
    """
    Send extracted autofill data to OpenSearch.

    Args:
        data (list[dict]): List of autofill entries to send.
    """
    client = OpenSearchClient(verbose=False)
    for entry in data:
        try:
            client.index_document(entry)
        except Exception as e:
            print(f"Failed to send document to OpenSearch: {e}")
