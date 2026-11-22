#!/usr/bin/env python3
"""Добавляет лекцию к одному из 6 предметов и обновляет меню/конфигурацию.

Пример:
  python3 tools/add_lecture.py cryptography ~/Downloads/lecture_01.qmd 'Введение в криптографию'
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def make_config(data:dict)->str:
    out='''project:
  type: book
  output-dir: _book
  execute:
    enabled: false

lang: ru

book:
  title: "Университетский учебник"
  subtitle: "Шесть дисциплин в одном электронном издании"
  chapters:
    - index.qmd
'''
    for subject in data['subjects']:
        name=json.dumps(subject['title'],ensure_ascii=False)
        out+=f'    - part: {name}\n      chapters:\n        - {subject["index"]}\n'
        for pg in subject['pages']:
            out+=f'        - {pg["file"]}\n'
    out+='''  page-navigation: true
  search: true
  sidebar:
    style: docked
    search: true
    collapse-level: 1

format:
  html:
    theme:
      light: cosmo
      dark: darkly
    css: styles.css
    toc: true
    toc-depth: 3
    number-sections: true
    code-copy: true
    smooth-scroll: true
    html-math-method: mathjax

editor: source
'''
    return out


def main():
    p=argparse.ArgumentParser(description='Добавить .qmd-лекцию в единый учебник')
    p.add_argument('subject',help='ID предмета: например, cryptography')
    p.add_argument('source',type=Path,help='Путь к новому файлу .qmd')
    p.add_argument('title',help='Название лекции в меню')
    p.add_argument('--no-build',action='store_true',help='Не собирать сайт после добавления')
    args=p.parse_args()
    manifest=ROOT/'book.json'
    data=json.loads(manifest.read_text(encoding='utf8'))
    subject=next((s for s in data['subjects'] if s['id']==args.subject),None)
    if not subject:p.error('Предмет не найден; проверьте его ID в book.json')
    src=args.source.expanduser().resolve()
    if not src.is_file() or src.suffix.lower()!='.qmd':p.error('Нужен существующий файл .qmd')
    dest=ROOT/'subjects'/subject['id']/'lectures'/src.name
    if dest.resolve()!=src and dest.exists():p.error(f'Файл уже существует: {dest}')
    rel=dest.relative_to(ROOT).as_posix()
    if any(page['file']==rel for page in subject['pages']):p.error('Эта лекция уже указана в book.json')
    dest.parent.mkdir(parents=True,exist_ok=True)
    if src!=dest.resolve():shutil.copy2(src,dest)
    subject['pages'].append({'file':rel,'title':args.title,'label':'Лекция'})
    manifest.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    (ROOT/'_quarto.yml').write_text(make_config(data),encoding='utf8')
    print('Добавлена лекция:',rel)
    if not args.no_build:
        subprocess.run([sys.executable,str(ROOT/'tools'/'build_site.py')],check=True)
        print('Открывайте:',ROOT/'site'/'index.html')

if __name__=='__main__':main()
