# chat-server

Учебный бэкенд мессенджера: Django (ORM, admin, миграции, Celery) + FastAPI (весь REST API) на одной базе Postgres, Centrifugo для realtime, Celery для обработки вложений. Ваша задача — написать фронтенд поверх этого API.

Задеплоен на **https://vkedu-fullstack-div2.ru** — те же пути, что и локально, просто вместо `http://localhost:8080` везде подставляйте `https://vkedu-fullstack-div2.ru` (и `wss://` вместо `ws://` для Centrifugo).

Swagger/OpenAPI: **http://localhost:8080/api/docs** локально или **https://vkedu-fullstack-div2.ru/api/docs** на проде.

## Стек и порты

| Сервис | Роль | Доступ снаружи |
|---|---|---|
| nginx | единая точка входа | `http://localhost:8080` |
| api (FastAPI) | весь REST API | через nginx: `/api/*` |
| django | admin, миграции | через nginx: `/admin/*` |
| centrifugo | realtime (WebSocket) | через nginx: `/connection/websocket` |
| postgres, redis, celery | инфраструктура | наружу не смотрят |

Всё за одним хостом `http://localhost:8080` — CORS-проблем при разработке фронтенда быть не должно.

## Запуск локально

Нужен Docker + Docker Compose.

```bash
make env        # cp .env.example -> .env
make up         # docker compose up -d (соберёт образы сам)
make migrate    # применить миграции Django
make superuser  # завести админа (для /admin)
```

Проверить, что всё поднялось:

```bash
curl http://localhost:8080/api/health
# {"status":"ok"}
```

Остальные команды — `make help`. Полезные: `make logs`, `make ps`, `make down`, `make deploy` (git pull + пересборка без даунтайма).

## Авторизация

JWT access-токен (по умолчанию живёт 15 минут) + опаковый refresh-токен (30 дней, хранится в БД, при рефреше перевыпускается). Access-токен кладётся в заголовок `Authorization: Bearer <token>` на каждый запрос к API.

### Регистрация

`POST /api/auth/register` — **multipart/form-data** (можно сразу приложить аватар):

```js
const form = new FormData()
form.append('username', 'alice')
form.append('password', 'password123')
form.append('first_name', 'Alice')
form.append('avatar', fileInput.files[0]) // необязательно

const res = await fetch('http://localhost:8080/api/auth/register', {
  method: 'POST',
  body: form, // Content-Type не ставим руками — браузер сам проставит boundary
})
const { access_token, refresh_token, user } = await res.json()
```

### Логин / рефреш / логаут

Обычный JSON:

```js
async function login(username, password) {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  return res.json() // { access_token, refresh_token, token_type, user }
}

async function refresh(refresh_token) {
  const res = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token }),
  })
  return res.json() // новая пара токенов, старый refresh_token отзывается
}

await fetch('/api/auth/logout', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ refresh_token }),
}) // 204, refresh_token отозван
```

### Авторизованный запрос

```js
async function apiFetch(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${accessToken}` },
  })
  if (res.status === 401) {
    // access-токен истёк -> обновляемся по refresh_token и повторяем запрос
  }
  return res
}
```

Практика: ловите `401` глобально (например в axios-интерцепторе), дергайте `/api/auth/refresh`, сохраняйте новую пару токенов и повторяйте исходный запрос.

## Multipart-загрузки

FastAPI ждёт `multipart/form-data` везде, где есть файл: регистрация с аватаркой, смена аватарки, создание группы с аватаркой, отправка медиа-сообщения. Правило одно: собираем `FormData`, **не** выставляем `Content-Type` вручную.

Пример — отправка фото в чат:

```js
async function sendMedia(chatId, file, text = '') {
  const form = new FormData()
  form.append('type', 'image') // image | video | voice | video_circle | file
  form.append('text', text)
  form.append('file', file)

  const res = await apiFetch(`/api/chats/${chatId}/messages/media`, {
    method: 'POST',
    body: form,
  })
  return res.json()
}
```

Смена своей аватарки:

```js
const form = new FormData()
form.append('file', fileInput.files[0])
await apiFetch('/api/users/me/avatar', { method: 'POST', body: form })
```

Ограничение размера файла — `MAX_UPLOAD_SIZE_BYTES` в `.env` (по умолчанию 50 МБ), при превышении — `413`.

## Realtime через Centrifugo

1. Получить токен подключения (JWT, отдельный от access-токена):

```js
const { token, channel, expires_in } = await (await apiFetch('/api/realtime/token')).json()
```

2. Подключиться и подписаться на свой личный канал (`personal#<user_id>`, он же приходит в `channel`):

```js
import { Centrifuge } from 'centrifuge' // npm i centrifuge

const centrifuge = new Centrifuge('ws://localhost:8080/connection/websocket', {
  getToken: async () => {
    const r = await apiFetch('/api/realtime/token')
    return (await r.json()).token
  },
})

const sub = centrifuge.newSubscription(channel)
sub.on('publication', (ctx) => {
  const { type, data } = ctx.data // конверт события
  handleEvent(type, data)
})
sub.subscribe()
centrifuge.connect()
```

Токен живёт `expires_in` секунд (по умолчанию 300) — `getToken` вызывается библиотекой автоматически на реконнекте/протухании, ничего дополнительно обновлять не нужно.

3. Каждое событие приходит конвертом `{"type": "...", "data": {...}}`. Возможные `type`:

| type | data |
|---|---|
| `message.new` | новое сообщение (`MessageOut`) |
| `message.updated` | отредактированное сообщение |
| `message.deleted` | `{id, chat_id}` |
| `message.read` | `{chat_id, user_id, message_id}` |
| `chat.created` | новый чат (`ChatOut`), в т.ч. когда вам создали приватный чат первым сообщением |
| `chat.updated` | изменились участники/настройки/непрочитанные |
| `chat.member_removed` | `{chat_id, user_id}` |

Личный канал у каждого пользователя один — туда прилетают события по всем его чатам, фильтровать по `chat_id`/`type` нужно на клиенте.

## Краткая карта REST API

Все пути ниже — относительно `/api`, все (кроме `auth/*`) требуют `Authorization: Bearer`.

- `auth/register`, `auth/login`, `auth/refresh`, `auth/logout`, `auth/change-password`
- `users/me` (GET/PATCH/DELETE), `users/me/avatar` (POST), `users/search?q=`
- `chats` (GET — список), `chats/group` (POST — создать группу)
- `chats/{id}` (GET/PATCH/DELETE), `chats/{id}/mute`, `chats/{id}/avatar`
- `chats/{id}/members` (POST добавить), `chats/{id}/members/{user_id}` (PATCH роль / DELETE выгнать)
- `chats/{id}/messages` (GET список / POST текст), `chats/{id}/messages/media` (POST медиа)
- `chats/{id}/messages/{message_id}` (PATCH/DELETE), `chats/{id}/read`, `chats/{id}/messages/{message_id}/read-by`
- `chats/direct/{other_user_id}` (POST текст), `chats/direct/{other_user_id}/media` (POST медиа) — приватный чат создаётся лениво первым сообщением, отдельного «создать чат» эндпоинта нет
- `realtime/token` (GET)

Точные схемы запросов/ответов — в `/api/docs` (это живой Swagger, ходит прямо в текущий инстанс).
