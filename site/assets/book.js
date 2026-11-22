(() => {
  'use strict';
  const $=s=>document.querySelector(s);
  const input=$('#search-input'), results=$('#search-results');
  const sidebar=$('#sidebar'), scrim=$('#scrim'), menu=$('#menu-btn');
  const theme=$('#theme-btn');
  const prefix=window.UNIBOOK_PREFIX||'';
  const pages=window.UNIBOOK_SEARCH_DATA||[];
  function closeMenu(){ sidebar?.classList.remove('open');scrim?.classList.remove('show'); }
  function toggleMenu(){sidebar?.classList.toggle('open');scrim?.classList.toggle('show');}
  menu?.addEventListener('click',toggleMenu);
  scrim?.addEventListener('click',closeMenu);
  theme?.addEventListener('click',()=>{
    const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=next;
    try{localStorage.setItem('unibook_theme',next);}catch(e){}
  });
  function normal(s){return (s||'').toLocaleLowerCase('ru').replace(/ё/g,'е');}
  function excerpt(text,q){
    const t=text||''; const p=normal(t).indexOf(q);
    const start=p<0?0:Math.max(0,p-55);
    const excerpt=t.slice(start,start+145);
    return (start?'…':'')+excerpt+(start+145<t.length?'…':'');
  }
  function updateSearch(){
    if(!results||!input) return;
    const q=normal(input.value.trim());
    results.replaceChildren();
    if(q.length<2){results.classList.remove('visible');return;}
    const hits=pages.filter(p=>normal(p.title+' '+p.category+' '+p.text).includes(q)).slice(0,12);
    if(!hits.length){
      const empty=document.createElement('div');empty.className='search-empty';
      empty.textContent='Совпадений не найдено';results.appendChild(empty);
    } else {
      hits.forEach(p=>{
        const a=document.createElement('a');a.className='search-item';
        a.href=prefix+p.path;
        const title=document.createElement('strong');title.textContent=p.title;
        const cat=document.createElement('small');cat.textContent=p.category;
        const frag=document.createElement('em');frag.textContent=excerpt(p.text,q);
        a.append(title,cat,frag);results.appendChild(a);
      });
    }
    results.classList.add('visible');
  }
  input?.addEventListener('input',updateSearch);
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'){input?.blur();results?.classList.remove('visible');closeMenu();return;}
    const el=document.activeElement;
    const editing=el&&(el.tagName==='INPUT'||el.tagName==='TEXTAREA'||el.isContentEditable);
    if(e.key==='/'&&!editing){e.preventDefault();input?.focus();if(window.innerWidth<850){sidebar?.classList.add('open');scrim?.classList.add('show');}}
  });
})();
