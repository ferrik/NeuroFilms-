# NeuroFilms — MVP Backend Service

Сервіс для MVP-процесу **подачі, модерації та курування AI-відео** відповідно до продуктового бріфу.

## Що реалізовано

- П'ять секцій каталогу: `featured`, `new_drops`, `music_visions`, `experimental`, `creator_spotlight`.
- Прийом заявок авторів.
- Валідація правил маніфесту:
  - тривалість 2–10 хв,
  - тільки `1080p`,
  - `original worlds only`,
  - обов'язково саби/озвучка,
  - заборона відомих IP (Marvel/DC/Disney/...)
  - базовий safety-фільтр (deepfake/18+/violent keywords).
- Ручна модерація (approve/reject) з причиною.
- Публікація approved-контенту в одну з головних секцій.

## Запуск

```bash
python app.py
```

Сервіс піднімається на `http://127.0.0.1:8080`.

## API

- `GET /health`
- `GET /api/v1/sections`
- `POST /api/v1/submissions`
- `GET /api/v1/submissions?status=pending|approved|rejected`
- `POST /api/v1/submissions/{id}/review`
- `GET /api/v1/catalog`

### Приклад: створення заявки

```bash
curl -X POST http://127.0.0.1:8080/api/v1/submissions \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Neon Dreams",
    "creator_name": "Olena K",
    "duration_minutes": 5.5,
    "category": "music_visions",
    "world_original": true,
    "has_subtitles_or_voiceover": true,
    "resolution": "1080p",
    "description": "Original cyberpunk music vision",
    "keywords": ["cyberpunk", "music", "ai"]
  }'
```

### Приклад: модерація

```bash
curl -X POST http://127.0.0.1:8080/api/v1/submissions/1/review \
  -H 'Content-Type: application/json' \
  -d '{
    "decision": "approved",
    "moderation_reason": "Fits quality bar",
    "section": "featured"
  }'
```

## Тести

```bash
python -m unittest -q
```
