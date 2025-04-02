import os
import concurrent.futures
from opensearch_client import OpenSearchClient
import datetime

def process_autofills_in_folder(root_folder, output_folder, autofill_file_name, verbose=False):
    print(f"Processing autofills in folder: {root_folder}")

    # Traverse all subdirectories to find autofill files
    autofill_files = []
    for root, _, files in os.walk(root_folder):
        # Check if the directory name contains "autofill" (case-insensitive)
        if 'autofill' in os.path.basename(root).lower():
            for file_name in files:
                if file_name.lower().endswith(('.csv', '.tsv', '.txt')):
                    autofill_files.append(os.path.join(root, file_name))
        else:
            # Check if the file name contains "autofill" (case-insensitive)
            for file_name in files:
                if 'autofill' in file_name.lower() and file_name.lower().endswith(('.csv', '.tsv', '.txt')):
                    autofill_files.append(os.path.join(root, file_name))

    # Reuse thread pool for file processing
    autofill_data = []
    if not autofill_files:
        if verbose:
            print("No autofill files found.")
        return

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

    # Write autofill data to the output file
    write_autofill_data(autofill_data, output_folder, autofill_file_name, verbose)

def process_autofill_files_parallel(file_path, verbose=False):
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
                # Process FORM/VALUE pairs
                if line_lower.startswith(('name:', 'form:')):
                    current_key = decoded_line.split(':', 1)[1].strip()
                elif line_lower.startswith('value:') and current_key is not None:
                    current_value = decoded_line.split(':', 1)[1].strip()
                    # Maintain key-value relationship
                    autofill_entries.append({
                        "email": current_key if "email" in current_key.lower() else None,
                        "password": current_value if "password" in current_key.lower() else None,
                        "source_file": file_path,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "type": "autofill"
                    })
                    current_key = None  # Reset for next pair
        
        return autofill_entries
    
    except IOError as e:
        if verbose:
            print(f"Error processing file {file_path}: {e}")
        return []

def write_autofill_data(autofill_data, output_folder, autofill_file_name, verbose=False):
    if not autofill_data:
        if verbose:
            print("No autofill data to write.")
        return

    if verbose:
        print(f"Writing autofill data to {autofill_file_name}")

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    target_file_path = os.path.join(output_folder, autofill_file_name)
    try:
        with open(target_file_path, 'w', encoding='utf-8') as target_file:
            for entry in autofill_data:
                # Write each key-value pair as a JSON-like structure for context
                target_file.write(f"{entry['key']}: {entry['value']}\n")
        if verbose:
            print(f"Wrote autofill data to: {target_file_path}")
    except IOError as e:
        if verbose:
            print(f"Error writing to file {target_file_path}: {e}")
