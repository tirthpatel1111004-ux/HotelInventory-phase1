import sqlite3
import hashlib
import hmac
import secrets
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DB = ROOT / 'hotel_inventory.db'

def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200000).hex()
    return salt + ':' + value

def verify(password, hashed):
    try:
        salt, unused = hashed.split(':', 1)
        return hmac.compare_digest(hash_password(password, salt), hashed)
    except (AttributeError, ValueError):
        return False

def initialize():
    with connect() as db:
        db.executescript((ROOT/'schema.sql').read_text())
        if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            db.executemany('INSERT INTO users(employee_id,password_hash,role) VALUES(?,?,?)',[
                ('Tirth Patel', hash_password('Tirth@1104'), 'manager'),
                ('Staff', hash_password('Staff2026'), 'staff')])
        if not db.execute('SELECT 1 FROM categories LIMIT 1').fetchone():
            db.executemany('INSERT INTO categories(name) VALUES(?)',[(x,) for x in ('Guest Supply','Bistro','Office')])
        if not db.execute('SELECT 1 FROM inventory LIMIT 1').fetchone():
            db.executemany('INSERT INTO inventory(name,category_id,quantity,minimum_qty) VALUES(?,?,?,?)',[
                ('Bath Towels',1,82,30),('Coffee Cups',2,18,25),('Shampoo',1,41,20),('Printer Paper',3,9,15)])
