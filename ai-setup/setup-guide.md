# Jak skonfigurowac asystenta AI dla tego projektu

Ponizej instrukcje jak zaladowac zasady z `global-instructions.md` i `project-instructions.md`
do konkretnych narzedzi AI.

---

## Claude Code (CLI / VSCode extension)

Juz skonfigurowany. Czyta automatycznie:
- `~/.claude/CLAUDE.md` (globalne)
- `CLAUDE.md` w katalogu projektu (projektowe)

Nie trzeba nic robic.

---

## Cursor

1. Stworz plik `.cursorrules` w rocie projektu z trescia `project-instructions.md`.
2. Dla globalnych zasad: Cursor Settings -> Rules for AI -> wklej tresc `global-instructions.md`.

Alternatywnie mozna dodac plik `.cursor/rules/project.mdc`:
```
---
description: BeSafeFish project rules
alwaysApply: true
---
<tresc project-instructions.md>
```

---

## OpenCode (CLI)

OpenCode czyta plik `.opencode/instructions.md` w katalogu projektu (jesli istnieje)
oraz globalny plik `~/.config/opencode/instructions.md`.

Kroki:
1. Skopiuj `project-instructions.md` do `.opencode/instructions.md` w rocie projektu.
2. Skopiuj `global-instructions.md` do `~/.config/opencode/instructions.md` (lub dolacz do istniejacego).

---

## Aider

Aider czyta plik `.aider.conf.yml` oraz moze wczytac dodatkowe instrukcje przez `--read`.

Opcja 1 - dodaj do `.aider.conf.yml`:
```yaml
read:
  - ai-setup/project-instructions.md
  - ai-setup/global-instructions.md
```

Opcja 2 - uruchom z flagami:
```
aider --read ai-setup/project-instructions.md --read ai-setup/global-instructions.md
```

---

## GitHub Copilot (VSCode)

Stworz plik `.github/copilot-instructions.md` w rocie projektu z trescia `project-instructions.md`.
Dla globalnych zasad: VSCode Settings -> GitHub Copilot -> Custom Instructions -> wklej tresc `global-instructions.md`.

---

## ChatGPT / Gemini (web, bez integracji z repozytorium)

Wklej recznie na poczatku rozmowy:

```
Przeczytaj ponizsze instrukcje zanim zaczniesz prace:

[tresc global-instructions.md]

[tresc project-instructions.md]
```

Mozna tez zapisac jako "Custom Instructions" / "System prompt" w ustawieniach konta.

---

## Continue (VSCode extension)

Continue czyta plik `.continue/config.json`. Dodaj system prompt:

```json
{
  "systemMessage": "<tresc global-instructions.md i project-instructions.md>"
}
```

Lub uzyj bloku `rules` w `.continue/config.yaml`:
```yaml
rules:
  - ai-setup/project-instructions.md
```

---

## Ogolna zasada dla kazdego nowego narzedzia

Jesli twoje narzedzie AI ma opcje "system prompt", "custom instructions" lub "rules":
1. Wklej tresc `global-instructions.md` jako instrukcje globalne/uzytkownika.
2. Wklej tresc `project-instructions.md` jako instrukcje projektowe/workspace.

Jesli narzedzie czyta plik z dysku automatycznie - sprawdz jego dokumentacje jaka nazwe pliku obsluguje
i skopiuj tam odpowiedni plik z tego folderu.
