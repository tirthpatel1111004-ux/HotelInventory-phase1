"""Hotel Inventory Management System: Python standard-library web server."""
import csv
import hashlib
import hmac
import html
import io
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('HOTEL_DB', os.path.join(BASE, 'hotel_inventory.db'))
SESSIONS = {}


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200000)
    return salt + '$' + digest.hex()


def check_password(password, stored):
    try:
        salt, digest = stored.split('$', 1)
        return hmac.compare_digest(password_hash(password, salt).split('$', 1)[1], digest)
    except (ValueError, TypeError):
        return False


def initialize():
    with db() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                employee_id TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('manager','staff')),
                active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(id),
                quantity INTEGER NOT NULL CHECK(quantity >= 0),
                minimum_quantity INTEGER NOT NULL CHECK(minimum_quantity >= 0));
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT, occurred_at TEXT NOT NULL,
                employee_id TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
        ''')
        if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            c.execute('INSERT INTO users VALUES (?,?,?,1)', ('Tirth Patel', password_hash('Tirth@104'), 'manager'))
            c.execute('INSERT INTO users VALUES (?,?,?,1)', ('S101', password_hash('StaffDemo2026!'), 'staff'))
        if not c.execute('SELECT 1 FROM categories LIMIT 1').fetchone():
            c.executemany('INSERT INTO categories(name) VALUES (?)',
                          [(x,) for x in ('Guest Supplies', 'Food Service', 'Housekeeping', 'Office')])
        if not c.execute('SELECT 1 FROM inventory LIMIT 1').fetchone():
            rows = [('Bath Towels',1,82,30), ('Coffee Cups',2,18,25),
                    ('Shampoo',1,41,20), ('Printer Paper',4,9,15),
                    ('Cleaning Spray',3,26,15)]
            c.executemany('INSERT INTO inventory(name,category_id,quantity,minimum_quantity) VALUES (?,?,?,?)', rows)


def esc(s):
    return html.escape(str(s), quote=True)


def record(c, employee, action, detail):
    c.execute('INSERT INTO activity(occurred_at,employee_id,action,detail) VALUES (?,?,?,?)',
              (datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), employee, action, detail))

CSS = '''
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#213047;background:#f3f6fa}
*{box-sizing:border-box}body{margin:0}a{color:#13667d;text-decoration:none}a:hover{text-decoration:underline}
header{background:#102d41;color:#fff;padding:19px 30px;display:flex;align-items:center;justify-content:space-between;gap:16px}
header strong{font-size:21px}header small{color:#c4d9e4}header a{color:white}
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);min-height:calc(100vh - 73px)}nav{background:#173a50;padding:20px 12px}nav a{display:block;color:#e7f3fb;padding:12px 15px;border-radius:8px;margin-bottom:4px}nav a:hover{background:#28556a;text-decoration:none}
main{max-width:1250px;width:100%;padding:30px 36px;margin:0 auto}h1{margin-top:0;color:#12374b;font-size:28px}h2{font-size:20px}.cards{display:flex;gap:15px;flex-wrap:wrap;margin:20px 0}.card,.panel{background:white;border:1px solid #dae3ea;border-radius:12px;padding:19px;box-shadow:0 2px 9px #1a334009}.card{min-width:170px;flex:1}.card .metric{font-weight:750;font-size:31px;color:#14718c}.panel{margin:18px 0;overflow-x:auto}
table{border-collapse:collapse;width:100%;background:white}th,td{padding:12px 13px;text-align:left;border-bottom:1px solid #e3eaf0}th{background:#eef4f6;color:#315368}tr:last-child td{border-bottom:none}
input,select,button{font:inherit;border-radius:7px;padding:10px;border:1px solid #aabcca}button{background:#116d87;color:white;border:0;cursor:pointer;font-weight:650}button:hover{background:#0c4f64}form.inline{display:flex;gap:9px;align-items:center;flex-wrap:wrap}label{display:block;margin-bottom:6px;font-weight:600}form.stack{max-width:500px;display:grid;gap:13px}form.stack input,form.stack select{width:100%}.muted{color:#667788}.low{color:#a13b28;font-weight:700}.ok{color:#137c56;font-weight:700}.alert{background:#fff0e8;border:1px solid #f6bfaa;padding:12px;border-radius:8px;margin-bottom:15px}.success{background:#e7f7ef;border:1px solid #a5d9c1;padding:12px;border-radius:8px;margin-bottom:15px}.login{max-width:430px;margin:8vh auto}.login .panel{padding:30px}.badge{background:#d9eaf2;border-radius:30px;padding:6px 12px;font-size:13px}
@media(max-width:720px){.layout{grid-template-columns:1fr}nav{display:flex;flex-wrap:wrap;gap:4px;padding:10px}nav a{margin:0;padding:8px}main{padding:18px}header{padding:16px}}
'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('%s - %s' % (self.address_string(), fmt % args))

    def respond(self, body, status=200, content_type='text/html; charset=utf-8', headers=None):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; form-action 'self'")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location, cookie=None):
        headers = {'Location': location}
        if cookie:
            headers['Set-Cookie'] = cookie
        self.respond('', 303, headers=headers)

    def user(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get('Cookie', ''))
            token = jar['hotel_session'].value if 'hotel_session' in jar else ''
        except cookies.CookieError:
            return None
        session = SESSIONS.get(token)
        if not session:
            return None
        with db() as c:
            user = c.execute('SELECT employee_id,role,active FROM users WHERE employee_id=?', (session['id'],)).fetchone()
        if user is None or not user['active']:
            SESSIONS.pop(token, None)
            return None
        return {'id': user['employee_id'], 'role': user['role'], 'csrf': session['csrf'], 'token': token}

    def page(self, title, content, user=None, notice=''):
        if user:
            links = [('/', 'Dashboard'), ('/inventory', 'View / Search Inventory'), ('/low-stock', 'Low Stock'), ('/update', 'Update Quantity')]
            if user['role'] == 'manager':
                links += [('/item', 'Add Item'), ('/items-edit', 'Edit Items'), ('/reports', 'Reports'), ('/employees', 'Employee Accounts'), ('/activity', 'Activity History')]
            navigation = '<nav>' + ''.join(f'<a href="{link}">{esc(label)}</a>' for link,label in links) + '</nav>'
            subtitle = f'{esc(user["id"])} · {esc(user["role"].title())}'
            top = f'<header><strong>HOTEL INVENTORY <small>Management System</small></strong><span>{subtitle} &nbsp; <a href="/logout">Logout</a></span></header>'
            body = f'{top}<div class="layout">{navigation}<main><h1>{esc(title)}</h1>{notice}{content}</main></div>'
        else:
            body = f'<header><strong>HOTEL INVENTORY</strong><small>Management System</small></header><div class="login"><div class="panel"><h1>{esc(title)}</h1>{notice}{content}</div></div>'
        return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+'</title><style>'+CSS+'</style></head><body>'+body+'</body></html>'

    def form_csrf(self, u):
        return f'<input type="hidden" name="csrf" value="{esc(u["csrf"])}">'

    def read_form(self):
        length = int(self.headers.get('Content-Length', '0'))
        if length > 20000:
            raise ValueError('Form too large')
        data = self.rfile.read(length).decode('utf-8')
        return {k: v[0] for k,v in parse_qs(data, keep_blank_values=True).items()}

    def inventory_rows(self, term='', low=False):
        q = '''SELECT i.*,c.name AS category FROM inventory i
               JOIN categories c ON c.id=i.category_id WHERE (i.name LIKE ? OR c.name LIKE ?)'''
        if low:
            q += ' AND i.quantity < i.minimum_quantity'
        q += ' ORDER BY i.name COLLATE NOCASE'
        with db() as c:
            return c.execute(q, ('%'+term+'%', '%'+term+'%')).fetchall()

    def inventory_table(self, rows, u, action=False):
        cells = ''
        for x in rows:
            status = '<span class="low">LOW</span>' if x['quantity'] < x['minimum_quantity'] else '<span class="ok">OK</span>'
            more = f'<td><a href="/update?id={x["id"]}">Update</a></td>' if action else ''
            cells += f'<tr><td>{esc(x["name"])}</td><td>{esc(x["category"])}</td><td>{x["quantity"]}</td><td>{x["minimum_quantity"]}</td><td>{status}</td>{more}</tr>'
        return '<div class="panel"><table><thead><tr><th>Item</th><th>Category</th><th>Quantity</th><th>Minimum</th><th>Status</th>'+('<th>Action</th>' if action else '')+'</tr></thead><tbody>'+ (cells or '<tr><td colspan="6">No matching items.</td></tr>') + '</tbody></table></div>'

    def do_GET(self):
        split = urlsplit(self.path)
        path, params = split.path, parse_qs(split.query)
        if path == '/health':
            return self.respond('OK', content_type='text/plain')
        if path == '/logout':
            u = self.user()
            if u: SESSIONS.pop(u['token'], None)
            return self.redirect('/login', 'hotel_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0')
        u = self.user()
        if not u:
            if path != '/login': return self.redirect('/login')
            form = '<form class="stack" method="post" action="/login"><div><label>Employee ID</label><input name="id" required autofocus></div><div><label>Password</label><input type="password" name="password" required></div><button>Log In</button></form><p class="muted">Use the demo accounts listed in README.md for local testing.</p>'
            return self.respond(self.page('Employee Login', form))
        if path == '/':
            with db() as c:
                total = c.execute('SELECT COUNT(*) FROM inventory').fetchone()[0]
                low = c.execute('SELECT COUNT(*) FROM inventory WHERE quantity < minimum_quantity').fetchone()[0]
                categories = c.execute('SELECT COUNT(*) FROM categories').fetchone()[0]
                activity = c.execute('SELECT * FROM activity ORDER BY id DESC LIMIT 5').fetchall()
            cards = ''.join(f'<div class="card"><div class="metric">{number}</div><b>{esc(label)}</b></div>' for number,label in [(total,'Inventory Items'),(low,'Low Stock'),(categories,'Categories')])
            logs = ''.join(f'<tr><td>{esc(a["occurred_at"])}</td><td>{esc(a["employee_id"])}</td><td>{esc(a["action"])}</td></tr>' for a in activity) or '<tr><td colspan="3">No activity yet.</td></tr>'
            return self.respond(self.page('Dashboard', '<div class="cards">'+cards+'</div><div class="panel"><h2>Recent Inventory Activity</h2><table><tr><th>Date</th><th>Employee</th><th>Action</th></tr>'+logs+'</table></div>', u))
        if path in ('/inventory', '/low-stock'):
            term = params.get('q',[''])[0].strip()[:80]
            form = '<form class="inline" method="get" action="/inventory"><input name="q" placeholder="Search by item or category" value="'+esc(term)+'"><button>Search</button></form>'
            return self.respond(self.page('Low Stock Items' if path == '/low-stock' else 'Inventory', (form if path == '/inventory' else '') + self.inventory_table(self.inventory_rows(term, path=='/low-stock'),u,True), u))
        if path == '/update':
            rows = self.inventory_rows()
            options = ''.join(f'<option value="{x["id"]}" '+('selected' if str(x['id']) == params.get('id',[''])[0] else '')+'>'+esc(x['name'])+' (current: '+str(x['quantity'])+')</option>' for x in rows)
            form = f'<div class="panel"><form class="stack" method="post" action="/update">{self.form_csrf(u)}<div><label>Inventory Item</label><select name="id">{options}</select></div><div><label>New Quantity</label><input name="quantity" type="number" min="0" required></div><button>Save Quantity</button></form></div>'
            return self.respond(self.page('Update Quantity',form,u))
        if u['role'] != 'manager':
            return self.respond(self.page('Access Denied','<p>Manager access is required.</p>',u),403)
        if path in ('/item','/items-edit'):
            edit_id = params.get('id',[''])[0]
            with db() as c:
                categories = c.execute('SELECT * FROM categories ORDER BY name').fetchall()
                current = c.execute('SELECT * FROM inventory WHERE id=?',(edit_id,)).fetchone() if edit_id else None
            options = ''.join(f'<option value="{x["id"]}" '+('selected' if current and x['id']==current['category_id'] else '')+'>'+esc(x['name'])+'</option>' for x in categories)
            form = f'<div class="panel"><form class="stack" method="post" action="/item">{self.form_csrf(u)}<input type="hidden" name="id" value="{esc(edit_id if current else "")}"><div><label>Item Name</label><input name="name" required maxlength="100" value="{esc(current["name"] if current else "")}"></div><div><label>Category</label><select name="category">{options}</select></div><div><label>Quantity</label><input type="number" min="0" required name="quantity" value="{current["quantity"] if current else 0}"></div><div><label>Minimum Quantity</label><input type="number" min="0" required name="minimum" value="{current["minimum_quantity"] if current else 0}"></div><button>{"Save Changes" if current else "Add Item"}</button></form></div>'
            if path == '/items-edit' and not current:
                rows = self.inventory_rows()
                links = ''.join(f'<tr><td>{esc(x["name"])}</td><td>{esc(x["category"])}</td><td><a href="/items-edit?id={x["id"]}">Edit</a></td></tr>' for x in rows)
                return self.respond(self.page('Edit Inventory Items','<div class="panel"><table><tr><th>Item</th><th>Category</th><th>Edit</th></tr>'+links+'</table></div>',u))
            return self.respond(self.page('Edit Item' if current else 'Add Inventory Item',form,u))
        if path == '/reports':
            with db() as c:
                rows = c.execute('''SELECT c.name, COUNT(i.id) AS count, COALESCE(SUM(i.quantity),0) AS units,
                    COALESCE(SUM(CASE WHEN i.quantity < i.minimum_quantity THEN 1 ELSE 0 END),0) AS low
                    FROM categories c LEFT JOIN inventory i ON i.category_id=c.id GROUP BY c.id ORDER BY c.name''').fetchall()
            trs = ''.join(f'<tr><td>{esc(x["name"])}</td><td>{x["count"]}</td><td>{x["units"]}</td><td>{x["low"]}</td></tr>' for x in rows)
            return self.respond(self.page('Inventory Reports','<p><a href="/reports.csv">Download inventory CSV</a></p><div class="panel"><table><tr><th>Category</th><th>Items</th><th>Total Units</th><th>Low-Stock Items</th></tr>'+trs+'</table></div>',u))
        if path in ('/reports.csv','/activity.csv'):
            with db() as c:
                rows = c.execute('''SELECT i.id,i.name,c.name AS category,i.quantity,i.minimum_quantity FROM inventory i JOIN categories c ON c.id=i.category_id ORDER BY i.name''' if path=='/reports.csv' else 'SELECT occurred_at,employee_id,action,detail FROM activity ORDER BY id DESC').fetchall()
            out=io.StringIO(); writer=csv.writer(out)
            writer.writerow(['Item ID','Item','Category','Quantity','Minimum'] if path=='/reports.csv' else ['Date','Employee','Action','Detail'])
            for row in rows: writer.writerow(tuple(row))
            return self.respond(out.getvalue(),content_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="'+('inventory' if path=='/reports.csv' else 'activity')+'.csv"'})
        if path == '/activity':
            with db() as c:
                rows=c.execute('SELECT * FROM activity ORDER BY id DESC LIMIT 150').fetchall()
            trs=''.join(f'<tr><td>{esc(x["occurred_at"])}</td><td>{esc(x["employee_id"])}</td><td>{esc(x["action"])}</td><td>{esc(x["detail"])}</td></tr>' for x in rows)
            return self.respond(self.page('Activity History','<p><a href="/activity.csv">Download activity CSV</a></p><div class="panel"><table><tr><th>Date</th><th>Employee</th><th>Action</th><th>Details</th></tr>'+trs+'</table></div>',u))
        if path == '/employees':
            with db() as c:
                users=c.execute('SELECT employee_id,role,active FROM users ORDER BY employee_id').fetchall()
            trs=''.join(f'<tr><td>{esc(x["employee_id"])}</td><td>{esc(x["role"])}</td><td>{"Active" if x["active"] else "Disabled"}</td></tr>' for x in users)
            form=f'<div class="panel"><h2>Create Employee Account</h2><form class="stack" method="post" action="/employees">{self.form_csrf(u)}<div><label>Employee ID</label><input name="id" required maxlength="20"></div><div><label>Temporary Password (8+ characters)</label><input name="password" type="password" minlength="8" required></div><div><label>Role</label><select name="role"><option value="staff">Staff</option><option value="manager">Manager</option></select></div><button>Create Account</button></form></div>'
            return self.respond(self.page('Employee Accounts',form+'<div class="panel"><table><tr><th>Employee ID</th><th>Role</th><th>Status</th></tr>'+trs+'</table></div>',u))
        return self.respond(self.page('Not Found','<p>Page not found.</p>',u),404)

    def do_POST(self):
        path=urlsplit(self.path).path
        try:
            form=self.read_form()
            if path == '/login':
                ident=form.get('id','').strip()
                with db() as c:
                    row=c.execute('SELECT * FROM users WHERE employee_id=? AND active=1',(ident,)).fetchone()
                if row is None or not check_password(form.get('password',''),row['password_hash']):
                    return self.respond(self.page('Employee Login','<p class="alert">Incorrect Employee ID or password.</p><a href="/login">Try again</a>'),401)
                token=secrets.token_urlsafe(32)
                SESSIONS[token]={'id': ident,'csrf':secrets.token_urlsafe(24)}
                return self.redirect('/','hotel_session='+token+'; HttpOnly; SameSite=Lax; Path=/')
            u=self.user()
            if not u: return self.redirect('/login')
            if not hmac.compare_digest(form.get('csrf',''),u['csrf']):
                return self.respond(self.page('Invalid Request','<p>Invalid form security token.</p>',u),403)
            if path == '/update':
                iid=int(form.get('id','')); qty=int(form.get('quantity',''))
                if qty < 0: raise ValueError('Quantity must not be negative')
                with db() as c:
                    x=c.execute('SELECT name,quantity FROM inventory WHERE id=?',(iid,)).fetchone()
                    if not x: raise ValueError('Item not found')
                    c.execute('UPDATE inventory SET quantity=? WHERE id=?',(qty,iid))
                    record(c,u['id'],'Quantity Updated',f'{x["name"]}: {x["quantity"]} to {qty}')
                return self.redirect('/inventory')
            if u['role'] != 'manager':
                return self.respond(self.page('Access Denied','<p>Manager access is required.</p>',u),403)
            if path == '/item':
                name=form.get('name','').strip()[:100]
                category=int(form.get('category','')); qty=int(form.get('quantity','')); minimum=int(form.get('minimum',''))
                if not name or min(qty,minimum) < 0: raise ValueError('Please enter valid item information')
                with db() as c:
                    if not c.execute('SELECT id FROM categories WHERE id=?',(category,)).fetchone(): raise ValueError('Category does not exist')
                    iid=form.get('id','').strip()
                    if iid:
                        result=c.execute('UPDATE inventory SET name=?,category_id=?,quantity=?,minimum_quantity=? WHERE id=?',(name,category,qty,minimum,int(iid)))
                        if result.rowcount==0: raise ValueError('Item not found')
                        record(c,u['id'],'Item Edited',name)
                    else:
                        c.execute('INSERT INTO inventory(name,category_id,quantity,minimum_quantity) VALUES (?,?,?,?)',(name,category,qty,minimum))
                        record(c,u['id'],'Item Added',name)
                return self.redirect('/inventory')
            if path == '/employees':
                ident=form.get('id','').strip(); password=form.get('password',''); role=form.get('role','')
                if not ident or len(ident)>20 or len(password)<8 or role not in ('staff','manager'):
                    raise ValueError('Provide valid Employee ID, password, and role')
                with db() as c:
                    c.execute('INSERT INTO users VALUES (?,?,?,1)',(ident,password_hash(password),role))
                    record(c,u['id'],'Employee Created',ident+' ('+role+')')
                return self.redirect('/employees')
            return self.respond(self.page('Not Found','<p>Unknown action.</p>',u),404)
        except (ValueError,sqlite3.IntegrityError) as e:
            u=self.user()
            return self.respond(self.page('Cannot Save','<p class="alert">'+esc(str(e))+'</p><p><a href="/">Return to dashboard</a></p>',u),400)


def serve(host='127.0.0.1',port=8000):
    initialize()
    httpd=ThreadingHTTPServer((host,port),Handler)
    print(f'Hotel Inventory running at http://{host}:{port}')
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: httpd.server_close()

if __name__=='__main__':
    serve(os.environ.get('HOTEL_HOST','127.0.0.1'),int(os.environ.get('HOTEL_PORT','8000')))
