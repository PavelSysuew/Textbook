# Как опубликовать учебник на GitHub Pages

## Что уже готово

Это полный исходный проект. В нем есть `subjects/**.qmd`, `tools/build_site.py`,
`site/` (готовый HTML) и `.github/workflows/publish.yml` (автоматическая сборка на GitHub).
Не загружайте сам ZIP в репозиторий: нужно распаковать его и отправить **содержимое** папки `university-textbook`.

## 1. Создайте публичный репозиторий

На https://github.com/new укажите название `university-textbook`, выберите **Public**
и нажмите Create repository. Не добавляйте отдельный README или лицензию при создании:
в проекте уже есть README.

## 2. Отправьте проект из Ubuntu

Откройте терминал внутри распакованной папки `university-textbook`:

```bash
git init
git branch -M main
git add .
git commit -m "Первый выпуск университетского учебника"
git remote add origin git@github.com:ВАШ_ЛОГИН/university-textbook.git
git push -u origin main
```

Замените `ВАШ_ЛОГИН` на свой логин GitHub. При необходимости настройте Git/SSH.

## 3. Включите GitHub Pages

Откройте `Settings` → `Pages` → `Build and deployment` → `Source: GitHub Actions`.
Проверьте вкладку `Actions`, дождитесь зеленой галочки у `Publish university textbook`.
Откройте `https://ВАШ_ЛОГИН.github.io/university-textbook/`.

## 4. Добавьте новую лекцию

Создайте `.qmd` в подходящей папке предмета (например,
`subjects/cryptography/lectures/01-lecture.qmd`), добавьте запись в `book.json`
или используйте `tools/add_lecture.py` по инструкции в README. Затем:

```bash
git add .
git commit -m "Добавлена новая лекция"
git push
```

GitHub Actions соберет HTML из исходников (Pandoc) и опубликует обновленный сайт.
Для локальной проверки выполните:

```bash
sudo apt install pandoc
python3 tools/build_site.py
python3 -m http.server 8000 -d site
```

После запуска локальный адрес — `http://localhost:8000/`.

## Важные моменты

- Сайт статический, сервер и база данных не нужны.
- Исходные лекции и сайт будут публичны в репозитории `Public`: проверьте права на публикацию материалов преподавателя и отсутствие личных данных.
- Архив **не** содержит исходные сканы и практикум, как и было оговорено.
- Хостинг GitHub Pages бесплатен при публичном репозитории для GitHub Free.
