# 🍿 Filmoinator

Aplikacja webowa do wybierania filmów na wspólny seans. Użytkownicy dodają propozycje filmów, głosują w rundach, a system wyłania zwycięzcę.

## Funkcje

- **Wyszukiwarka filmów** — integracja z TMDB (plakaty, oceny, oznaczenia wiekowe)
- **System głosowania** — 3 rundy eliminacyjne (top 3 → top 2 → zwycięzca)
- **Ochrona przed wielokrotnym głosowaniem** — ciasteczka + opcjonalnie IP
- **Dodatkowy głos** — admin może zezwolić użytkownikowi na oddanie drugiego głosu (bez usuwania pierwszego)
- **ID urządzenia** — każdy użytkownik widzi swój identyfikator (#ABCD) na dole strony, co ułatwia znalezienie swojego głosu w panelu admina
- **Adminer** — zarządzanie bazą danych przez przeglądarkę pod `/adminer`

## Wymagania

- [Docker](https://docs.docker.com/desktop/setup/install/)

## Szybki start

```bash
git clone https://github.com/NNP-OSS/Filmoinator.git
cd Filmoinator
docker compose up -d
```

Po uruchomieniu wejdź na **http://localhost** — pierwsze uruchomienie przekieruje do konfiguracji.

## Konfiguracja

### Pierwsze uruchomienie

1. Wejdź na http://localhost
2. Wypełnij formularz:
   - **Nazwa użytkownika** — login do panelu administracyjnego
   - **Hasło** — minimum 4 znaki
   - **Klucz API TMDB** (opcjonalnie) — potrzebny do wyszukiwania filmów

### Klucz API TMDB

1. Załóż konto na [themoviedb.org](https://www.themoviedb.org/settings/api)
2. Wygeneruj **API Read Access Token (v4)**
3. Wpisz go podczas konfiguracji lub później w panelu admina → Ustawienia

### Zmiana portu

W `docker-compose.yml` zmień mapowanie portów dla serwisu `nginx`:

```yaml
services:
  nginx:
    ports:
      - "8080:80"   # zmień 8080 na dowolny port
```

### Zmiana klucza secret (sessions)

W `docker-compose.yml` dla serwisu `app`:

```yaml
environment:
  SECRET_KEY: twoj_wlasny_klucz
```

## Adminer (zarządzanie bazą danych)

Dostępny pod **http://localhost/adminer/**. Logowanie:

| Pole | Wartość |
|------|---------|
| System | PostgreSQL |
| Serwer | `db` |
| Użytkownik | `filmoinator` |
| Hasło | `filmoinator_secret` |
| Baza | `filmoinator` |

## Resetowanie hasła / konfiguracji

Usuń plik `data/config.json` i zrestartuj kontenery:

```bash
rm data/config.json
docker compose restart
```

Po wejściu na stronę zobaczysz ponownie formularz konfiguracji. **Baza danych** (filmy, głosy, wyniki) pozostaje nienaruszona.

## Jak to działa

| Runda | Faza | Opis |
|---|---|---|
| 1 | Dodawanie filmów | Użytkownicy wyszukują i dodają filmy z TMDB |
| 1 | Głosowanie | Głosowanie, 3 najlepsze filmy przechodzą dalej |
| 2 | Głosowanie | Głosowanie na 3 filmy, 2 najlepsze przechodzą do finału |
| 3 | Głosowanie (finał) | Wybór zwycięskiego filmu |

Administrator steruje fazami z poziomu panelu administracyjnego.

## Panel administracyjny

Dostępny pod `/admin` (przekierowuje do dashboardu jeśli sesja jest aktywna, w przeciwnym razie do logowania). Funkcje:

- Sterowanie rundami (rozpoczęcie/zakończenie głosowania)
- Podgląd statystyk głosowania na żywo
- Lista głosów z detalami (ID urządzenia, adres IP, przeglądarka)
- Cofanie głosów i zezwalanie na dodatkowy głos
- Zarządzanie filmami (przeglądanie/usuwanie)
- Zmiana klucza TMDB, loginu i hasła
- Włączanie/wyłączanie blokady według adresu IP
- Resetowanie całego głosowania

## Technologie

- **Backend:** Python, Flask, SQLAlchemy, Gunicorn
- **Baza danych:** PostgreSQL 16
- **Serwer HTTP:** Nginx
- **API zewnętrzne:** TMDB (The Movie Database)
- **Konteneryzacja:** Docker, Docker Compose
- **Zarządzanie DB:** Adminer
