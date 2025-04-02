import os
import re
import concurrent.futures
import datetime
from opensearch_client import OpenSearchClient

def process_passwords_in_folder(root_folder, output_folder, password_file_name, verbose=False, max_workers=None, enable_opensearch=False):
    print(f"Processing passwords in folder: {root_folder}")

    # Initialize list to store paths of output files in subfolders
    output_files = []

    # Traverse through each subfolder
    subfolders = [f.path for f in os.scandir(root_folder) if f.is_dir()]
    
    # Process subfolders in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Map subfolder processing to executor
        future_to_subfolder = {
            executor.submit(process_passwords_in_subfolder, subfolder, output_folder, password_file_name, verbose, enable_opensearch): subfolder
            for subfolder in subfolders
        }
        
        # Collect results as they complete
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

    # Combine all output files into one at output_folder level
    combine_password_files(output_files, output_folder, password_file_name, verbose)

def process_passwords_in_subfolder(subfolder, output_folder, password_file_name, verbose=False, enable_opensearch=False):
    if verbose:
        print(f"\tsubfolder: {subfolder}")

    # Initialize list to store credentials
    credentials = []

    # Use os.scandir for faster directory traversal
    password_files = []
    with os.scandir(subfolder) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.lower().endswith(('.csv', '.tsv', '.txt')) and 'password' in entry.name.lower():
                password_files.append(entry.path)

    # Reuse thread pool for file processing
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

    # Skip if no credentials found
    if not credentials:
        return None

    # Create temp folder in output location for temporary files
    subfolder_name = os.path.basename(subfolder)
    temp_folder = os.path.join(output_folder, 'temp')
    os.makedirs(temp_folder, exist_ok=True)
    
    # Write credentials to the output file in temp folder
    output_file_path = os.path.join(temp_folder, f"{subfolder_name}_{password_file_name}")
    with open(output_file_path, 'w', encoding='utf-8') as out_file:
        for credential in credentials:
            out_file.write(','.join(credential.values()) + '\n')

    # Send credentials to OpenSearch if enabled
    if enable_opensearch:
        send_to_opensearch(credentials)

    return output_file_path

def process_password_files(file_path, verbose=False):
    if verbose:
        print(f"Processing {file_path}")
    
    file_credentials = []
    password_info = {'URL': '', 'USER': '', 'PASS': ''}
    expected_next = 'URL'  # Start expecting a URL

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
                # Skip lines that do not start with expected credential keys
                if not (line_lower.startswith('url:') or 
                        line_lower.startswith('user:') or 
                        line_lower.startswith('username:') or 
                        line_lower.startswith('login:') or 
                        line_lower.startswith('pass:') or 
                        line_lower.startswith('password:')):
                    continue

                # Process line if it starts with expected info and matches the expected sequence
                if expected_next == 'URL' and 'url:' in line_lower:
                    parts = decoded_line.split(':', 1)
                    if len(parts) == 2:
                        password_info['URL'] = parts[1].strip()
                        expected_next = 'USER'  # Next, expect User/Login

                elif expected_next == 'USER' and ('user:' in line_lower or 'username:' in line_lower or 'login:' in line_lower):
                    parts = decoded_line.split(':', 1)
                    if len(parts) == 2:
                        password_info['USER'] = parts[1].strip()
                        expected_next = 'PASS'  # Next, expect Password

                elif expected_next == 'PASS' and ('pass:' in line_lower or 'password:' in line_lower):
                    parts = decoded_line.split(':', 1)
                    if len(parts) == 2:
                        password_info['PASS'] = parts[1].strip()
                        # After capturing Password, ensure URL is properly formatted
                        
                        # Create a properly escaped credential
                        if password_info['USER'] and password_info['PASS'] and password_info['URL']:
                            file_credentials.append({
                                "email": password_info['USER'],
                                "password": password_info['PASS'],
                                "source_file": file_path,
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                "type": "password"
                            })
                        
                        password_info = {'URL': '', 'USER': '', 'PASS': ''}  # Reset for next credential set
                        expected_next = 'URL'  # Start expecting a URL again for the next set

        return file_credentials
    except IOError as e:
        print(f"Error processing file {file_path}: {e}")
        return []

def combine_password_files(output_files, output_folder, output_file_name, verbose=False):
    if not output_files:
        if verbose:
            print("No credentials found to combine.")
        return
    
    if verbose:
        print(f"Combining credentials into {output_file_name}")

    combined_credentials = set()
    for output_file in output_files:
        try:
            with open(output_file, 'r', encoding='utf-8') as file:
                for line in file:
                    combined_credentials.add(line.strip())
        except Exception as e:
            if verbose:
                print(f"Error reading file {output_file}: {e}")

    # Write combined credentials to the target file
    target_file_path = os.path.join(output_folder, output_file_name)
    try:
        with open(target_file_path, 'w', encoding='utf-8') as target_file:
            for credential in combined_credentials:
                target_file.write(credential + '\n')
        if verbose:
            print(f"Wrote combined credentials to: {target_file_path}")

    except IOError as e:
        if verbose:
            print(f"Error writing to file {target_file_path}: {e}")
    
    # Clean up intermediate files
    for output_file in output_files:
        try:
            os.remove(output_file)
        except Exception as e:
            if verbose:
                print(f"Failed to remove temporary file {output_file}: {e}")
    
    # Attempt to remove temp directory if it exists and is empty
    temp_folder = os.path.join(output_folder, 'temp')
    try:
        if os.path.exists(temp_folder) and not os.listdir(temp_folder):
            os.rmdir(temp_folder)
    except Exception as e:
        if verbose:
            print(f"Failed to remove temp folder: {e}")

def send_to_opensearch(credentials):
    client = OpenSearchClient()
    for credential in credentials:
        try:
            client.index_document(credential)
        except Exception as e:
            print(f"Failed to send document to OpenSearch: {e}")
