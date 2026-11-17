# TaskFlow API

[![CI](https://github.com/fatihguloglu34/taskflow-api/actions/workflows/ci.yml/badge.svg)](https://github.com/fatihguloglu34/taskflow-api/actions/workflows/ci.yml)

Takımlar için görev yönetimi REST API'si. Kullanıcılar proje oluşturup ekip arkadaşlarını davet edebiliyor, görevleri atayıp takip edebiliyor ve görevler üzerine yorum yazabiliyor. Trello / Jira mantığının sadeleştirilmiş bir backend'i.

**Kullanılan teknolojiler:** Python, FastAPI, SQLAlchemy 2.0, PostgreSQL / SQLite, Pydantic v2, JWT, Pytest, Docker, GitHub Actions

## Özellikler

- **Kimlik doğrulama:** Kayıt / giriş, JWT access token, bcrypt ile şifre hashleme
- **Rol bazlı yetkilendirme:** Her projede `owner`, `admin` ve `member` rolleri
- **Projeler:** CRUD, üye ekleme/çıkarma, rol değiştirme, projeden ayrılma
- **Görevler:** Durum (`todo`, `in_progress`, `done`), öncelik, bitiş tarihi, atama
- **Filtreleme & arama:** Durum, öncelik, atanan kişi, geciken görevler, metin araması
- **Sıralama & sayfalama:** `sort_by`, `order`, `limit`, `offset`
- **İstatistikler:** Proje bazında durum/öncelik dağılımı, geciken görev sayısı, tamamlanma oranı
- **Yorumlar:** Görevlere yorum ekleme/silme
- **Testler:** 22 entegrasyon testi, her push'ta GitHub Actions üzerinde çalışıyor

## Yetki Tablosu

| İşlem | member | admin | owner |
|---|:-:|:-:|:-:|
| Projeyi ve görevleri görme | ✓ | ✓ | ✓ |
| Görev oluşturma / güncelleme | ✓ | ✓ | ✓ |
| Başkasının görevini / yorumunu silme | | ✓ | ✓ |
| Proje bilgilerini güncelleme | | ✓ | ✓ |
| Üye ekleme / çıkarma | | ✓ | ✓ |
| Admin atama, rol değiştirme | | | ✓ |
| Projeyi silme | | | ✓ |

Projeye üye olmayan kullanıcılar projeyle ilgili isteklerde `403` yerine `404` alır, böylece projenin var olup olmadığı dışarıya sızmaz.

## Kurulum

### Lokal (SQLite)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

uvicorn app.main:app --reload
```

### Docker (PostgreSQL)

```bash
docker compose up --build
```

API `http://localhost:8000` adresinde çalışır. Swagger dokümantasyonu: **http://localhost:8000/docs**

### Demo verisi

```bash
python -m scripts.seed
# giriş: demo@taskflow.dev / demo12345
```

### Testler

```bash
pytest -q
```

## Endpoint'ler

Tüm endpoint'ler `/api/v1` altında.

| Method | Endpoint | Açıklama |
|---|---|---|
| POST | `/auth/register` | Kayıt ol |
| POST | `/auth/login` | Giriş yap, token al |
| GET / PATCH | `/users/me` | Profil bilgileri |
| GET | `/users/me/tasks` | Bana atanan görevler |
| GET / POST | `/projects` | Projelerimi listele / proje oluştur |
| GET / PATCH / DELETE | `/projects/{id}` | Proje detay / güncelle / sil |
| GET | `/projects/{id}/stats` | Proje istatistikleri |
| GET / POST | `/projects/{id}/members` | Üyeleri listele / üye ekle |
| PATCH / DELETE | `/projects/{id}/members/{user_id}` | Rol değiştir / üyeyi çıkar |
| GET / POST | `/projects/{id}/tasks` | Görevleri listele (filtreli) / görev oluştur |
| GET / PATCH / DELETE | `/projects/{id}/tasks/{task_id}` | Görev detay / güncelle / sil |
| GET / POST | `/projects/{id}/tasks/{task_id}/comments` | Yorumlar |
| DELETE | `/projects/{id}/tasks/{task_id}/comments/{comment_id}` | Yorumu sil |

### Örnek kullanım

```bash
# Kayıt
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"ali@example.com","password":"password123","full_name":"Ali Veli"}'

# Giriş
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -d "username=ali@example.com&password=password123" | jq -r .access_token)

# Geciken ve yüksek öncelikli görevler
curl "localhost:8000/api/v1/projects/1/tasks?overdue=true&priority=high&sort_by=due_date&order=asc" \
  -H "Authorization: Bearer $TOKEN"
```

## Proje Yapısı

```
app/
├── main.py            # FastAPI uygulaması, middleware, router kayıtları
├── db.py              # Veritabanı bağlantısı ve session
├── models.py          # SQLAlchemy modelleri
├── core/
│   ├── config.py      # Ortam değişkenleri
│   └── security.py    # JWT ve şifre hashleme
├── schemas/           # Pydantic request/response modelleri
└── api/
    ├── deps.py        # Auth ve yetki kontrolü dependency'leri
    └── routes/        # auth, users, projects, tasks, comments
tests/                 # pytest testleri
scripts/seed.py        # Demo verisi
```

## Yapılacaklar

- [ ] Alembic ile veritabanı migration'ları
- [ ] Refresh token
- [ ] Rate limiting
- [ ] Görev etiketleri (label)
