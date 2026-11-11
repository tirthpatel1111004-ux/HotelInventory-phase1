async function load(){try{const {items}=await api('/inventory?search='+encodeURIComponent(document.getElementById('search').value));document.getElementById('result').innerHTML=table(items);note(items.length+' item(s) found');}catch(e){note(e.message);}}
(async()=>{if(await setup()){document.getElementById('search_button').onclick=load;load();}})();
