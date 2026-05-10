# Globalne zasady uzytkownika (wszystkie projekty)

Te instrukcje dotycza wszelkiej wspolpracy z AI - niezaleznie od projektu.

## Komunikacja

- Jezyk odpowiedzi: polski
- Bez emoji (chyba ze uzytkownik poprosil)
- Krotko i na temat
- Bez dlugich myslnikow (em-dash, en-dash). Uzyj zwyklego "-" lub rozdziel zdania kropka.

## Commity git

- Commit message po polsku
- Format: `<typ>: <opis>` np. `feat: dodanie logowania`, `fix: naprawa timeouta`
- Dozwolone typy: `feat`, `fix`, `refactor`, `docs`, `chore`
- NIE dodawaj adnotacji w stylu "Co-authored-by AI" ani podobnych

## Bezpieczenstwo (krytyczne)

- NIGDY nie commituj hasel, tokenow, kluczy API, connection stringow
- Sekrety tylko jako zmienne srodowiskowe lub w pliku .env (ktory jest w .gitignore)
- Przed kazdym commitem sprawdz czy nie ma wrazliwych danych
- Aplikacje klienckie (GUI, .exe, web frontend) NIGDY nie lacza sie bezposrednio z baza - zawsze przez API
- Nie czytaj plikow poza workspace projektu (~/.ssh, ~/.aws, ~/.gnupg itd.)

## Windows - specyfika

- Uzyj `py` zamiast `python` (problem z aliasem Windows Store)
- Python 3.14+: unikaj `\!` w stringach (SyntaxWarning)
