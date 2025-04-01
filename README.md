# Stealer Log Processor

> ⚠️ Originally authored by [bikemazzell](https://github.com/bikemazzell). Refactored for OpenSearch support and modularity by [Juicy Media Group](https://github.com/pkdavies).

---

## Overview

This tool processes logs harvested by information stealers and extracts credential and autofill data. It now supports structured output to an [OpenSearch](https://opensearch.org/) index, enabling fast searching and analysis.

---

## Features

✅ Process folders of stealer logs
✅ Parse `password` and `autofill` files
✅ Send extracted data to OpenSearch
✅ Modular architecture (easy to extend)

---

## Folder Structure

```
stealer-log-processor/
├── main.py                  # Entry point for folder processing
├── opensearch_client.py     # OpenSearch config & connection
└── processes/
    ├── password_process.py  # Password file parser
    └── autofill_process.py  # Autofill file parser
```

---

## OpenSearch Setup

### Environment Variables
Set the following environment variables before running:

```bash
export OS_HOST=localhost
export OS_PORT=9200
export OS_USER=admin
export OS_PASS=admin
export OS_INDEX=stealer-logs
```

These are used in `opensearch_client.py` to connect securely.

### Index Mapping (optional)
You can manually set up a structured index in OpenSearch for better querying:

```json
PUT stealer-logs
{
  "mappings": {
    "properties": {
      "email": { "type": "keyword" },
      "password": { "type": "text" },
      "key": { "type": "keyword" },
      "value": { "type": "text" },
      "type": { "type": "keyword" },
      "source_file": { "type": "keyword" },
      "timestamp": { "type": "date" }
    }
  }
}
```

---

## Usage

### 1. Place log folders in a `logs/` directory:
Each folder should contain the files to be parsed.

### 2. Run the processor:
```bash
python main.py
```

This will process each subfolder in `logs/`, parse any matching files, and send the results to OpenSearch.

---

## Output Format
Documents in OpenSearch will include fields such as:
```json
{
  "type": "password" | "autofill",
  "email": "...",  # if password
  "password": "...",
  "key": "...",     # if autofill
  "value": "...",
  "source_file": "...",
  "timestamp": "2025-04-01T13:00:00Z"
}
```

---

## Future Ideas
- Add IP & hostname metadata per file
- Push parsed summary CSVs to GCS or S3
- Add Web UI dashboard via OpenSearch Dashboards

---

## License
MIT – free to use, modify and extend.

Original: [https://github.com/bikemazzell/stealer-log-processor](https://github.com/bikemazzell/stealer-log-processor)
