# Tymczasowe plany robocze

Pliki w tym folderze to robocze plany implementacji - usuwane po skonczeniu
funkcjonalnosci i wpisaniu lekcji do `app/docs/`.

## Aktualne plany

### Anti-spam rejestracji (3 tiery)

| Plik | Status | Co zawiera |
|------|--------|------------|
| [plan-anti-spam-rejestracji.md](plan-anti-spam-rejestracji.md) | **Tier 1 - DONE 2026-05-10** | Honeypot field + Flask-Limiter + walidacja email regex. Lekcje: [app/docs/lekcje-anti-spam-tier1.md](../../app/docs/lekcje-anti-spam-tier1.md). Commit: `f1f9f07`. |
| (nowy) | **Tier 1.5 - do realizacji** | Auth na `/api/round/use` (krytyczna dziura: sabotaz limitu rund), rate limit na pozostalych 6 endpointach |
| [plan-anti-spam-tier2.md](plan-anti-spam-tier2.md) | Tier 2 - po Tier 1.5 | Email weryfikacja (Resend) + wlasna domena + Cloudflare WAF |
| [plan-anti-spam-tier3.md](plan-anti-spam-tier3.md) | Tier 3 - tylko jesli potrzebne | Cloudflare Turnstile (CAPTCHA) + blacklist disposable email |

**Kolejnosc**: Tier 1 -> obserwacja 2-4 tyg -> Tier 2 jesli widac problem ->
obserwacja 2-4 tyg -> Tier 3 jesli wciaz problem.

**Decyzje wymagane:**
- Tier 1: brak (lecimy)
- Tier 2: zakup domeny (~50zl/rok), wybor SMTP (Resend rekomendowany)
- Tier 3: tylko jesli logi pokazuja realny spam mimo Tier 1+2

## Po skonczeniu

Gdy plan jest zrealizowany:
1. Wnioski przeniesc do `app/docs/lekcje-anti-spam.md` (nowy plik)
2. Zaktualizowac `SECURITY.md` z nowymi mechanizmami
3. Usunac plik z tego folderu
4. Zaktualizowac ten README
