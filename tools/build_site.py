#!/usr/bin/env python3
"""Offline compiler: .qmd / Markdown -> MathML HTML pages for 6-subject book.

Only Pandoc is needed. Subject / chapter inventory lives in book.json.
"""
from __future__ import annotations

import html
import json
import posixpath
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site'
MANIFEST = json.loads((ROOT/'book.json').read_text(encoding='utf-8'))


def all_pages() -> list[dict]:
    pages = [{'file':'index.qmd','title':'Главная','label':'Главная','subject':None,'category':'Обзор'}]
    for subject in MANIFEST['subjects']:
        pages.append({'file':subject['index'], 'title':subject['title'], 'label':'Обзор предмета',
                      'subject':subject['id'], 'category':subject['title']})
        for page in subject['pages']:
            pages.append({**page,'subject':subject['id'],'category':subject['title']})
    return pages

PAGES = all_pages()

def page_path(qmd: str) -> str:
    return 'index.html' if qmd == 'index.qmd' else qmd.removesuffix('.qmd') + '.html'


def pandoc_html(filepath: Path) -> str:
    args = ['pandoc','-f','markdown+fenced_divs+tex_math_dollars+raw_html+yaml_metadata_block',
            '-t','html5','--mathml','--wrap=none',str(filepath)]
    p = subprocess.run(args, text=True, capture_output=True, check=True)
    return p.stdout


def plain_text(source: str) -> str:
    source = re.sub(r'^---\s*\n.*?\n---\s*\n', '', source, flags=re.S)
    source = re.sub(r'```.*?```', ' ', source, flags=re.S)
    source = re.sub(r'\$\$.*?\$\$', ' ', source, flags=re.S)
    source = re.sub(r'(?<!\\)\$.*?(?<!\\)\$', ' ', source, flags=re.S)
    source = re.sub(r'^:::\s*(?:\{[^}]*\})?\s*$', ' ', source, flags=re.M)
    source = re.sub(r'<[^>]+>', ' ', source)
    source = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1', source)
    source = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', source)
    source = re.sub(r'[#$*`<>|_\\{}\[\]]', ' ', source)
    return re.sub(r'\s+', ' ', source).strip()[:24000]


def nav_html(current: dict, prefix: str) -> str:
    parts = [f'<a class="nav-home {"active" if current["file"] == "index.qmd" else ""}" href="{prefix}index.html"><span class="home-glyph">⌂</span> Главная страница</a>',
             '<div class="sidebar-caption">Дисциплины</div>']
    for subject in MANIFEST['subjects']:
        this_subject = current.get('subject') == subject['id']
        pages = subject['pages']
        open_attr = ' open' if this_subject else ''
        parts.append(f'<details class="subject-nav tone-{html.escape(subject["tone"])}"{open_attr}>')
        parts.append(f'<summary><span class="mini-symbol">{html.escape(subject["symbol"])}</span>'
                     f'<span class="nav-subject-title">{html.escape(subject["title"])}'
                     f'<small>{len([p for p in pages if p["label"]=="Лекция"])} лекц.</small></span>'
                     '<span class="expand-indicator">⌄</span></summary>')
        parts.append('<div class="subject-chapters">')
        entries = [{'file':subject['index'],'title':'О разделе'},*pages]
        for page in entries:
            active = ' active' if current['file'] == page['file'] else ''
            parts.append(f'<a class="chapter-link{active}" href="{prefix}{page_path(page["file"])}">{html.escape(page["title"])}</a>')
        parts.append('</div></details>')
    return '\n'.join(parts)


def make_toc(fragment: str) -> str:
    matches = re.findall(r'<h([23])\s+id="([^"]+)"[^>]*>(.*?)</h\1>', fragment, flags=re.S)
    links=[]
    for level, id_, raw in matches:
        # MathML contains both a presentation and a LaTeX annotation. Keeping
        # both makes formulas appear twice in the generated table of contents.
        raw=re.sub(r'<annotation\b[^>]*>.*?</annotation>', '', raw, flags=re.S)
        txt=re.sub(r'<[^>]+>','',raw)
        txt=html.unescape(txt).strip()
        if not txt: continue
        links.append(f'<a class="toc-link toc-level-{level}" href="#{html.escape(id_,quote=True)}">{html.escape(txt)}</a>')
    if len(links)<2: return ''
    return '<details class="page-toc"><summary>На этой странице <span>⌄</span></summary><nav aria-label="Разделы страницы">'+'\n'.join(links)+'</nav></details>'


def rewrite_qmd_links(fragment: str) -> str:
    # Preserve fragment anchors and relative hierarchy; change only links, not text or code.
    return re.sub(r'(href=["\'])([^"\'#?]+)\.qmd(?=[#?"\'])',r'\1\2.html',fragment)


