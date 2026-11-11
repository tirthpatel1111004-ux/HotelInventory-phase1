import json
import secrets
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import database,services
from router import PAGES

ROOT=Path(__file__).resolve().parent
CLIENT=ROOT/'client'
SESSIONS={}
MIME={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'}
class Handler(BaseHTTPRequestHandler):
    def reply(self,status,obj,cookie=None):
        body=json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(body)
    def user(self):
        try:
            cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
            return SESSIONS.get(cookie['session'].value) if 'session' in cookie else None
        except Exception:return None
    def data(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>10000:raise services.ServiceError('Request too large')
        try:
            obj=json.loads(self.rfile.read(size) or b'{}')
            if not isinstance(obj,dict):raise ValueError
            return obj
        except (ValueError,UnicodeDecodeError):raise services.ServiceError('Invalid JSON')
    def page(self,file):
        file=file.resolve()
        if not file.is_file() or not file.is_relative_to(CLIENT.resolve()):return self.send_error(404)
        content=file.read_bytes();self.send_response(200)
        self.send_header('Content-Type',MIME.get(file.suffix,'application/octet-stream'))
        self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
    def do_GET(self):self.handle_action('GET')
    def do_POST(self):self.handle_action('POST')
    def do_PUT(self):self.handle_action('PUT')
    def handle_action(self,method):
        url=urlsplit(self.path);path=url.path
        try:
            if method=='GET' and path.startswith('/client/'):
                return self.page(CLIENT/path[len('/client/'):])
            if method=='GET' and path in PAGES:return self.page(CLIENT/PAGES[path])
            if method=='POST' and path=='/api/login':
                user=services.login(self.data());token=secrets.token_urlsafe(32);SESSIONS[token]=user
                return self.reply(200,{'user':user},f'session={token}; HttpOnly; SameSite=Strict; Path=/')
            if method=='POST' and path=='/api/logout':
                try:
                    cookies=SimpleCookie();cookies.load(self.headers.get('Cookie',''))
                    if 'session' in cookies:SESSIONS.pop(cookies['session'].value,None)
                except Exception:pass
                return self.reply(200,{'ok':True},'session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/')
            if not path.startswith('/api/'):return self.send_error(404)
            user=self.user()
            if not user:raise services.ServiceError('Login required',401)
            data=self.data() if method in ('POST','PUT') else {}
            if path=='/api/me' and method=='GET':result={'user':user}
            elif path=='/api/inventory' and method=='GET':
                result={'items':services.inventory(parse_qs(url.query).get('search',[''])[0])}
            elif path=='/api/low-stock' and method=='GET':result={'items':services.inventory(low=True)}
            elif path=='/api/categories' and method=='GET':result={'categories':services.categories()}
            elif path=='/api/inventory' and method=='POST':result=services.save_item(data,user)
            elif path.startswith('/api/inventory/') and path.split('/')[-1].isdigit() and method=='PUT':
                result=services.save_item(data,user,int(path.split('/')[-1]))
            elif path.startswith('/api/quantity/') and path.split('/')[-1].isdigit() and method=='PUT':
                result=services.update_quantity(int(path.split('/')[-1]),data)
            elif path=='/api/reports' and method=='GET':result={'report':services.report(user)}
            elif path=='/api/employees' and method=='POST':result=services.create_employee(data,user)
            else:raise services.ServiceError('Unknown endpoint',404)
            return self.reply(200,result)
        except services.ServiceError as e:self.reply(e.status,{'error':str(e)})
        except (ValueError,TypeError):self.reply(400,{'error':'Invalid input'})
        except Exception:
            self.reply(500,{'error':'Server error'})

if __name__=='__main__':
    database.initialize()
    server=ThreadingHTTPServer(('127.0.0.1',8000),Handler)
    print('Hotel Inventory System: http://127.0.0.1:8000/login',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
