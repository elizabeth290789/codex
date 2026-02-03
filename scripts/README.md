# Сборщик статей за месяц

Скрипт `article_scraper.py` ищет статьи за выбранный месяц на заданных блогах.
Он использует sitemap, а при необходимости загружает страницы, чтобы получить
название, дату публикации и краткое описание. Результат выводится в Markdown.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

```bash
python scripts/article_scraper.py --month 2026-01 --output reports/jan-2026.md
```

По умолчанию используется список блогов из задания. Можно передать собственный
набор URL:

```bash
python scripts/article_scraper.py --month 2026-01 \
  --sites https://adoric.com/blog/ https://vwo.com/blog/
```

Если за месяц ничего не найдено, в отчёте будет строка
`Нет статей за YYYY-MM` для соответствующего сайта.
