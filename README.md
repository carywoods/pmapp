# Idea Census Registry Web App

A lightweight, zero-dependency local web application to view, search, filter, edit, and export the Idea Census project registry. This replaces the previous complex workflow with a simple, durable, and fast local-first solution.

## Prerequisites

- **Python 3.6+** (No external dependencies required)
- A CSV file named `idea_census_project_registry_ic_numbers.csv` placed in the same directory as `app.py`.

## Getting Started Locally

1. Ensure your dataset is named `idea_census_project_registry_ic_numbers.csv` and located in the same directory as the script.
2. Open your terminal, navigate to the project directory, and run the following command:

```bash
python3 app.py
```

3. Open your web browser and navigate to the local URL:
   [http://127.0.0.1:8765](http://127.0.0.1:8765) (or the port specified by the `$PORT` environment variable).

## Deploying via Coolify

This app is built to be easily deployed using Coolify with zero additional configuration required, leveraging standard Nixpacks detection.

1. Connect your repository to Coolify.
2. Coolify will automatically detect it as a Python application (thanks to `requirements.txt` and `Procfile`).
3. **CRITICAL: Persistent Storage**
   Because this app uses a local CSV file and stores backups, you **must** configure a persistent volume in Coolify to prevent data loss when the container restarts or redeploys.
   - In your Coolify resource settings for this app, go to **Storages**.
   - Add a volume mapping. For example:
     - Volume Name: `idea_census_data`
     - Destination Path: `/app` (or wherever Coolify sets your working directory, typically `/app`).
   - *Alternative:* You can map a specific directory for the CSV and backups if you update the `app.py` variables (`CSV_FILE` and `BACKUP_DIR`), but mapping the entire `/app` directory ensures both the app code and the generated data persist.
4. Ensure your initial `idea_census_project_registry_ic_numbers.csv` file is placed in that persistent volume before you begin using the app in production.
5. Deploy the application.

## Storage Model

This app relies entirely on a **local-first CSV storage model**:
- The registry acts as the single source of truth and is stored directly in `idea_census_project_registry_ic_numbers.csv`.
- There is **no database** (no SQLite, MySQL, etc.). The script directly reads from and writes to the CSV file.
- The `IC Number` column is used as the stable unique identifier for each project record. It is never treated as a database auto-increment ID and cannot be modified via the UI, ensuring data integrity.
- If the original CSV contains extra columns not explicitly displayed or edited in the UI, they will be seamlessly preserved during saves.

## Backups

Data safety is a core feature:
- Every time you click "Save Changes" on a record, the app creates a full backup of the current CSV *before* writing the updated data.
- Backups are stored in the `backups/` directory (automatically created if it doesn't exist).
- Backup files are timestamped (e.g., `backup_20260502_153045.csv`) so you can easily trace the history or revert to an exact point in time if needed.
- The application will **never** overwrite the original CSV without first safely copying the old version to the `backups/` folder.

## Features

- **Search & Filtering**: Search across all text fields instantly. Filter by Domain, Status, Priority, and Confidence.
- **Dynamic Stats**: Real-time counts for total records, visible records, active records, and P0/P1 priorities.
- **Editing**: Click any row to open the edit modal. Update fields seamlessly.
- **Exports**: Export your full dataset or current state to a timestamped CSV or JSON file with a single click.

## UI

The interface is built with vanilla HTML/JS/CSS embedded directly into `app.py` for maximum portability. It features a clean, dark-themed responsive table layout.