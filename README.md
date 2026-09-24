# 🍿 Filmoinator

Aplikacja webowa do wybierania filmów na wspólny seans. Użytkownicy dodają propozycje filmów, głosują w rundach, a system wyłania zwycięzcę.

## Funkcje

- **Wyszukiwarka filmów** — integracja z TMDB (plakaty, oceny, oznaczenia wiekowe)
- **System głosowania** — 3 rundy eliminacyjne (top 3 → top 2 → zwycięzca)
- **Ochrona przed wielokrotnym głosowaniem** — ciasteczka + opcjonalnie IP
- **Dodatkowy głos** — admin może zezwolić użytkownikowi na oddanie drugiego głosu (bez usuwania pierwszego)
- **ID urządzenia** — każdy użytkownik widzi swój identyfikator (#ABCD) na dole strony, co ułatwia znalezienie swojego głosu w panelu admina

## Wymagania

- [Docker](https://docs.docker.com/desktop/setup/install/)

## Szybki start

Skopiuj plik zmiennych środowiskowych i ustaw własne wartości:

```bash
cp stack.env.example stack.env
```

Najważniejsze zmienne:

| Zmienna | Opis |
|---|---|
| `ADMIN_PASSWORD` | Hasło do panelu administracyjnego |
| `TMDB_API_KEY` | Opcjonalny TMDB API Read Access Token v4 |
| `POSTGRES_PASSWORD` | Hasło bazy danych używane przez PostgreSQL i aplikację |
| `QR_URL` | Opcjonalny adres wyświetlany jako kod QR w widoku projektora |

Uruchom stack:

```bash
docker compose up -d --build
```

Po uruchomieniu wejdź na **http://localhost**. Klucz sesji Flask jest generowany automatycznie przy każdym uruchomieniu, a ustawienie blokady głosów według adresu IP zmienisz w panelu administracyjnym.

```bash
docker compose up -d --force-recreate app
```

## Panel administracyjny

Panel jest dostępny pod **http://localhost/admin**. Logowanie wymaga wyłącznie hasła ustawionego w `ADMIN_PASSWORD`; nazwa użytkownika nie jest używana.

Funkcje panelu:

- Sterowanie rundami (rozpoczęcie/zakończenie głosowania)
- Podgląd statystyk głosowania na żywo i widok projektora `/admin/widok`
- Lista głosów z detalami (ID urządzenia, adres IP, przeglądarka)
- Cofanie głosów i zezwalanie na dodatkowy głos
- Zarządzanie filmami
- Włączanie/wyłączanie blokady według adresu IP
- Resetowanie całego głosowania

## Zmiana portu

W `docker-compose.yml` zmień mapowanie portów dla serwisu `nginx`:

```yaml
services:
  nginx:
    ports:
      - "8080:80"
```

## Dane i reset

Stack nie montuje katalogów hosta do kontenerów. Baza danych jest przechowywana w nazwanym volume Docker `postgres_data`, a konfiguracja aplikacji pochodzi wyłącznie ze `stack.env`. Aplikacja buduje adres połączenia z `POSTGRES_DB`, `POSTGRES_USER` i `POSTGRES_PASSWORD`, więc te wartości muszą być spójne.

Jeśli istniejący volume został utworzony ze starym hasłem, zmiana `POSTGRES_PASSWORD` nie zmieni hasła w PostgreSQL. Aby zachować dane, ustaw w `stack.env` poprzednie hasło albo zmień hasło użytkownika z poziomu lokalnego socketu kontenera:

```bash
docker compose up -d db
docker compose exec -T db psql -U postgres -c \
  "ALTER USER filmoinator WITH PASSWORD 'NOWE_HASŁO_ZE_STACK_ENV';"
docker compose up -d --build --remove-orphans
```

Przy świadomym usunięciu danych można utworzyć bazę od nowa:

```bash
docker compose down -v
docker compose up -d --build
```

## Jak to działa

| Runda | Faza | Opis |
|---|---|---|
| 1 | Dodawanie filmów | Użytkownicy wyszukują i dodają filmy z TMDB |
| 1 | Głosowanie | Głosowanie, 3 najlepsze filmy przechodzą dalej |
| 2 | Głosowanie | Głosowanie na 3 filmy, 2 najlepsze przechodzą do finału |
| 3 | Głosowanie (finał) | Wybór zwycięskiego filmu |

Administrator steruje fazami z poziomu panelu administracyjnego.

## Technologie

- **Backend:** Python, Flask, SQLAlchemy, Gunicorn
- **Baza danych:** PostgreSQL 16
- **Serwer HTTP:** Nginx
- **API zewnętrzne:** TMDB (The Movie Database)
- **Konteneryzacja:** Docker, Docker Compose