def render_doc(page: dict, idx: int) -> None:
    qmd = page['file']; title=page['title']; cat=page['category']
    target = OUT / page_path(qmd)
    target.parent.mkdir(parents=True, exist_ok=True)
    depth = len(Path(qmd).parts)-1
    prefix = '../'*depth
    main = rewrite_qmd_links(pandoc_html(ROOT/qmd))
    toc = '' if qmd == 'index.qmd' else make_toc(main)
    subject = next((s for s in MANIFEST['subjects'] if s['id'] == page['subject']),None)
    subject_link = f'<a href="{prefix}{page_path(subject["index"])}">{html.escape(subject["title"])}</a> <span class="crumb-sep">/</span> ' if subject and page['file'] != subject['index'] else ''
    prev = PAGES[idx-1] if idx else None
    nxt = PAGES[idx+1] if idx<len(PAGES)-1 else None
    prev_link = (f'<a class="pager-prev" href="{prefix}{page_path(prev["file"])}"><span>← Предыдущая</span><strong>{html.escape(prev["title"])}</strong></a>' if prev else '<div></div>')
    next_link = (f'<a class="pager-next" href="{prefix}{page_path(nxt["file"])}"><span>Следующая →</span><strong>{html.escape(nxt["title"])}</strong></a>' if nxt else '<div></div>')
    result = f'''<!DOCTYPE html>
<html lang="ru" data-theme="light">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Sysuew — электронный университетский учебник">
<title>{html.escape(title)} · Sysuew</title>
<link rel="stylesheet" href="{prefix}styles.css">
<script>try{{let theme=localStorage.getItem('unibook_theme');if(theme==='dark'||theme==='light')document.documentElement.dataset.theme=theme;}}catch(e){{}}</script>
</head>
<body>
<div class="shell">
<aside class="sidebar" id="sidebar" aria-label="Навигация по книге">
 <a class="brand" href="{prefix}index.html"><span class="brand-icon">S<span>Y</span></span><span class="brand-copy">SYSUEW<small>ЛИЧНАЯ БИБЛИОТЕКА</small></span></a>
 <div class="sidebar-search"><div class="search-field"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg><input id="search-input" type="search" autocomplete="off" aria-label="Поиск по книге" placeholder="Поиск по учебнику…"><kbd>/</kbd></div><div id="search-results" aria-live="polite"></div></div>
 <nav class="book-nav">{nav_html(page,prefix)}</nav>
 <div class="sidebar-footer"><span class="online-indicator"></span> Электронный учебник <small>6 дисциплин · единый поиск</small></div>
</aside>
<div id="scrim" class="scrim" aria-hidden="true"></div>
<div class="workspace">
 <header class="topbar"><div class="header-left"><button class="mobile-menu" id="menu-btn" aria-label="Открыть меню">☰</button><a href="{prefix}index.html" class="breadcrumb-root">Учебник</a><span class="crumb-sep">/</span>{subject_link}<span class="breadcrumb-current">{html.escape('Каталог дисциплин' if not subject else title)}</span></div><div class="header-right"><span class="header-capsule">{html.escape(cat)}</span><button id="theme-btn" class="theme-toggle" title="Сменить тему" aria-label="Сменить тему"><span class="theme-icon">◐</span><span class="theme-label">Тема</span></button></div></header>
 <main class="content-wrap"><div class="article-top"><span class="overline">{html.escape(cat.upper())}</span><span class="page-index">{idx+1:02d} / {len(PAGES):02d}</span></div><article class="content">{toc}{main}</article><nav class="page-pager" aria-label="Навигация по страницам">{prev_link}{next_link}</nav><footer class="footnote">Sysuew · Шесть дисциплин в одной книге · HTML из Markdown + LaTeX</footer></main>
</div></div>
<script>window.UNIBOOK_PREFIX={json.dumps(prefix)};</script>
<script src="{prefix}assets/search-data.js"></script>
<script src="{prefix}assets/book.js"></script>
</body></html>'''
    target.write_text(result,encoding='utf8')


def main():
    if not shutil.which('pandoc'):
        raise SystemExit('Необходим Pandoc: sudo apt install pandoc')
    OUT.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'styles.css',OUT/'styles.css')
    (OUT/'assets').mkdir(exist_ok=True)
    for subject in MANIFEST['subjects']:
        src=ROOT/'subjects'/subject['id']/'assets'
        if src.exists():
            dest=OUT/'subjects'/subject['id']/'assets'
            shutil.copytree(src,dest,dirs_exist_ok=True)
    search=[]
    for i,page in enumerate(PAGES):
        file=ROOT/page['file']
        if not file.exists(): raise ValueError(f'Нет файла: {file}')
        render_doc(page,i)
        src=file.read_text(encoding='utf8')
        search.append({'title':page['title'],'category':page['category'],
                       'path':page_path(page['file']),'text':plain_text(src)})
    (OUT/'assets'/'search-data.js').write_text('window.UNIBOOK_SEARCH_DATA = '+json.dumps(search,ensure_ascii=False)+';\n',encoding='utf8')
    shutil.copy2(ROOT/'tools'/'book.js',OUT/'assets'/'book.js')
    print(f'Готово: {len(PAGES)} страниц, {len(MANIFEST["subjects"])} предметов. {OUT/"index.html"}')

if __name__=='__main__':
    main()
