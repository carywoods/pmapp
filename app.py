import csv
import datetime
import io
import json
import os
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

CSV_FILE = "idea_census_project_registry_ic_numbers.csv"
BACKUP_DIR = "backups"
PORT = int(os.environ.get("PORT", 8765))
IC_WIDTH = 6
STATUS_OPTIONS = ["New", "Active", "Queued", "On Hold", "In Progress", "Completed", "Archived"]
PRIORITY_OPTIONS = ["P0", "P1", "P2", "P3"]
CONFIDENCE_OPTIONS = ["Low", "Medium", "High"]

os.makedirs(BACKUP_DIR, exist_ok=True)


def today_iso():
    return datetime.date.today().isoformat()


def ic_int(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else 0


def format_ic(value):
    return f"IC-{int(value):0{IC_WIDTH}d}"


def next_ic(rows):
    return format_ic(max([ic_int(r.get("IC Number") or r.get("IC") or r.get("Id") or r.get("ID")) for r in rows] + [0]) + 1)


def completed(row):
    return str(row.get("Status", "")).strip().lower() in {"complete", "completed", "done", "closed"}


HTML_CONTENT = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Idea Census Registry</title>
<style>
body{font-family:system-ui,sans-serif;background:#121212;color:#e0e0e0;margin:0;padding:20px}h1{font-size:1.5rem;margin:0 0 12px}.navbar{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;background:#1f1f1f;margin:-20px -20px 20px;padding:15px 20px;border-bottom:1px solid #333}.nav-links a{color:#aaa;text-decoration:none;margin-right:18px;font-weight:700;font-size:14px}.nav-links a:hover,.nav-links a.active{color:#fff;border-bottom:2px solid #2d5a27;padding-bottom:5px}.nav-exports button,.btn-save,.upload-box button{background:#2d5a27;border-color:#3b7533}.view{display:none}.view.active{display:block}.controls{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;align-items:center}input,select,button,textarea{padding:8px;border-radius:4px;border:1px solid #444;background:#222;color:#fff;font-size:14px}input[type=text]{flex-grow:1;min-width:200px}button{cursor:pointer;background:#333}.toggle-label{display:inline-flex;align-items:center;gap:6px;background:#1a1a1a;border:1px solid #333;padding:7px 10px;border-radius:4px;color:#ccc}table{width:100%;border-collapse:collapse;font-size:14px}th,td{border:1px solid #333;padding:8px 12px;text-align:left}th{background:#1f1f1f;position:sticky;top:0;color:#aaa;text-transform:uppercase;font-size:12px}tr:nth-child(even){background:#161616}tr:hover{background:#2a2a2a;cursor:pointer}.stats{margin-bottom:15px;font-size:14px;color:#999;display:flex;gap:15px;flex-wrap:wrap;background:#1a1a1a;padding:10px 15px;border-radius:4px;border:1px solid #222}.stats b{color:#fff;margin-left:5px}.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(2px);z-index:100}.modal-content{background:#1e1e1e;margin:5% auto;padding:25px;width:90%;max-width:700px;border-radius:8px;max-height:85vh;overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,.5);border:1px solid #333}.modal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;border-bottom:1px solid #333;padding-bottom:10px}.modal-header h2{margin:0;font-size:1.25rem}.close{cursor:pointer;font-size:1.5em;color:#aaa}.form-group{margin-bottom:15px}.form-group label{display:block;margin-bottom:6px;font-weight:700;font-size:13px;color:#aaa}.form-group input,.form-group textarea,.form-group select{width:100%;box-sizing:border-box}.form-group textarea{height:100px;resize:vertical;font-family:inherit}.readonly-field{background:#181818;color:#aaa}.footer{margin-top:20px;display:flex;justify-content:flex-end;gap:10px}.upload-box,.summary-box{padding:25px;border-radius:6px;max-width:650px}.upload-box{background:#1a1a1a;border:1px solid #333}.upload-box input,.upload-box select,.upload-box button{width:100%;box-sizing:border-box;margin-bottom:15px}.summary-box{display:none;background:#162616;border:1px solid #2d5a27;color:#b0e0b0;margin-top:20px}
</style>
</head>
<body>
<div class="navbar"><div class="nav-links"><a href="#" onclick="showView('registry')" id="nav-registry" class="active">Registry</a><a href="#" onclick="showView('upload')" id="nav-upload">Upload CSV</a><a href="#" onclick="openModal({},true)">New IC Record</a></div><div class="nav-exports"><button onclick="exportFile('csv')">Export CSV</button><button onclick="exportFile('tsv')">Export TSV</button><button onclick="exportFile('json')">Export JSON</button></div></div>
<div id="registryView" class="view active"><h1>Idea Census Registry</h1><div class="stats" id="stats">Loading stats...</div><div class="controls"><input type="text" id="searchInput" placeholder="Search everywhere..."><select id="domainFilter"><option value="">All Domains</option></select><select id="statusFilter"><option value="">All Statuses</option></select><select id="priorityFilter"><option value="">All Priorities</option></select><select id="confidenceFilter"><option value="">All Confidences</option></select><label class="toggle-label"><input type="checkbox" id="showCompletedToggle"> Show completed</label></div><table><thead><tr id="tableHead"></tr></thead><tbody id="tableBody"></tbody></table></div>
<div id="uploadView" class="view"><h1>Upload Registry</h1><div class="upload-box"><h2>Import File</h2><input type="file" id="csvFileInput" accept=".csv,.tsv,text/csv,text/tab-separated-values"><select id="uploadMode"><option value="replace">Replace current registry</option><option value="merge">Merge into current registry by IC Number</option></select><button onclick="handleUpload()">Upload File</button></div><div id="uploadSummary" class="summary-box"></div></div>
<div id="editModal" class="modal"><div class="modal-content"><div class="modal-header"><h2 id="modalTitle">Edit Record</h2><span class="close" onclick="closeModal()">&times;</span></div><form id="editForm"></form><div class="footer"><button type="button" onclick="closeModal()">Cancel</button><button type="button" class="btn-save" onclick="saveRecord()">Save Changes</button></div></div></div>
<script>
let allData=[];let filteredData=[];let currentRecordId=null;const IC_WIDTH=6;
const statusOptions=['New','Active','Queued','On Hold','In Progress','Completed','Archived'];
const priorityOptions=['P0','P1','P2','P3'];const confidenceOptions=['Low','Medium','High'];
const editableColumns=['Project','Domain','Status','Priority','Confidence','Aliases','Top Related Concepts','Basis','Source Files','Notes'];
const displayColumns=['IC Number','Project','Domain','Status','Priority','Confidence','First Seen'];
function todayIso(){const d=new Date();return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,10)}
function icNum(v){const d=String(v||'').replace(/[^0-9]/g,'');return d?parseInt(d,10):0}
function formatIc(n){return `IC-${String(n).padStart(IC_WIDTH,'0')}`}
function getNextIc(){return formatIc(allData.reduce((m,r)=>Math.max(m,icNum(r['IC Number']||r.IC||r.Id||r.ID)),0)+1)}
function isCompleted(r){return ['complete','completed','done','closed'].includes(String(r.Status||'').trim().toLowerCase())}
function showView(v){document.querySelectorAll('.view').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.nav-links a').forEach(e=>e.classList.remove('active'));document.getElementById(v+'View').classList.add('active');const nav=document.getElementById('nav-'+v);if(nav)nav.classList.add('active')}
async function loadData(){try{const res=await fetch('/api/data');if(!res.ok)throw new Error('Could not load data');allData=await res.json();populateFilters();applyFilters()}catch(e){document.getElementById('stats').innerHTML=`<span style="color:#ff5555">Error loading data: ${e.message}</span>`}}
function populateFilters(){const domains=new Set(),statuses=new Set(statusOptions),priorities=new Set(priorityOptions),confidences=new Set(confidenceOptions);allData.forEach(r=>{if(r.Domain)domains.add(r.Domain);if(r.Status)statuses.add(r.Status);if(r.Priority)priorities.add(r.Priority);if(r.Confidence)confidences.add(r.Confidence)});fillSelect('domainFilter',domains,'All Domains');fillSelect('statusFilter',statuses,'All Statuses');fillSelect('priorityFilter',priorities,'All Priorities');fillSelect('confidenceFilter',confidences,'All Confidences')}
function fillSelect(id,values,label){const s=document.getElementById(id),cur=s.value;s.innerHTML=`<option value="">${label}</option>`;Array.from(values).filter(Boolean).sort().forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;s.appendChild(o)});s.value=Array.from(s.options).some(o=>o.value===cur)?cur:'';s.onchange=applyFilters}
document.getElementById('searchInput').addEventListener('input',applyFilters);document.getElementById('showCompletedToggle').addEventListener('change',applyFilters);
function applyFilters(){const q=document.getElementById('searchInput').value.toLowerCase(),domain=document.getElementById('domainFilter').value,status=document.getElementById('statusFilter').value,priority=document.getElementById('priorityFilter').value,confidence=document.getElementById('confidenceFilter').value,showCompleted=document.getElementById('showCompletedToggle').checked;filteredData=allData.filter(r=>{if(!showCompleted&&isCompleted(r))return false;if(domain&&r.Domain!==domain)return false;if(status&&r.Status!==status)return false;if(priority&&r.Priority!==priority)return false;if(confidence&&r.Confidence!==confidence)return false;if(q&&!Object.values(r).join(' ').toLowerCase().includes(q))return false;return true});renderTable();updateStats()}
function updateStats(){const total=allData.length,visible=filteredData.length,done=allData.filter(isCompleted).length,active=allData.filter(r=>String(r.Status||'').toLowerCase()==='active').length,p0=allData.filter(r=>r.Priority==='P0').length,p1=allData.filter(r=>r.Priority==='P1').length;document.getElementById('stats').innerHTML=`<span>Total:<b>${total}</b></span><span>Visible:<b>${visible}</b></span><span>Active:<b>${active}</b></span><span>Completed:<b>${done}</b></span><span>P0:<b>${p0}</b></span><span>P1:<b>${p1}</b></span>`}
function renderTable(){const h=document.getElementById('tableHead'),b=document.getElementById('tableBody');h.innerHTML='';b.innerHTML='';displayColumns.forEach(c=>{const th=document.createElement('th');th.textContent=c;h.appendChild(th)});filteredData.forEach(r=>{const tr=document.createElement('tr');tr.onclick=()=>openModal(r,false);displayColumns.forEach(c=>{const td=document.createElement('td');td.textContent=r[c]||'';tr.appendChild(td)});b.appendChild(tr)})}
function readonly(form,label,id,value){const g=document.createElement('div');g.className='form-group';g.innerHTML=`<label>${label}</label>`;const i=document.createElement('input');i.type='text';i.id=id;i.value=value||'';i.readOnly=true;i.className='readonly-field';g.appendChild(i);form.appendChild(g)}
function optionInput(col,value){const s=document.createElement('select'),opts=col==='Status'?statusOptions:col==='Priority'?priorityOptions:confidenceOptions;if(!value){const b=document.createElement('option');b.value='';b.textContent=`Select ${col}`;s.appendChild(b)}opts.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;s.appendChild(o)});if(value&&!opts.includes(value)){const o=document.createElement('option');o.value=value;o.textContent=value;s.appendChild(o)}s.value=value||'';return s}
function openModal(row={},isNew=false){currentRecordId=isNew?getNextIc():row['IC Number'];const firstSeen=isNew?todayIso():(row['First Seen']||todayIso());document.getElementById('modalTitle').textContent=isNew?`New IC Record ${currentRecordId}`:`Edit ${currentRecordId} - ${row.Project||'Unknown'}`;const f=document.getElementById('editForm');f.innerHTML='';readonly(f,'IC Number','edit_IC_Number',currentRecordId);readonly(f,'First Seen','edit_First_Seen',firstSeen);editableColumns.forEach(c=>{const g=document.createElement('div');g.className='form-group';const l=document.createElement('label');l.textContent=c;let inp;if(['Status','Priority','Confidence'].includes(c))inp=optionInput(c,row[c]||'');else if(['Notes','Source Files','Aliases','Top Related Concepts'].includes(c)){inp=document.createElement('textarea');inp.value=row[c]||''}else{inp=document.createElement('input');inp.type='text';inp.value=row[c]||''}inp.id='edit_'+c.replace(/\s+/g,'_');g.appendChild(l);g.appendChild(inp);f.appendChild(g)});document.getElementById('editModal').style.display='block'}
function closeModal(){document.getElementById('editModal').style.display='none'}
async function saveRecord(){const updates={'IC Number':document.getElementById('edit_IC_Number').value,'First Seen':document.getElementById('edit_First_Seen').value||todayIso()};editableColumns.forEach(c=>{const el=document.getElementById('edit_'+c.replace(/\s+/g,'_'));if(el)updates[c]=el.value});try{const res=await fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(updates)});if(!res.ok)throw new Error(await res.text());const saved=(await res.json()).record;const idx=allData.findIndex(r=>r['IC Number']===saved['IC Number']);if(idx>=0)allData[idx]={...allData[idx],...saved};else allData.push(saved);closeModal();populateFilters();applyFilters()}catch(e){alert('Error saving: '+e.message)}}
async function handleUpload(){const input=document.getElementById('csvFileInput'),mode=document.getElementById('uploadMode').value,box=document.getElementById('uploadSummary');if(!input.files.length){alert('Please select a file first.');return}const reader=new FileReader();reader.onload=async e=>{box.style.display='block';box.textContent='Uploading and processing...';try{const res=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fileContent:e.target.result,mode})});const result=await res.json();if(!res.ok||result.error){box.innerHTML=`<span style="color:#ff5555">Error: ${result.error||res.statusText}</span>`;return}const s=result.summary;box.innerHTML=`<h3>Upload Successful</h3><ul><li>Rows imported: ${s.imported}</li><li>Rows updated: ${s.updated}</li><li>Rows added: ${s.added}</li><li>Rows skipped: ${s.skipped}</li><li>Backup created: ${s.backup_file||'None'}</li></ul><button onclick="showView('registry');loadData()">Return to Registry</button>`}catch(err){box.innerHTML=`<span style="color:#ff5555">Error: ${err.message}</span>`}};reader.readAsText(input.files[0])}
function exportFile(kind){window.location.href='/api/export/'+kind}window.onclick=e=>{const m=document.getElementById('editModal');if(e.target===m)closeModal()};loadData();
</script>
</body>
</html>'''


class RequestHandler(BaseHTTPRequestHandler):
    def read_csv(self):
        if not os.path.exists(CSV_FILE):
            return []
        with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def write_csv(self, rows):
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        preferred = ["IC Number", "Project", "Domain", "Status", "Priority", "Confidence", "First Seen"]
        fieldnames = [f for f in preferred if f in fieldnames] + [f for f in fieldnames if f not in preferred]
        with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def backup_csv(self, suffix=""):
        if not os.path.exists(CSV_FILE):
            return None
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"backup_{stamp}{suffix}.csv"
        shutil.copy2(CSV_FILE, os.path.join(BACKUP_DIR, name))
        return name

    def send_json(self, payload, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        elif path == "/api/data":
            self.send_json(self.read_csv())
        elif path == "/api/next-id":
            self.send_json({"next_id": next_ic(self.read_csv()), "first_seen": today_iso()})
        elif path in {"/api/export/csv", "/api/export/tsv", "/api/export/json"}:
            self.export(path.rsplit("/", 1)[-1])
        else:
            self.send_error(404, "Not Found")

    def export(self, kind):
        rows = self.read_csv()
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if kind == "csv":
            if not os.path.exists(CSV_FILE):
                self.send_error(404, "CSV file not found")
                return
            self.send_response(200)
            self.send_header("Content-Disposition", f'attachment; filename="idea_census_export_{stamp}.csv"')
            self.send_header("Content-type", "text/csv; charset=utf-8")
            self.end_headers()
            with open(CSV_FILE, "rb") as f:
                self.wfile.write(f.read())
        elif kind == "tsv":
            self.send_response(200)
            self.send_header("Content-Disposition", f'attachment; filename="idea_census_export_{stamp}.tsv"')
            self.send_header("Content-type", "text/tab-separated-values; charset=utf-8")
            self.end_headers()
            out = io.StringIO()
            if rows:
                fieldnames = []
                for row in rows:
                    for key in row:
                        if key not in fieldnames:
                            fieldnames.append(key)
                writer = csv.DictWriter(out, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)
            self.wfile.write(out.getvalue().encode("utf-8"))
        else:
            self.send_response(200)
            self.send_header("Content-Disposition", f'attachment; filename="idea_census_export_{stamp}.json"')
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(rows, indent=2).encode("utf-8"))

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            if path == "/api/save":
                self.save_record(payload)
            elif path == "/api/upload":
                self.upload(payload)
            else:
                self.send_error(404, "Not Found")
        except Exception as exc:
            self.send_json({"error": str(exc)}, 500)

    def save_record(self, updates):
        rows = self.read_csv()
        ic_number = str(updates.get("IC Number") or "").strip() or next_ic(rows)
        updates["IC Number"] = ic_number
        existing = next((r for r in rows if r.get("IC Number") == ic_number), None)
        if not updates.get("First Seen"):
            updates["First Seen"] = (existing or {}).get("First Seen") or today_iso()
        self.backup_csv()
        if existing:
            existing.update({k: v for k, v in updates.items() if k != "IC Number"})
            saved = dict(existing)
        else:
            saved = dict(updates)
            rows.append(saved)
        self.write_csv(rows)
        self.send_json({"status": "success", "record": saved})

    def upload(self, payload):
        content = payload.get("fileContent", "")
        mode = payload.get("mode", "replace")
        if not content:
            self.send_json({"error": "File content is empty."}, 400)
            return
        first_line = content.split("\n", 1)[0]
        delimiter = "\t" if "\t" in first_line and first_line.count("\t") >= first_line.count(",") else ","
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        incoming = list(reader)
        if not incoming:
            self.send_json({"error": "No data rows found in file."}, 400)
            return
        id_col = next((c for c in (reader.fieldnames or []) if c and c.lower() in {"ic number", "ic", "id"}), None)
        rows = self.read_csv()
        next_number = ic_int(next_ic(rows))
        processed = []
        for row in incoming:
            raw_id = str(row.get(id_col, "") if id_col else "").strip()
            row["IC Number"] = format_ic(raw_id) if raw_id.isdigit() else (raw_id or format_ic(next_number))
            if not raw_id:
                next_number += 1
            if id_col and id_col != "IC Number" and id_col in row:
                del row[id_col]
            if not row.get("First Seen"):
                row["First Seen"] = today_iso()
            processed.append(row)
        backup_file = self.backup_csv("_pre_upload")
        updated = added = 0
        if mode == "replace":
            rows = processed
            added = len(processed)
        else:
            by_id = {r["IC Number"]: r for r in rows if r.get("IC Number")}
            for row in processed:
                if row["IC Number"] in by_id:
                    by_id[row["IC Number"]].update(row)
                    updated += 1
                else:
                    by_id[row["IC Number"]] = row
                    added += 1
            rows = list(by_id.values())
        self.write_csv(rows)
        self.send_json({"success": True, "summary": {"imported": len(processed), "updated": updated, "added": added, "skipped": 0, "backup_file": backup_file}})


def run():
    server = HTTPServer(("0.0.0.0", PORT), RequestHandler)
    print("========================================")
    print("Idea Census Registry Web App")
    print(f"Running at: http://0.0.0.0:{PORT}")
    print(f"Using CSV file: {CSV_FILE}")
    print(f"Backups directory: {BACKUP_DIR}/")
    print("Press Ctrl+C to stop.")
    print("========================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("Server stopped.")


if __name__ == "__main__":
    run()
