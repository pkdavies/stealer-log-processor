# Stealer Log Processor

> ⚠️ Originally authored by [bikemazzell](https://github.com/bikemazzell). Refactored for OpenSearch support, multi-processing, and modularity.

---

## Overview

This tool processes logs harvested by information stealers and extracts credential and autofill data. It now supports structured output to an [OpenSearch](https://opensearch.org/) index, enabling fast searching and analysis.

---

## Features

✅ Process folders of stealer logs  
✅ Parse `password` and `autofill` files  
✅ Send extracted data to OpenSearch  iles
✅ Modular architecture (easy to extend)  
✅ Timezone-aware timestamps for accurate indexing 
✅ Send extracted data to OpenSearch


## Folder Structure---

```
stealer-log-processor/
├── main.py                  # Entry point for folder processing
├── opensearch_client.py     # OpenSearch config & connectionocessor/
└── processes/er processing
    ├── password_process.py  # Password file parserconnection
    └── autofill_process.py  # Autofill file parser processes/
```    ├── password_process.py  # Password file parser
 └── autofill_process.py  # Autofill file parser
---```

## OpenSearch Setup---

### Environment Variables
Set the following environment variables before running:
ironment Variables
```bashnment variables before running:
export OS_HOST=localhost
export OS_PORT=9200
export OS_USER=adminhost
export OS_PASS=admin
export OS_INDEX=stealer-logsort OS_USER=admin
```export OS_PASS=admin

These are used in `opensearch_client.py` to connect securely.```

### Index Mapping (optional)
You can manually set up a structured index in OpenSearch for better querying:
ex Mapping (optional)
```json set up a structured index in OpenSearch for better querying:
PUT stealer-logs
{
  "mappings": {
    "properties": {
      "email": { "type": "keyword" },
      "password": { "type": "text" },
      "key": { "type": "keyword" }, },
      "value": { "type": "text" },,
      "type": { "type": "keyword" },
      "source_file": { "type": "keyword" },
      "timestamp": { "type": "date" } "type": { "type": "keyword" },
    }   "source_file": { "type": "keyword" },
  }     "timestamp": { "type": "date" }
} }
```  }

---```

## Usage---

### 1. Place log folders in a `logs/` directory:
Each folder should contain the files to be parsed.
in a `logs/` directory:
### 2. Run the processor:lder should contain the files to be parsed.
```bash
python main.py 2. Run the processor:
``````bash

This will process each subfolder in `logs/`, parse any matching files, and send the results to OpenSearch.```

---This will process each subfolder in `logs/`, parse any matching files, and send the results to OpenSearch.

## Output Format
Documents in OpenSearch will include fields such as:
```json# Output Format
{de fields such as:
  "type": "password" | "autofill",
  "email": "...",  # if password
  "password": "...",,
  "key": "...",     # if autofill  # if password
  "value": "...",
  "source_file": "...",
  "timestamp": "2025-04-01T13:00:00+00:00" "value": "...",
}source_file": "...",
```  "timestamp": "2025-04-01T13:00:00Z"

---```

