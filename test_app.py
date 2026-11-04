import http.client
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

import app


class HotelInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(cls.temp.name, 'test.db')
        app.initialize()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def request(self, method, path, data=None, cookie=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port)
        headers = {}
        if cookie: headers['Cookie'] = cookie
        if data is not None:
            data = urlencode(data)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        conn.request(method, path, data, headers)
        response = conn.getresponse()
        result = (response.status, dict(response.getheaders()), response.read().decode('utf-8'))
        conn.close()
        return result

    def login(self, ident='M100', password='HotelDemo2026!'):
        status, headers, _ = self.request('POST','/login', {'id':ident,'password':password})
        self.assertEqual(status,303)
        token=headers['Set-Cookie'].split(';')[0]
        return token, app.SESSIONS[token.split('=',1)[1]]['csrf']

    def test_health(self):
        self.assertEqual(self.request('GET','/health')[2],'OK')

    def test_login_failure(self):
        self.assertEqual(self.request('POST','/login',{'id':'M100','password':'wrong'})[0],401)

    def test_login_and_search(self):
        cookie,_=self.login()
        status,_,body=self.request('GET','/inventory?q=Coffee',cookie=cookie)
        self.assertEqual(status,200)
        self.assertIn('Coffee Cups',body)
        self.assertNotIn('Printer Paper',body)

    def test_staff_cannot_access_manager(self):
        cookie,csrf=self.login('S101','StaffDemo2026!')
        self.assertEqual(self.request('GET','/employees',cookie=cookie)[0],403)
        self.assertEqual(self.request('POST','/item',{'csrf':csrf,'name':'Forbidden','category':1,'quantity':3,'minimum':1},cookie)[0],403)

    def test_add_edit_update_low_stock_and_activity(self):
        cookie,csrf=self.login()
        data={'csrf':csrf,'name':'Test Soap','category':1,'quantity':1,'minimum':5}
        self.assertEqual(self.request('POST','/item',data,cookie)[0],303)
        with app.db() as c:
            iid=c.execute("SELECT id FROM inventory WHERE name='Test Soap'").fetchone()[0]
        self.assertIn('Test Soap',self.request('GET','/low-stock',cookie=cookie)[2])
        self.assertEqual(self.request('POST','/update',{'csrf':csrf,'id':iid,'quantity':12},cookie)[0],303)
        self.assertNotIn('Test Soap',self.request('GET','/low-stock',cookie=cookie)[2])
        self.assertEqual(self.request('POST','/item',{'csrf':csrf,'id':iid,'name':'Test Hand Soap','category':1,'quantity':12,'minimum':5},cookie)[0],303)
        self.assertIn('Test Hand Soap',self.request('GET','/inventory',cookie=cookie)[2])
        self.assertIn('Quantity Updated',self.request('GET','/activity',cookie=cookie)[2])

    def test_employee_creation_reports_and_csv(self):
        cookie,csrf=self.login()
        self.assertEqual(self.request('POST','/employees',{'csrf':csrf,'id':'TEST-9','password':'ExamplePass123','role':'staff'},cookie)[0],303)
        self.assertEqual(self.login('TEST-9','ExamplePass123')[0].startswith('hotel_session='),True)
        self.assertIn('Total Units',self.request('GET','/reports',cookie=cookie)[2])
        self.assertIn('Item ID,Item,Category',self.request('GET','/reports.csv',cookie=cookie)[2])

    def test_csrf_and_negative_quantity_blocked(self):
        cookie,csrf=self.login()
        self.assertEqual(self.request('POST','/update',{'id':1,'quantity':40},cookie)[0],403)
        self.assertEqual(self.request('POST','/update',{'csrf':csrf,'id':1,'quantity':-1},cookie)[0],400)


if __name__ == '__main__':
    unittest.main()
