import csv
import json
import os
import shutil
import datetime
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

CSV_FILE = 'idea_census_project_registry_ic_numbers.csv'
BACKUP_DIR = 'backups'
PORT = int(os.environ.get('PORT', 8765))

# Ensure backup dir exists
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Idea Census Registry</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        h1 { color: #fff; font-size: 1.5rem; margin-bottom: 10px; margin-top: 0; }
        .navbar { display: flex; justify-content: space-between; align-items: center; background: #1f1f1f; padding: 15px 20px; margin: -20px -20px 20px -20px; border-bottom: 1px solid #333; flex-wrap: wrap; gap: 10px; }
        .nav-links a { color: #aaa; text-decoration: none; margin-right: 20px; font-weight: bold; font-size: 14px; }
        .nav-links a:hover, .nav-links a.active { color: #fff; border-bottom: 2px solid #2d5a27; padding-bottom: 5px; }
        .nav-exports button { background: #2d5a27; border: 1px solid #3b7533; color: #fff; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; margin-left: 5px; transition: background 0.2s; }
        .nav-exports button:hover { background: #3b7533; }
        
        .view { display: none; }
        .view.active { display: block; }
        
        .controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
        input, select, button { padding: 8px; border-radius: 4px; border: 1px solid #444; background: #222; color: #fff; font-size: 14px; }
        input[type="text"] { flex-grow: 1; min-width: 200px; }
        button { cursor: pointer; background: #333; transition: background 0.2s; }
        button:hover { background: #555; }
        
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th, td { border: 1px solid #333; padding: 8px 12px; text-align: left; }
        th { background: #1f1f1f; position: sticky; top: 0; font-weight: 600; color: #aaa; text-transform: uppercase; font-size: 12px; }
        tr:nth-child(even) { background: #161616; }
        tr:hover { background: #2a2a2a; cursor: pointer; }
        
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); backdrop-filter: blur(2px); z-index: 100; }
        .modal-content { background: #1e1e1e; margin: 5% auto; padding: 25px; width: 90%; max-width: 700px; border-radius: 8px; max-height: 85vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); border: 1px solid #333; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .modal-header h2 { margin: 0; font-size: 1.25rem; color: #fff; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px; color: #aaa; }
        .form-group input, .form-group textarea { width: 100%; box-sizing: border-box; }
        .form-group textarea { height: 100px; resize: vertical; font-family: inherit; }
        
        .stats { margin-bottom: 15px; font-size: 14px; color: #999; display: flex; gap: 15px; flex-wrap: wrap; background: #1a1a1a; padding: 10px 15px; border-radius: 4px; border: 1px solid #222; }
        .stats span { display: flex; align-items: center; }
        .stats b { color: #fff; margin-left: 5px; }
        .close { cursor: pointer; font-size: 1.5em; line-height: 1; color: #aaa; }
        .close:hover { color: #fff; }
        .footer { margin-top: 20px; display: flex; justify-content: flex-end; gap: 10px; }
        .btn-save { background: #2d5a27; font-weight: bold; border-color: #3b7533; }
        .btn-save:hover { background: #3b7533; }
        .btn-cancel { background: #444; }
        .btn-cancel:hover { background: #555; }

        .upload-box { background: #1a1a1a; padding: 25px; border: 1px solid #333; border-radius: 6px; max-width: 600px; }
        .upload-box h2 { margin-top: 0; margin-bottom: 20px; font-size: 1.2rem; }
        .upload-box input[type="file"] { width: 100%; padding: 10px; background: #222; margin-bottom: 15px; border: 1px solid #444; border-radius: 4px; }
        .upload-box select { width: 100%; padding: 10px; margin-bottom: 20px; font-size: 14px; }
        .upload-box button { width: 100%; padding: 10px; background: #2d5a27; font-weight: bold; border-color: #3b7533; }
        .upload-box button:hover { background: #3b7533; }
        .summary-box { background: #162616; padding: 20px; border: 1px solid #2d5a27; border-radius: 6px; max-width: 600px; margin-top: 20px; color: #b0e0b0; }
        .summary-box h3 { margin-top: 0; color: #fff; }
        .summary-box ul { margin: 10px 0; padding-left: 20px; }
        .summary-box li { margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="nav-links">
            <a href="#" onclick="showView('registry')" id="nav-registry" class="active">Registry</a>
            <a href="#" onclick="showView('upload')" id="nav-upload">Upload CSV</a>
            <a href="#" onclick="openModal({}, true)">New IC Record</a>
        </div>
        <div class="nav-exports">
            <button onclick="exportCSV()">Export CSV</button>
            <button onclick="exportTSV()">Export TSV</button>
            <button onclick="exportJSON()">Export JSON</button>
        </div>
    </div>

    <div id="registryView" class="view active">
        <h1>Idea Census Registry</h1>
        <div class="stats" id="stats">
            <span>Loading stats...</span>
        </div>

        <div class="controls">
            <input type="text" id="searchInput" placeholder="Search everywhere...">
            <select id="domainFilter"><option value="">All Domains</option></select>
            <select id="statusFilter"><option value="">All Statuses</option></select>
            <select id="priorityFilter"><option value="">All Priorities</option></select>
            <select id="confidenceFilter"><option value="">All Confidences</option></select>
        </div>

        <table id="dataTable">
            <thead>
                <tr id="tableHead"></tr>
            </thead>
            <tbody id="tableBody"></tbody>
        </table>
    </div>

    <div id="uploadView" class="view">
        <h1>Upload Registry</h1>
        <div class="upload-box">
            <h2>Import File</h2>
            <input type="file" id="csvFileInput" accept=".csv, .tsv, text/csv, text/tab-separated-values">
            <select id="uploadMode">
                <option value="replace">Replace current registry</option>
                <option value="merge">Merge into current registry by IC Number</option>
            </select>
            <button onclick="handleUpload()">Upload File</button>
        </div>
        <div id="uploadSummary" class="summary-box" style="display:none;"></div>
    </div>

    <div id="editModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle">Edit Record</h2>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <form id="editForm"></form>
            <div class="footer">
                <button type="button" class="btn-cancel" onclick="closeModal()">Cancel</button>
                <button type="button" class="btn-save" onclick="saveRecord()">Save Changes</button>
            </div>
        </div>
    </div>

    <script>
        let allData = [];
        let filteredData = [];
        
        const editableColumns = [
            "Project", "Domain", "Status", "Priority", "Confidence", 
            "Aliases", "Top Related Concepts", "Basis", "Source Files", "Notes"
        ];
        
        const displayColumns = [
            "IC Number", "Project", "Domain", "Status", "Priority", "Confidence", "First Seen"
        ];

        function showView(viewId) {
            document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-links a').forEach(el => el.classList.remove('active'));
            
            document.getElementById(viewId + 'View').classList.add('active');
            const navItem = document.getElementById('nav-' + viewId);
            if(navItem) navItem.classList.add('active');
        }

        async function loadData() {
            try {
                const response = await fetch('/api/data');
                if (!response.ok) throw new Error("Could not load data");
                allData = await response.json();
                populateFilters();
                applyFilters();
            } catch (e) {
                document.getElementById('stats').innerHTML = `<span style="color:#ff5555;">Error loading data: ${e.message}</span>`;
            }
        }

        function populateFilters() {
            const domains = new Set();
            const statuses = new Set();
            const priorities = new Set();
            const confidences = new Set();

            allData.forEach(row => {
                if(row["Domain"]) domains.add(row["Domain"]);
                if(row["Status"]) statuses.add(row["Status"]);
                if(row["Priority"]) priorities.add(row["Priority"]);
                if(row["Confidence"]) confidences.add(row["Confidence"]);
            });

            populateSelect("domainFilter", domains, "All Domains");
            populateSelect("statusFilter", statuses, "All Statuses");
            populateSelect("priorityFilter", priorities, "All Priorities");
            populateSelect("confidenceFilter", confidences, "All Confidences");
        }

        function populateSelect(id, values, defaultText) {
            const select = document.getElementById(id);
            select.innerHTML = `<option value="">${defaultText}</option>`;
            Array.from(values).sort().forEach(val => {
                const opt = document.createElement("option");
                opt.value = val;
                opt.textContent = val;
                select.appendChild(opt);
            });
            select.addEventListener('change', applyFilters);
        }

        document.getElementById('searchInput').addEventListener('input', applyFilters);

        function applyFilters() {
            const q = document.getElementById('searchInput').value.toLowerCase();
            const domain = document.getElementById('domainFilter').value;
            const status = document.getElementById('statusFilter').value;
            const priority = document.getElementById('priorityFilter').value;
            const confidence = document.getElementById('confidenceFilter').value;

            filteredData = allData.filter(row => {
                let match = true;
                if (domain && row["Domain"] !== domain) match = false;
                if (status && row["Status"] !== status) match = false;
                if (priority && row["Priority"] !== priority) match = false;
                if (confidence && row["Confidence"] !== confidence) match = false;
                
                if (match && q) {
                    const rowText = Object.values(row).join(' ').toLowerCase();
                    if (!rowText.includes(q)) match = false;
                }
                return match;
            });

            renderTable();
            updateStats();
        }

        function updateStats() {
            const total = allData.length;
            const visible = filteredData.length;
            const active = allData.filter(r => r["Status"] && r["Status"].toLowerCase() === "active").length;
            const p0 = allData.filter(r => r["Priority"] === "P0").length;
            const p1 = allData.filter(r => r["Priority"] === "P1").length;

            document.getElementById('stats').innerHTML = `
                <span>Total: <b>${total}</b></span>
                <span>Visible: <b>${visible}</b></span>
                <span>Active: <b>${active}</b></span>
                <span>P0: <b>${p0}</b></span>
                <span>P1: <b>${p1}</b></span>
            `;
        }

        function renderTable() {
            const thead = document.getElementById('tableHead');
            const tbody = document.getElementById('tableBody');
            thead.innerHTML = '';
            tbody.innerHTML = '';

            displayColumns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                thead.appendChild(th);
            });

            filteredData.forEach(row => {
                const tr = document.createElement('tr');
                tr.onclick = () => openModal(row);
                displayColumns.forEach(col => {
                    const td = document.createElement('td');
                    td.textContent = row[col] || '';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
        }

        let currentRecordId = null;

        function openModal(row = {}, isNew = false) {
            currentRecordId = isNew ? null : row["IC Number"];
            document.getElementById('modalTitle').textContent = isNew ? "New IC Record" : `Edit ${currentRecordId} - ${row["Project"] || 'Unknown'}`;
            
            const form = document.getElementById('editForm');
            form.innerHTML = '';

            if (isNew) {
                const group = document.createElement('div');
                group.className = 'form-group';
                const label = document.createElement('label');
                label.textContent = "IC Number (e.g. IC-000099)";
                const input = document.createElement('input');
                input.type = 'text';
                input.id = 'edit_IC_Number';
                input.value = '';
                group.appendChild(label);
                group.appendChild(input);
                form.appendChild(group);
            }

            editableColumns.forEach(col => {
                const group = document.createElement('div');
                group.className = 'form-group';
                
                const label = document.createElement('label');
                label.textContent = col;
                
                let input;
                if (["Notes", "Source Files", "Aliases", "Top Related Concepts"].includes(col)) {
                    input = document.createElement('textarea');
                } else {
                    input = document.createElement('input');
                    input.type = 'text';
                }
                input.id = 'edit_' + col.replace(/\s+/g, '_');
                input.value = row[col] || '';
                
                group.appendChild(label);
                group.appendChild(input);
                form.appendChild(group);
            });
            
            document.getElementById('editModal').style.display = 'block';
        }

        function closeModal() {
            document.getElementById('editModal').style.display = 'none';
        }

        async function saveRecord() {
            let idToSave = currentRecordId;
            if (!idToSave) {
                const icInput = document.getElementById('edit_IC_Number');
                if (!icInput || !icInput.value.trim()) {
                    alert("IC Number is required for new records.");
                    return;
                }
                idToSave = icInput.value.trim();
            }

            const updates = { "IC Number": idToSave };
            editableColumns.forEach(col => {
                const el = document.getElementById('edit_' + col.replace(/\s+/g, '_'));
                if (el) updates[col] = el.value;
            });

            try {
                const response = await fetch('/api/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates)
                });
                
                if (!response.ok) {
                    const err = await response.text();
                    throw new Error(err);
                }
                
                // Update local data
                const idx = allData.findIndex(r => r["IC Number"] === idToSave);
                if (idx !== -1) {
                    allData[idx] = { ...allData[idx], ...updates };
                } else {
                    allData.push(updates); // Append if new
                }
                
                closeModal();
                populateFilters();
                applyFilters();
            } catch (e) {
                alert("Error saving: " + e.message);
            }
        }

        async function handleUpload() {
            const fileInput = document.getElementById('csvFileInput');
            const mode = document.getElementById('uploadMode').value;
            const summaryBox = document.getElementById('uploadSummary');
            
            if (!fileInput.files.length) {
                alert("Please select a file first.");
                return;
            }
            
            const file = fileInput.files[0];
            const reader = new FileReader();
            
            reader.onload = async function(e) {
                const content = e.target.result;
                summaryBox.style.display = 'block';
                summaryBox.innerHTML = "Uploading and processing...";
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fileContent: content, mode: mode })
                    });
                    
                    const result = await response.json();
                    if (!response.ok || result.error) {
                        summaryBox.innerHTML = `<span style="color:#ff5555;">Error: ${result.error || response.statusText}</span>`;
                    } else {
                        const s = result.summary;
                        summaryBox.innerHTML = `
                            <h3>Upload Successful</h3>
                            <ul>
                                <li>Rows imported: ${s.imported}</li>
                                <li>Rows updated: ${s.updated}</li>
                                <li>Rows added: ${s.added}</li>
                                <li>Rows skipped (no valid ID): ${s.skipped}</li>
                                <li>Backup created: ${s.backup_file || 'None'}</li>
                            </ul>
                            <button onclick="showView('registry'); loadData();" style="margin-top: 15px; padding: 8px 16px; background: #2d5a27; color: #fff; border: 1px solid #3b7533; border-radius: 4px; cursor: pointer;">Return to Registry</button>
                        `;
                    }
                } catch (err) {
                    summaryBox.innerHTML = `<span style="color:#ff5555;">Error: ${err.message}</span>`;
                }
            };
            
            reader.readAsText(file);
        }

        function exportCSV() {
            window.location.href = '/api/export/csv';
        }

        function exportTSV() {
            window.location.href = '/api/export/tsv';
        }

        function exportJSON() {
            window.location.href = '/api/export/json';
        }

        // Close modal if clicked outside
        window.onclick = function(event) {
            const modal = document.getElementById('editModal');
            if (event.target == modal) {
                closeModal();
            }
        }

        loadData();
    </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def read_csv(self):
        if not os.path.exists(CSV_FILE):
            return []
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def write_csv(self, data):
        if not data:
            return
            
        fieldnames = []
        for row in data:
            for k in row.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
                    
        with open(CSV_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def do_GET(self):
        parsed_path = urlparse(self.path).path
        
        if parsed_path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
            
        elif parsed_path == '/api/data':
            data = self.read_csv()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
            
        elif parsed_path == '/api/export/csv':
            if os.path.exists(CSV_FILE):
                self.send_response(200)
                self.send_header('Content-Disposition', f'attachment; filename="idea_census_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"')
                self.send_header('Content-type', 'text/csv; charset=utf-8')
                self.end_headers()
                with open(CSV_FILE, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "CSV file not found")

        elif parsed_path == '/api/export/tsv':
            if os.path.exists(CSV_FILE):
                data = self.read_csv()
                self.send_response(200)
                self.send_header('Content-Disposition', f'attachment; filename="idea_census_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.tsv"')
                self.send_header('Content-type', 'text/tab-separated-values; charset=utf-8')
                self.end_headers()
                
                if data:
                    fieldnames = []
                    for row in data:
                        for k in row.keys():
                            if k not in fieldnames:
                                fieldnames.append(k)
                    
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter='\t')
                    writer.writeheader()
                    writer.writerows(data)
                    self.wfile.write(output.getvalue().encode('utf-8'))
            else:
                self.send_error(404, "CSV file not found")
                
        elif parsed_path == '/api/export/json':
            data = self.read_csv()
            self.send_response(200)
            self.send_header('Content-Disposition', f'attachment; filename="idea_census_export_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json"')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
            
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path).path
        
        if parsed_path == '/api/save':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                updates = json.loads(post_data.decode('utf-8'))
                ic_number = updates.get('IC Number')
                
                if not ic_number:
                    self.send_error(400, "Missing IC Number")
                    return
                
                if os.path.exists(CSV_FILE):
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.csv")
                    shutil.copy2(CSV_FILE, backup_path)
                
                data = self.read_csv()
                updated = False
                for row in data:
                    if row.get('IC Number') == ic_number:
                        for k, v in updates.items():
                            if k != 'IC Number':
                                row[k] = v
                        updated = True
                        break
                
                if not updated:
                    data.append(updates)
                
                self.write_csv(data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, str(e))
                
        elif parsed_path == '/api/upload':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                file_content = payload.get('fileContent', '')
                mode = payload.get('mode', 'replace')
                
                if not file_content:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "File content is empty."}).encode('utf-8'))
                    return
                    
                first_line = file_content.split('\n')[0]
                delimiter = '\t' if '\t' in first_line and first_line.count('\t') >= first_line.count(',') else ','
                
                reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)
                rows = list(reader)
                
                if not rows:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "No data rows found in file."}).encode('utf-8'))
                    return
                    
                id_col = None
                for col in reader.fieldnames:
                    if col and col.lower() in ['ic number', 'ic', 'id']:
                        id_col = col
                        break
                        
                if not id_col:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"No recognizable identifier column found. Expected one of: IC Number, IC, Id, ID."}).encode('utf-8'))
                    return
                    
                processed_rows = []
                skipped = 0
                for r in rows:
                    raw_id = r.get(id_col, '').strip()
                    if not raw_id:
                        skipped += 1
                        continue
                        
                    if raw_id.isdigit():
                        norm_id = f"IC-{int(raw_id):06d}"
                    else:
                        norm_id = raw_id
                        
                    r['IC Number'] = norm_id
                    if id_col != 'IC Number':
                        del r[id_col]
                    processed_rows.append(r)
                    
                backup_file = None
                current_data = []
                if os.path.exists(CSV_FILE):
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_file = f"backup_{timestamp}_pre_upload.csv"
                    backup_path = os.path.join(BACKUP_DIR, backup_file)
                    shutil.copy2(CSV_FILE, backup_path)
                    
                    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                        current_data = list(csv.DictReader(f))
                        
                updated = 0
                added = 0
                imported = len(processed_rows)
                
                if mode == 'replace':
                    self.write_csv(processed_rows)
                    added = imported
                else:
                    current_dict = {row['IC Number']: row for row in current_data if row.get('IC Number')}
                    for pr in processed_rows:
                        ic = pr['IC Number']
                        if ic in current_dict:
                            current_dict[ic].update(pr)
                            updated += 1
                        else:
                            current_dict[ic] = pr
                            added += 1
                    self.write_csv(list(current_dict.values()))
                    
                summary = {
                    "imported": imported,
                    "updated": updated,
                    "added": added,
                    "skipped": skipped,
                    "backup_file": backup_file
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "summary": summary}).encode('utf-8'))
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

def run():
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    print("========================================")
    print(f"Idea Census Registry Web App")
    print(f"Running at: http://{server_address[0]}:{server_address[1]}")
    print(f"Using CSV file: {CSV_FILE}")
    print(f"Backups directory: {BACKUP_DIR}/")
    print("Press Ctrl+C to stop.")
    print("========================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()