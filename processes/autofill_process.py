import os
import concurrent.futures

def process_autofills_in_folder(root_folder, output_folder, autofill_file_name, verbose=False):
    print(f"Processing autofills in folder: {root_folder}")
    
    # Find all autofill files
    autofill_files = []
    for root, dirs, files in os.walk(root_folder):
        autofill_directory = 'autofill' in os.path.basename(root).lower()
        for file_name in files:
            if (autofill_directory or 'autofill' in file_name.lower()) and file_name.lower().endswith(('.csv', '.tsv', '.txt')):
                file_path = os.path.join(root, file_name)
                autofill_files.append(file_path)
    
    # Process files in parallel
    output_files = []
    seen_pairs = set()  # This will be synchronized using a lock
    
    if not autofill_files:
        if verbose:
            print("No autofill files found.")
        return
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Map each file to process_autofill_files
        future_to_file = {}
        for file_path in autofill_files:
            future = executor.submit(process_autofill_files_parallel, file_path, verbose)
            future_to_file[future] = file_path
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                form_value_pairs = future.result()
                if form_value_pairs:
                    # Filter out duplicates
                    unique_pairs = []
                    for pair in form_value_pairs:
                        if pair not in seen_pairs:
                            seen_pairs.add(pair)
                            unique_pairs.append(pair)
                            
                    if unique_pairs:
                        autofills_output = ','.join(unique_pairs)
                        output_files.append(autofills_output)
                        
            except Exception as e:
                if verbose:
                    print(f"Error processing file {file_path}: {str(e)}")
    
    combine_autofill_files(output_files, output_folder, autofill_file_name, verbose)

# New function for parallel processing that doesn't use shared seen_pairs
def process_autofill_files_parallel(file_path, verbose=False):
    if verbose:
        print(f"Processing {file_path}")
    
    form_value_pairs = []
    
    try:
        with open(file_path, 'rb') as file:
            current_key = None  # Use current_key instead of current_form
            
            for line in file:
                try:
                    decoded_line = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    if verbose:
                        print(f"Skipping undecodable line in file {file_path}")
                    continue
                
                line_lower = decoded_line.lower()
                # Check for tab-separated key/value pairs on the same line
                if '\t' in decoded_line:
                    key, value = decoded_line.split('\t', 1)
                    # Properly handle values that might include URLs
                    pair = f'"{key}":"{value}"' if (',' in key or ',' in value) else f"{key}:{value}"
                    form_value_pairs.append(pair)
                else:
                    # Process FORM/VALUE pairs across lines
                    if line_lower.startswith(('form:', 'name:')):
                        current_key = decoded_line.split(':', 1)[1].strip()
                    elif (line_lower.startswith(('value:')) and current_key is not None):
                        current_value = decoded_line.split(':', 1)[1].strip()
                        # Properly handle values that might include URLs or commas
                        pair = f'"{current_key}":"{current_value}"' if (',' in current_key or ',' in current_value) else f"{current_key}:{current_value}"
                        form_value_pairs.append(pair)
                        current_key = None  # Reset for next FORM/VALUE pair
        
        return form_value_pairs
    
    except IOError as e:
        if verbose:
            print(f"Error processing file {file_path}: {e}")
        return []

# Keep the original function for compatibility
def process_autofill_files(file_path, seen_pairs, verbose=False):
    form_value_pairs = process_autofill_files_parallel(file_path, verbose)
    
    # Filter through seen_pairs and create output
    unique_pairs = []
    for pair in form_value_pairs:
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            unique_pairs.append(pair)
    
    if unique_pairs:
        autofills_output = ','.join(unique_pairs)
        return autofills_output
    return None

def combine_autofill_files(output_files, output_folder, output_file_name, verbose=False):
    if not output_files:
        if verbose:
            print("No autofills found to combine.")
        return
    
    if verbose:
        print(f"Combining output files into {output_file_name}")
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    target_file_path = os.path.join(output_folder, output_file_name)
    try:
        with open(target_file_path, 'w', encoding='utf-8') as target_file:
            for autofill in set(output_files):
                target_file.write(autofill + '\n')
        if verbose:
            print(f"Wrote combined autofills to: {target_file_path}")
     
    except IOError as e:
        if verbose:
            print(f"Error writing to file {target_file_path}: {e}")
