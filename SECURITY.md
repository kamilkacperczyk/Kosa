# Bezpieczenstwo — Kosa

## Zasady bezpieczenstwa projektu

### 1. NIGDY nie commituj wrazliwych danych

Do repo NIE WOLNO dodawac:
- Hasel, tokenow, kluczy API
- Connection stringow do baz danych
- Kluczy prywatnych (SSH, PEM, PFX)
- Danych logowania (login/haslo do czegokolwiek)
- Webhookow, adresow serwerow produkcyjnych

### 2. Jak przechowywac sekrety

- Uzyj pliku `.env` (jest w .gitignore — nie trafi do repo)
- Lub zmiennych srodowiskowych systemu
- Pliki `config.local.*` i `*.secret` sa automatycznie ignorowane

### 3. Pre-commit hook

Repo ma zainstalowany **pre-commit hook** ktory automatycznie:
- Skanuje kazdy commit pod katem hasel, tokenow, kluczy, connection stringow
- **Blokuje commit** jesli wykryje cos podejrzanego
- Pokazuje dokladnie ktory plik i jaka linia jest problemem

Hook jest w `.git/hooks/pre-commit`.

> **UWAGA**: Hook nie jest wersjonowany (`.git/hooks/` nie jest w repo).
> Kazdy kto klonuje repo, musi go skopiowac recznie lub uzyc skryptu `setup_hooks.sh`.

Obejscie (tylko w wyjatkowych sytuacjach, po weryfikacji ze to false positive):
```
git commit --no-verify
```

### 4. .gitignore

Plik `.gitignore` chroni przed przypadkowym dodaniem:
- `.env`, `.env.*` — pliki srodowiskowe
- `*.pem`, `*.key`, `*.p12`, `*.pfx` — klucze i certyfikaty
- `config.local.*`, `credentials.*`, `*.secret` — lokalna konfiguracja
- `id_rsa*` — klucze SSH

### 5. Branch protection (GitHub)

Branch `main` jest chroniony:
- Wymaga Pull Request (brak direct push)
- Zapobiega przypadkowemu nadpisaniu historii (force push disabled)

### 6. Co robic gdy wyciekna dane

Jesli przypadkowo scommitowales wrazliwe dane:

1. **NATYCHMIAST** zmien haslo/token/klucz ktory wyciekl
2. Usun dane z kodu i scommituj poprawke
3. Jesli dane trafily do historii Git — uzyj `git filter-branch` lub `BFG Repo Cleaner`
4. Sam commit z usunieciem NIE wystarczy — Git pamięta calą historię

### 7. Kontakt

Jesli znajdziesz problem bezpieczenstwa — zglos to przez prywatna wiadomosc do wlasciciela repo.
