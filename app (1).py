"""App Deploy Platform"""
import os,json,time,shutil,subprocess
from pathlib import Path
from flask import Flask,request,jsonify,Response,send_from_directory

B = Path('/tmp/appdp')
B.mkdir(exist_ok=True)
P = B / 'projects'
P.mkdir(exist_ok=True)
D = B / 'db.json'
APPS = {}

def load_db():
    if D.exists():
        return json.loads(D.read_text())
    return {'projects': {}}

def save_db(db):
    D.write_text(json.dumps(db, indent=2))

def start_app(pid, proj):
    stop_app(pid)
    if proj.get('type') == 'static':
        APPS[pid] = {'status': 'running'}
        return True
    if proj.get('type') == 'python':
        app_dir = P / pid
        main_file = app_dir / proj.get('main', 'app.py')
        if not main_file.exists():
            return False
        port = 5100 + (hash(str(time.time())) % 200)
        env = os.environ.copy()
        env['PORT'] = str(port)
        try:
            proc = subprocess.Popen(['python3', str(main_file)], cwd=str(app_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)
            if proc.poll() is not None:
                return False
            APPS[pid] = {'proc': proc, 'port': port, 'status': 'running'}
            return True
        except:
            return False
    return False

def stop_app(pid):
    if pid in APPS:
        if 'proc' in APPS[pid] and APPS[pid]['proc']:
            APPS[pid]['proc'].terminate()
        del APPS[pid]

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/')
def home():
    db = load_db()
    cards = ''
    for pid, proj in db['projects'].items():
        s = proj.get('status', '-')
        nm = proj.get('name', pid)
        tp = proj.get('type', 'static').upper()
        cards += '<div class=card><b>' + nm + '</b> [' + s + '] ' + tp + ' <a href=/edit/' + pid + '>Edit</a> | '
        cards += '<a href=/s/' + pid + '/>Visit</a> | '
        cards += '<button onclick=tg("' + pid + '")>Toggle</button> | '
        cards += '<button onclick=dl("' + pid + '")>Del</button></div>'
    if not db['projects']:
        cards = '<p>No apps yet. Create one!</p>'
    h = '<!DOCTYPE html><html><head><meta charset=UTF-8><meta name=viewport content="width=device-width,initial-scale=1.0"><title>App Deploy</title>'
    h += '<style>body{font-family:system-ui;background:#fafafa;color:#18181b;margin:0;padding:20px}a{text-decoration:none}'
    h += '.card{background:#fff;border:1px solid #e4e4e7;border-radius:1rem;padding:16px;margin:8px 0;transition:.2s}'
    h += '.card:hover{transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,0,0,.08)}</style>'
    h += '</head><body><div style=max-width:900px;margin:0 auto><h1>App Deploy Platform</h1>'
    h += '<p style=color:#71717a>Python and Static apps with built-in editor</p>'
    h += '<button onclick="document.getElementById(\'mdl\').style.display=\'flex\'" style=background:#18181b;color:#fff;border:none;padding:10px 24px;border-radius:50px;cursor:pointer;font-size:14px;margin-bottom:20px>+ New App</button>'
    h += '<div>' + cards + '</div></div>'
    h += '<div id=mdl style=display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:50;justify-content:center;align-items:center>'
    h += '<div style=background:#fff;border-radius:1rem;padding:20px;width:340px>'
    h += '<h3>New App</h3><form onsubmit=cr(event)>'
    h += '<input name=name placeholder="App name" required style=width:100%;padding:10px;border:1px solid #e4e4e7;border-radius:50px;margin:8px 0;font-size:14px>'
    h += '<select name=type style=width:100%;padding:10px;border:1px solid #e4e4e7;border-radius:50px;margin:8px 0;font-size:14px><option value=static>Static HTML</option><option value=python>Python Flask</option></select>'
    h += '<button style=background:#18181b;color:#fff;border:none;padding:10px;width:100%;border-radius:50px;cursor:pointer>Create</button>'
    h += '<button type=button onclick="document.getElementById(\'mdl\').style.display=\'none\'" style=border:1px solid #e4e4e7;background:none;padding:10px;width:100%;border-radius:50px;cursor:pointer;margin-top:8px>Cancel</button>'
    h += '</form></div></div>'
    h += '<script>async function cr(e){e.preventDefault();let f=new FormData(e.target);let d={name:f.get("name"),type:f.get("type")};'
    h += 'await fetch("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});location.reload()}'
    h += 'async function tg(id){await fetch("/api/projects/"+id+"/toggle",{method:"POST"});location.reload()}'
    h += 'async function dl(id){if(confirm("Delete?")){await fetch("/api/projects/"+id,{method:"DELETE"});location.reload()}}</script>'
    h += '</body></html>'
    return Response(h, mimetype='text/html')

@app.route('/edit/<pid>')
def edit(pid):
    db = load_db()
    proj = db['projects'].get(pid)
    if not proj:
        return 'Not found', 404
    main_file = proj.get('main', 'app.py' if proj.get('type') == 'python' else 'index.html')
    file_path = P / pid / main_file
    content = file_path.read_text() if file_path.exists() else ''
    h = '<!DOCTYPE html><html><head><meta charset=UTF-8><title>' + pid + ' - Editor</title>'
    h += '<style>body{margin:0;font-family:system-ui;background:#fafafa}'
    h += 'textarea{outline:none;font-family:monospace;font-size:14px;border:none;resize:none;width:100%;height:calc(100vh-44px);padding:16px;background:#fafafa}</style>'
    h += '</head><body>'
    h += '<div style=display:flex;align-items:center;gap:8px;padding:8px 16px;border-bottom:1px solid #e4e4e7;background:#fff>'
    h += '<a href=/ style=color:#71717a;text-decoration:none>Back</a>'
    h += '<b>' + pid + '</b>'
    h += '<span style=font-size:11px;background:#f4f4f5;padding:2px 8px;border-radius:50px>' + proj.get('type') + '</span>'
    h += '<div style=flex:1></div>'
    h += '<button onclick=save() style=background:#16a34a;color:#fff;border:none;padding:6px 14px;border-radius:50px;cursor:pointer;font-size:12px>Save</button>'
    h += '<button onclick=deploy() style=background:#18181b;color:#fff;border:none;padding:6px 14px;border-radius:50px;cursor:pointer;font-size:12px>Deploy</button>'
    h += '</div>'
    h += '<textarea id=editor>' + content + '</textarea>'
    h += '<div id=output style=background:#18181b;color:#4ade80;padding:4px 16px;font-size:11px;display:none></div>'
    h += '<script>'
    h += 'async function save(){let c=document.getElementById("editor").value;'
    h += 'await fetch("/api/projects/' + pid + '/files/' + main_file + '",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({content:c})});msg("Saved!")}'
    h += 'async function deploy(){msg("Deploying...");let r=await fetch("/api/projects/' + pid + '/deploy",{method:"POST"});let d=await r.json();msg(d.ok?"Deployed!":"Failed")}'
    h += 'function msg(t){let o=document.getElementById("output");o.style.display="block";o.textContent=t}'
    h += '</script></body></html>'
    return Response(h, mimetype='text/html')

@app.route('/s/<pid>/', defaults={'subpath': ''})
@app.route('/s/<pid>/<path:subpath>')
def serve(pid, subpath):
    db = load_db()
    proj = db['projects'].get(pid)
    if not proj:
        return 'Not found', 404
    app_dir = P / pid
    if proj.get('type') == 'static':
        if subpath:
            return send_from_directory(str(app_dir), subpath) if (app_dir / subpath).is_file() else ('Not Found', 404)
        for mf in ['index.html', 'i.html', 'index.htm']:
            if (app_dir / mf).is_file():
                return (app_dir / mf).read_text()
        return '<h1>Welcome</h1>'
    if pid in APPS and APPS[pid].get('status') == 'running':
        import requests
        try:
            return requests.get('http://127.0.0.1:' + str(APPS[pid]['port']) + '/' + subpath, timeout=10).text
        except:
            return '<h1>Starting...</h1>'
    return '<h1>Stopped</h1>'

@app.route('/api/projects')
def api_list():
    return jsonify(load_db()['projects'])

@app.route('/api/projects', methods=['POST'])
def api_create():
    d = request.get_json()
    name = d.get('name', '').strip()
    ptype = d.get('type', 'static')
    if not name:
        return jsonify({'error': 'Name required'}), 400
    pid = ''.join(c for c in name.lower().replace(' ', '-') if c.isalnum() or c == '-')[:30]
    if not pid:
        pid = 'app' + str(abs(hash(name)) % 10000)
    db = load_db()
    if pid in db['projects']:
        pid += str(abs(hash(str(time.time()))) % 1000)
    app_dir = P / pid
    app_dir.mkdir(parents=True, exist_ok=True)
    if ptype == 'static':
        (app_dir / 'index.html').write_text('<!DOCTYPE html><html><head><meta charset=UTF-8><meta name=viewport content="width=device-width,initial-scale=1.0"><title>App</title><style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f8f9fa;text-align:center}h1{font-size:3rem}</style></head><body><div><h1>Hello World!</h1><p>Edit me!</p></div></body></html>')
    elif ptype == 'python':
        (app_dir / 'requirements.txt').write_text('flask>=3.0')
        (app_dir / 'app.py').write_text('from flask import Flask\nimport os\napp=Flask(__name__)\n@app.route("/")\ndef home():\n    return "<h1 style=text-align:center;margin-top:20%>Python App LIVE!</h1>"\nif __name__=="__main__":\n    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))\n')
    db['projects'][pid] = {'name': name, 'type': ptype, 'main': 'app.py' if ptype == 'python' else 'index.html', 'status': '-'}
    save_db(db)
    return jsonify({'ok': True, 'id': pid})

@app.route('/api/projects/<pid>', methods=['DELETE'])
def api_delete(pid):
    db = load_db()
    if pid in db['projects']:
        stop_app(pid)
        app_dir = P / pid
        if app_dir.exists():
            shutil.rmtree(str(app_dir))
        del db['projects'][pid]
        save_db(db)
    return jsonify({'ok': True})

@app.route('/api/projects/<pid>/toggle', methods=['POST'])
def api_toggle(pid):
    db = load_db()
    proj = db['projects'].get(pid)
    if not proj:
        return jsonify({'error': 'Not found'}), 404
    if proj.get('status') == 'running':
        stop_app(pid)
        proj['status'] = '-'
    else:
        ok = start_app(pid, proj)
        proj['status'] = 'running' if ok else 'crashed'
    save_db(db)
    return jsonify({'ok': True, 'status': proj['status']})

@app.route('/api/projects/<pid>/deploy', methods=['POST'])
def api_deploy(pid):
    db = load_db()
    proj = db['projects'].get(pid)
    if not proj:
        return jsonify({'error': 'Not found'}), 404
    ok = start_app(pid, proj)
    proj['status'] = 'running' if ok else 'crashed'
    save_db(db)
    return jsonify({'ok': ok})

@app.route('/api/projects/<pid>/files/<path:filepath>')
def api_get_file(pid, filepath):
    fp = P / pid / filepath
    return jsonify({'content': fp.read_text() if fp.is_file() else ''})

@app.route('/api/projects/<pid>/files/<path:filepath>', methods=['PUT'])
def api_save_file(pid, filepath):
    d = request.get_json()
    fp = P / pid / filepath
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(d.get('content', ''))
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=False)
