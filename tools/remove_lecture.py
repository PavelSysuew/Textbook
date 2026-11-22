#!/usr/bin/env python3
"""Safely remove a lecture from the Universitas HTML textbook.

Usage:
  python3 tools/remove_lecture.py numerical-methods lecture01.qmd
  python3 tools/remove_lecture.py cryptography lecture_02.qmd --dry-run
  python3 tools/remove_lecture.py numerical-methods lecture01.qmd --yes

The script removes a registered .qmd lecture, its entry in book.json and
_quarto.yml, and its generated HTML page; then rebuilds the site with Pandoc.
It does not delete shared figures in subjects/<subject>/assets/.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from add_lecture import make_config

ROOT = Path(__file__).resolve().parents[1]


def page_html(rel: str) -> Path:
    return ROOT / 'site' / (rel[:-4] + '.html')


def select_page(pages: list[dict], query: str, subject_id: str, parser: argparse.ArgumentParser) -> dict:
    query = query.replace('\\', '/').strip()
    if not query or Path(query).is_absolute() or '..' in Path(query).parts:
        parser.error('Укажите название .qmd либо относительный путь внутри проекта')
    matches = []
    for page in pages:
        name = page.get('file', '')
        if name == query or Path(name).name == query or ('.' not in Path(query).name and Path(name).stem == query):
            matches.append(page)
    if not matches:
        parser.error(f'Лекция «{query}» не зарегистрирована в разделе {subject_id} (book.json)')
    if len(matches) > 1:
        options = '\n'.join(f'  - {p["file"]}' for p in matches)
        parser.error(f'Неоднозначное имя; укажите полный относительный путь:\n{options}')
    return matches[0]


def safe_lecture_path(rel: str, subject_id: str, parser: argparse.ArgumentParser) -> Path:
    path = Path(rel)
    expected = ('subjects', subject_id, 'lectures')
    if path.is_absolute() or len(path.parts) != 4 or path.parts[:3] != expected or path.suffix.lower() != '.qmd':
        parser.error('Можно удалять только файлы subjects/<предмет>/lectures/*.qmd')
    absolute = ROOT / path
    if not absolute.resolve().is_relative_to(ROOT.resolve()):
        parser.error('Путь выходит за пределы репозитория')
    return absolute


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Удалить лекцию из book.json, _quarto.yml и готового HTML-сайта'
    )
    parser.add_argument('subject', help='ID предмета, например numerical-methods')
    parser.add_argument('lecture', help='Имя лекции, например lecture01.qmd')
    parser.add_argument('--dry-run', action='store_true', help='Только показать, что будет удалено')
    parser.add_argument('--yes', '-y', action='store_true', help='Не запрашивать подтверждение')
    parser.add_argument('--no-build', action='store_true', help='Не пересобирать сайт (временно оставит старое меню на других страницах)')
    args = parser.parse_args()

    manifest_file = ROOT / 'book.json'
    quarto_file = ROOT / '_quarto.yml'
    if not manifest_file.is_file():
        parser.error(f'Не найден book.json: {manifest_file}')
    manifest_before = manifest_file.read_bytes()
    try:
        manifest = json.loads(manifest_before.decode('utf-8'))
    except (ValueError, UnicodeDecodeError) as exc:
        parser.error(f'Ошибка чтения book.json: {exc}')

    subject = next((s for s in manifest['subjects'] if s['id'] == args.subject), None)
    if subject is None:
        parser.error(f'Предмет «{args.subject}» не найден. Проверьте ID в book.json')
    page = select_page(subject['pages'], args.lecture, args.subject, parser)
    rel = page['file']
    lecture_path = safe_lecture_path(rel, args.subject, parser)
    html_path = page_html(rel)
    if not html_path.resolve().is_relative_to((ROOT / 'site').resolve()):
        parser.error('Опасный путь HTML-файла')

    print(f'Предмет: {subject["title"]}')
    print(f'Лекция:  {page.get("title", Path(rel).stem)}')
    print(f'Исходник: {lecture_path.relative_to(ROOT)}' + ('' if lecture_path.exists() else ' (отсутствует)'))
    print(f'HTML:     {html_path.relative_to(ROOT)}' + ('' if html_path.exists() else ' (отсутствует)'))
    print('Также обновятся book.json, _quarto.yml, оглавление и поиск.')
    print('Общие графики и изображения из assets/ не удаляются.')

    if args.dry_run:
        print('\nПроверка (--dry-run) завершена. Файлы не изменены.')
        return
    if not args.no_build and shutil.which('pandoc') is None:
        parser.error('Для пересборки нужен Pandoc. Установите: sudo apt install pandoc')
    if not args.yes:
        if not sys.stdin.isatty():
            parser.error('В неинтерактивном режиме добавьте --yes')
        answer = input('\nУдалить эту лекцию? [д/Н]: ').strip().casefold()
        if answer not in {'д', 'да', 'y', 'yes'}:
            print('Удаление отменено.')
            return

    quarto_before = quarto_file.read_bytes() if quarto_file.exists() else None
    with tempfile.TemporaryDirectory(prefix='unibook-delete-') as backup_folder:
        backup = Path(backup_folder)
        for path, name in ((lecture_path, 'lecture.qmd'), (html_path, 'lecture.html')):
            if path.exists():
                shutil.copy2(path, backup / name)
        try:
            # The manifest is the single source of truth for both the menu and book config.
            subject['pages'].remove(page)
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            quarto_file.write_text(make_config(manifest), encoding='utf-8')
            lecture_path.unlink(missing_ok=True)
            html_path.unlink(missing_ok=True)
            if not args.no_build:
                subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_site.py')], check=True)
        except Exception:
            # Restore project metadata and deleted lecture if anything fails.
            manifest_file.write_bytes(manifest_before)
            if quarto_before is not None:
                quarto_file.write_bytes(quarto_before)
            else:
                quarto_file.unlink(missing_ok=True)
            for path, name in ((lecture_path, 'lecture.qmd'), (html_path, 'lecture.html')):
                if (backup / name).exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup / name, path)
            if not args.no_build:
                try:
                    subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_site.py')], check=True)
                except Exception:
                    print('Не удалось пересобрать прежнюю версию сайта; исходники и настройки восстановлены.', file=sys.stderr)
            raise

    print('\nЛекция удалена из проекта.')
    if args.no_build:
        print('ВНИМАНИЕ: после этого запустите python3 tools/build_site.py, чтобы обновить поиск и меню.')
    else:
        print('HTML-сайт пересобран. Можно выполнить git add -A, git commit и git push.')


if __name__ == '__main__':
    main()
