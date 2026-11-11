async function api(path,method='GET',data){const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined});const j=await r.json();if(!r.ok)throw Error(j.error||'Request failed');return j;}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function note(s){document.getElementById('notice').textContent=s;}
let user;
async function setup(){try{user=(await api('/me')).user;}catch{location.href='/login';return false;}document.getElementById('who').textContent=user.employee_id+' ('+user.role+')';document.querySelectorAll('.manager').forEach(x=>x.hidden=user.role!=='manager');return true;}
async function logout(){await api('/logout','POST');location.href='/login';}
function table(items,action=''){return '<table><thead><tr><th>ID</th><th>Item</th><th>Category</th><th>Quantity</th><th>Minimum</th><th>Status</th>'+(action?'<th>Action</th>':'')+'</tr></thead><tbody>'+items.map(i=>`<tr><td>${i.id}</td><td>${esc(i.name)}</td><td>${esc(i.category)}</td><td>${i.quantity}</td><td>${i.minimum_qty}</td><td>${i.quantity<=i.minimum_qty?'LOW':'OK'}</td>${action?`<td><button data-id="${i.id}">${action}</button></td>`:''}</tr>`).join('')+'</tbody></table>';}
