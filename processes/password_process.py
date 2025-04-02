import os
import re
import concurrent.futures
import datetime
from opensearch_client import OpenSearchClient

def process_passwords_in_folder(root_folder, output_folder, password_file_name, verbose=False, max_workers=None, enable_opensearch=False, save_csv=True):
    """
    Process all subfolders in the root folder to extract password data.

    Args:
        root_folder (str): Path to the root folder containing subfolders with password files.
        output_folder (str): Path to the folder where output files will be saved.
        password_file_name (str): Name of the output file for combined credentials.
        verbose (bool): Enable verbose logging.
        max_workers (int): Maximum number of processes for parallel processing.
        enable_opensearch (bool): Whether to send data to OpenSearch.
        save_csv (bool): Whether to save extracted data to a CSV file.
    """
    print(f"Processing passwords in folder: {root_folder}")

    subfolders = [f.path for f in os.scandir(root_folder) if f.is_dir()]
    output_files = []

    # Use ProcessPoolExecutor for CPU-bound tasks
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_subfolder = {
            executor.submit(process_passwords_in_subfolder, subfolder, output_folder, password_file_name, verbose, enable_opensearch, save_csv): subfolder
            for subfolder in subfolders
        }

        for future in concurrent.futures.as_completed(future_to_subfolder):
            subfolder = future_to_subfolder[future]
            try:
                output_file_path = future.result()
                if output_file_path:
                    output_files.append(output_file_path)
                    if verbose:
                        print(f"Completed processing subfolder: {subfolder}")
            except Exception as e:
                print(f"Error processing subfolder {subfolder}: {str(e)}")

    if save_csv:
        combine_password_files(output_files, output_folder, password_file_name, verbose)

def process_passwords_in_subfolder(subfolder, output_folder, password_file_name, verbose=False, enable_opensearch=False, save_csv=True):
    """
    Process a single subfolder to extract password data.

    Args:
        subfolder (str): Path to the subfolder containing password files.
        output_folder (str): Path to the folder where output files will be saved.
        password_file_name (str): Name of the output file for the subfolder.
        verbose (bool): Enable verbose logging.
        enable_opensearch (bool): Whether to send data to OpenSearch.
        save_csv (bool): Whether to save extracted data to a CSV file.

    Returns:
        str: Path to the output file for the subfolder, or None if no credentials found.
    """
    if verbose:
        print(f"\tProcessing subfolder: {subfolder}")

    password_files = [
        entry.path for entry in os.scandir(subfolder)
        if entry.is_file() and entry.name.lower().endswith(('.csv', '.tsv', '.txt')) and 'password' in entry.name.lower()
    ]

    credentials = []
    # Use ThreadPoolExecutor for I/O-bound tasks
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_password_files, file_path, verbose) for file_path in password_files]
        for future in concurrent.futures.as_completed(futures):
            try:
                file_credentials = future.result()
                if file_credentials:
                    credentials.extend(file_credentials)
            except Exception as e:
                if verbose:
                    print(f"Error processing file: {str(e)}")

    if not credentials:
        return None

    if save_csv:
        temp_folder = os.path.join(output_folder, 'temp')
        os.makedirs(temp_folder, exist_ok=True)
        output_file_path = os.path.join(temp_folder, f"{os.path.basename(subfolder)}_{password_file_name}")

        with open(output_file_path, 'w', encoding='utf-8') as out_file:
            for credential in credentials:
                out_file.write(','.join(credential.values()) + '\n')
    else:
        output_file_path = None

    if enable_opensearch:
        send_to_opensearch(credentials)

    return output_file_path

def process_password_files(file_path, verbose=False):
    """
    Extract credentials from a single password file.

    Args:
        file_path (str): Path to the password file.
        verbose (bool): Enable verbose logging.

    Returns:
        list[dict]: List of extracted credentials.
    """
    if verbose:
        print(f"Processing file: {file_path}")

    file_credentials = []
    password_info = {'URL': '', 'USER': '', 'PASS': ''}
    expected_next = 'URL'

    try:
        with open(file_path, 'rb') as file:
            for line in file:
                try:
                    decoded_line = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    if verbose:
                        print(f"Skipping undecodable line in file {file_path}")
                    continue

                line_lower = decoded_line.lower()
                if not any(line_lower.startswith(prefix) for prefix in ['url:', 'user:', 'username:', 'login:', 'pass:', 'password:']):
                    continue

                if expected_next == 'URL' and 'url:' in line_lower:
                    parts = decoded_line.split(':', 1)
                    if len(parts) == 2:
                        password_info['URL'] = parts[1].strip()
                        expected_next = 'USER'

                elif expected_next == 'USER' and any(key in line_lower for key in ['user:', 'username:', 'login:']):
                    parts = decoded_line.split(':', 1)
                    if len(parts) == 2:
                        password_info['USER'] = parts[1].strip()
                        expected_next = 'PASS'

                elif expected_next == 'PASS' and any(key in line_lower for key in ['pass:', 'password:']):
                    parts = decoded_line.split(':', 1)
                    if len(parts) == 2:
                        password_info['PASS'] = parts[1].strip()
                        if all(password_info.values()):
                            file_credentials.append({
                                "email": password_info['USER'],
                                "password": password_info['PASS'],
                                "source_file": os.path.basename(file_path),
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "type": "password"  # Add the "type" field
                            })
                        password_info = {'URL': '', 'USER': '', 'PASS': ''}
                        expected_next = 'URL'

        return file_credentials
    except IOError as e:
        print(f"Error processing file {file_path}: {e}")
        return []

def combine_password_files(output_files, output_folder, output_file_name, verbose=False):
    """
    Combine all extracted credentials into a single output file.

    Args:
        output_files (list[str]): List of paths to temporary output files.
        output_folder (str): Path to the folder where the combined file will be saved.
        output_file_name (str): Name of the combined output file.
        verbose (bool): Enable verbose logging.
    """
    if not output_files:
        if verbose:
            print("No credentials found to combine.")
        return

    combined_credentials = set()
    for output_file in output_files:
        try:
            with open(output_file, 'r', encoding='utf-8') as file:
                combined_credentials.update(line.strip() for line in file)
        except Exception as e:
            if verbose:
                print(f"Error reading file {output_file}: {e}")

    target_file_path = os.path.join(output_folder, output_file_name)
    try:
        with open(target_file_path, 'w', encoding='utf-8') as target_file:
            target_file.write('\n'.join(combined_credentials) + '\n')
        if verbose:
            print(f"Wrote combined credentials to: {target_file_path}")
    except IOError as e:
        if verbose:
            print(f"Error writing to file {target_file_path}: {e}")

    for output_file in output_files:
        try:
            os.remove(output_file)
        except Exception as e:
            if verbose:
                print(f"Failed to remove temporary file {output_file}: {e}")

    temp_folder = os.path.join(output_folder, 'temp')
    try:
        if os.path.exists(temp_folder) and not os.listdir(temp_folder):
            os.rmdir(temp_folder)
    except Exception as e:
        if verbose:
            print(f"Failed to remove temp folder: {e}")

def send_to_opensearch(credentials):
    """
    Send extracted credentials to OpenSearch.

    Args:
        credentials (list[dict]): List of credentials to send.
    """
    client = OpenSearchClient()
    for credential in credentials:
        try:
            client.index_document(credential)
        except Exception as e:
            print(f"Failed to send document to OpenSearch: {e}")
