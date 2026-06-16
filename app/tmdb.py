import requests

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p/w342"


def search_movies(query, api_key, language="pl-PL"):
    url = f"{TMDB_BASE}/search/movie"
    params = {"query": query, "language": language, "page": 1}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("results", [])[:7]:
            results.append({
                "tmdb_id": item["id"],
                "title": item["title"],
                "year": item.get("release_date", "")[:4] if item.get("release_date") else "",
                "poster": f"{TMDB_IMAGE}{item['poster_path']}" if item.get("poster_path") else "",
                "rating": round(item.get("vote_average", 0), 1),
                "overview": item.get("overview", "")[:200],
            })
        return results
    except requests.RequestException:
        return []


def get_age_rating(tmdb_id, api_key):
    url = f"{TMDB_BASE}/movie/{tmdb_id}/release_dates"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()

        priority = {"PL": 0, "US": 1, "GB": 2, "DE": 3, "FR": 4}
        best = None
        best_prio = 999

        for country in data.get("results", []):
            code = country.get("iso_3166_1", "")
            prio = priority.get(code, 10)
            for release in country.get("release_dates", []):
                cert = release.get("certification", "")
                if cert and cert.strip():
                    if prio < best_prio:
                        best_prio = prio
                        best = cert

        return best or ""
    except requests.RequestException:
        return ""


def get_movie_details(tmdb_id, api_key, language="pl-PL"):
    url = f"{TMDB_BASE}/movie/{tmdb_id}"
    params = {"language": language}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=5)
        r.raise_for_status()
        data = r.json()
        return {
            "title": data.get("title", ""),
            "year": (data.get("release_date") or "")[:4],
            "poster": f"{TMDB_IMAGE}{data['poster_path']}" if data.get("poster_path") else "",
            "rating": round(data.get("vote_average", 0), 1),
            "overview": data.get("overview", ""),
        }
    except requests.RequestException:
        return None
