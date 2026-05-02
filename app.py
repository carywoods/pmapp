import csv
import json
import os
import shutil
import datetime
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
        h1 { color: #fff; font-size: 1.5rem; margin-bottom: 10px; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
        input, select, button { padding: 8px; border-radius: 4px; border: 1px solid #444; background: #222; color: #fff; font-size: 14px; }
        input[type="text"] { flex-grow: 1; min-width: 200px; }
        button { cursor: pointer; background: #333; transition: background 0.2s; }
        button:hover { background: #555; }
        .export-btn { background: #2d5a27; border-color: #3b7533; }
        .export-btn:hover { background: #3b7533; }
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
    </style>
</head>
<body>
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
        <button class="export-btn" onclick="exportCSV()">CSV Export</button>
        <button class="export-btn" onclick="exportJSON()">JSON Export</button>
    </div>

    <table id="dataTable">
        <thead>
            <tr id="tableHead"></tr>
        </thead>
        <tbody id="tableBody"></tbody>
    </table>

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

        function openModal(row) {
            currentRecordId = row["IC Number"];
            document.getElementById('modalTitle').textContent = `Edit ${currentRecordId} - ${row["Project"] || 'Unknown'}`;
            
            const form = document.getElementById('editForm');
            form.innerHTML = '';

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
            if (!currentRecordId) return;

            const updates = { "IC Number": currentRecordId };
            editableColumns.forEach(col => {
                updates[col] = document.getElementById('edit_' + col.replace(/\s+/g, '_')).value;
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
                const idx = allData.findIndex(r => r["IC Number"] === currentRecordId);
                if (idx !== -1) {
                    allData[idx] = { ...allData[idx], ...updates };
                }
                
                closeModal();
                applyFilters();
                // Brief flash to indicate saving success could be added here
            } catch (e) {
                alert("Error saving: " + e.message);
            }
        }

        function exportCSV() {
            window.location.href = '/api/export/csv';
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
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def write_csv(self, data):
        if not data:
            return
            
        # Collect all unique fieldnames to preserve unknown columns
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
                
                # Backup before saving
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
                    self.send_error(404, "IC Number not found")
                    return
                
                self.write_csv(data)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, str(e))
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
