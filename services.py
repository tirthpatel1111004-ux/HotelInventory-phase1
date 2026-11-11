from database import connect, hash_password, verify

class ServiceError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status=status

def manager(user):
    if user['role']!='manager':
        raise ServiceError('Manager access required',403)

def required(data, key):
    value=str(data.get(key,'')).strip()
    if not value or len(value)>120:raise ServiceError(key+' is required (maximum 120 characters)')
    return value

def whole(value, name):
    try:
        if isinstance(value,bool):raise ValueError
        number=int(value)
        if number<0:raise ValueError
        return number
    except (TypeError, ValueError):raise ServiceError(name+' must be a nonnegative whole number')

def login(data):
    employee_id=required(data,'employee_id')
    with connect() as db:
        row=db.execute('SELECT * FROM users WHERE employee_id=?',(employee_id,)).fetchone()
    if not row or not verify(str(data.get('password','')),row['password_hash']):
        raise ServiceError('Invalid employee ID or password',401)
    return {'employee_id':row['employee_id'],'role':row['role']}

def inventory(search='',low=False):
    sql="""SELECT i.id,i.name,i.quantity,i.minimum_qty,c.name AS category,
      c.id AS category_id FROM inventory i JOIN categories c ON i.category_id=c.id WHERE 1=1"""
    args=[]
    if search:sql+=' AND (i.name LIKE ? OR c.name LIKE ?)';args += ['%'+search+'%']*2
    if low:sql+=' AND i.quantity<=i.minimum_qty'
    sql+=' ORDER BY i.name COLLATE NOCASE'
    with connect() as db:return [dict(r) for r in db.execute(sql,args).fetchall()]

def categories():
    with connect() as db:return [dict(r) for r in db.execute('SELECT id,name FROM categories ORDER BY name')]

def update_quantity(item_id,data):
    quantity=whole(data.get('quantity'),'quantity')
    with connect() as db:
        if db.execute('UPDATE inventory SET quantity=? WHERE id=?',(quantity,item_id)).rowcount==0:
            raise ServiceError('Item not found',404)
    return {'id':item_id,'quantity':quantity}

def save_item(data,user,item_id=None):
    manager(user)
    name=required(data,'name')
    category_id=whole(data.get('category_id'),'category_id')
    minimum=whole(data.get('minimum_qty'),'minimum_qty')
    with connect() as db:
        if not db.execute('SELECT 1 FROM categories WHERE id=?',(category_id,)).fetchone():raise ServiceError('Invalid category')
        if item_id is None:
            quantity=whole(data.get('quantity'),'quantity')
            cur=db.execute('INSERT INTO inventory(name,category_id,quantity,minimum_qty) VALUES(?,?,?,?)',(name,category_id,quantity,minimum))
            item_id=cur.lastrowid
        else:
            if db.execute('UPDATE inventory SET name=?,category_id=?,minimum_qty=? WHERE id=?',(name,category_id,minimum,item_id)).rowcount==0:
                raise ServiceError('Item not found',404)
    return {'id':item_id}

def report(user):
    manager(user)
    with connect() as db:
        return dict(db.execute("""SELECT COUNT(*) AS items,COALESCE(SUM(quantity),0) AS total_quantity,
           COALESCE(SUM(CASE WHEN quantity<=minimum_qty THEN 1 ELSE 0 END),0) AS low_stock
           FROM inventory""").fetchone())

def create_employee(data,user):
    manager(user)
    employee_id=required(data,'employee_id')
    password=required(data,'password')
    role=required(data,'role')
    if role not in ('staff','manager'):raise ServiceError('Role must be staff or manager')
    with connect() as db:
        try:db.execute('INSERT INTO users(employee_id,password_hash,role) VALUES(?,?,?)',(employee_id,hash_password(password),role))
        except Exception as e:
            if 'UNIQUE constraint failed' in str(e):raise ServiceError('Employee ID already exists')
            raise
    return {'employee_id':employee_id,'role':role}
