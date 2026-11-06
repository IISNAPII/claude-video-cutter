# Lessons

## 06.11.2026: Erster Windows-Lauf (work/kisocial)

Drei Inkompatibilitäten der Pipeline mit der aktuellen Windows-Umgebung. Für den Lauf mit Wrappern umgangen, Projektdateien nicht geändert. Dauerhafte Fixes stehen noch aus.

1. **QA (qa_stage_a.py) stürzt ab:** faster-whisper 1.2.1 ruft `av.open(..., metadata_errors=...)` auf, PyAV 19.0.2 kennt den Parameter nicht. `av` ist in requirements.txt nicht gepinnt. Fix-Vorschlag: `av` auf eine zu faster-whisper 1.2.1 passende Version pinnen oder Audio als numpy-Array statt Dateipfad an `model.transcribe` geben.
2. **QA unter Windows:** `os.unlink(f.name)` innerhalb des offenen `NamedTemporaryFile`-Blocks scheitert mit WinError 32. Fix-Vorschlag: Unlink hinter den `with`-Block ziehen.
3. **build_playback_proxy.py:** ffmpeg 9 hat `-vsync` entfernt. Fix-Vorschlag: `-fps_mode cfr`.
4. **cockpit_server.py / cutter_provider.py / cutter_render_jobs.py / sf_project.py** importieren `fcntl`, `pty`, `termios` (Unix-only). Das Cockpit startet unter Windows nicht. Für den Lauf mit Shim gestartet (flock via msvcrt, pty/termios als Stubs). Das eingebettete Agent-Terminal funktioniert damit nicht.

Regel daraus: Nach Updates von ffmpeg oder Python-Paketen einen kurzen Rauchtest (QA auf 1 Naht, Cockpit-Start) laufen lassen, bevor ein echtes Video geschnitten wird.

## 06.11.2026: Windows-Fixes angewendet (Punkte 1 bis 4 behoben)

1. `requirements.txt`: `av==18.1.0` gepinnt. Getestet: 16.1.0, 17.1.0 und 18.1.0 kennen `metadata_errors`, 19.x nicht. In `.venv312` installiert.
2. `qa_stage_a.py`: `os.unlink` steht jetzt hinter dem `with`-Block.
3. `-vsync` durch `-fps_mode` ersetzt in `build_playback_proxy.py`, `rerender.py` (Zeile 721) und `rebuild_sf.py` (Zeile 432). Kommentare in `cockpit_server.py` und `rerender.py` blieben unverändert.
4. Unix-Module: neues `scripts/posix_compat.py` (flock über msvcrt). `sf_project.py`, `cutter_render_jobs.py` und `cutter_provider.py` fallen unter Windows darauf zurück. `pty` und `termios` sind dort `None`. `cockpit_server.py` hatte die drei Imports ungenutzt, sie sind entfernt. Das eingebettete Agent-Terminal bleibt unter Windows deaktiviert.

Verifiziert ohne Hilfsskripte: QA auf 1 Naht (PASS), Proxy-Encode eines 10-s-Ausschnitts, Cockpit-Start auf Testport (HTTP 200), Dateisperre blockiert zweiten Zugriff. Nicht getestet: "Neu rendern" im Cockpit.

## 06.11.2026: Testlauf work/kisocial_test2 ohne Hilfsskripte

Fixes 1 bis 4 halten (QA, Proxy-Render, Playback-Proxy, Cockpit-Start laufen durch). Offen ist ein fünfter Punkt: **Datei-Kodierung**.

5. Fast alle Skripte schreiben und lesen mit `open(..., "w")` ohne `encoding`. Unter Windows ist das cp1252 (`transcribe_aai.py:50`, `:53`, `merge_decisions.py:52/70/79`, `solver_v5.py:128`, `qa_stage_a.py:130/133`, `qa_repair.py:103`, `generate_review.py:106`). Folgen:
   - `generate_review.py:106` stürzt ab (UnicodeEncodeError, Emoji in Zeile 53/58 nicht in cp1252). REVIEW-LISTE.md bleibt leer.
   - `cockpit_server.py:177` (`load_json`) liest mit `encoding="utf-8"` und scheitert an `words_aai.json` (Byte 0xFC = ü). `/api/state` liefert 500, das Cockpit zeigt 0 Segmente und "Quellvideo nicht erreichbar".
   - Der erste Lauf funktionierte nur, weil dort `PYTHONUTF8=1` gesetzt war.
   Fix-Vorschlag: überall `encoding="utf-8"` beim Öffnen von Textdateien (oder zentral `PYTHONUTF8=1` im Aufruf dokumentieren). Bereits mit cp1252 geschriebene Workdirs müssen danach einmal neu erzeugt oder konvertiert werden.

Regel daraus: Der Cockpit-Rauchtest muss `/api/state` prüfen (nicht nur die Startseite) und mit Umlaut-Daten laufen.

## 06.11.2026: Kodierung, Review-Liste, Setup und Terminal behoben

Testlauf work/kisocial_test4 lief ohne Hilfsskript, ohne PYTHONUTF8 und ohne Absturz durch (alle Dateien gültiges UTF-8, `/api/state` 200 mit Segmenten und Wörtern, Review-Liste gefüllt).

5. **Kodierung:** In 24 Dateien haben 67 Text-Aufrufe (`open`, `read_text`, `write_text`) jetzt `encoding="utf-8"`. Binärzugriffe sind unverändert.
6. **Logs:** Neues `scripts/utf8_console.py` stellt stdout und stderr auf UTF-8. Die 17 Einstiegsskripte importieren es als Erstes. Vorher schrieb Python bei umgeleiteter Ausgabe cp1252 (Emoji im print() hätte abgestürzt).
7. **Skills:** `video-cut-transkription/SKILL.md` öffnet Dateien jetzt mit `encoding='utf-8'` (Zeilen 60, 79, 94, 100).
8. **Gegenleser-Befunde:** `generate_review.py` filterte auf `vorschlag == "check"`, der Agent schreibt aber `"review"`. Jetzt zählen beide. Befunde ab Konfidenz 0.7 stehen im Feinschliff-Abschnitt, 0.4 bis 0.7 unter "Weniger sichere Gegenleser-Hinweise". Das Format ist in `video-cut-uebergabe/SKILL.md` beschrieben.
9. **cockpit_setup.py:** Neuer Parameter `--port <n>`. Ohne Angabe bleibt der Port aus `cockpit.json` erhalten (vorher stand fest 8766 im Code). Ohne `--src` meldet das Skript jetzt klar "Quellvideo fehlt" und nennt den Aufruf. Beim ersten Lauf ist `--src` Pflicht (im Skill dokumentiert).
10. **Eingebettetes Terminal unter Windows:** `cutter_provider.py` startet Claude dort über pywinpty (ConPTY, `pywinpty==3.1.2`, mit echtem Claude getestet). Der Codex-Start nutzt denselben Code, ist aber ungetestet. Der Unix-Pfad mit `pty.fork` ist unverändert. Beenden räumt den Prozessbaum mit `taskkill /T /F` ab. `cutter_claude_resume.py` kennt kein `SIGHUP` mehr unter Windows. `serve_term_stream` zeigt Startfehler (`OSError`) jetzt im Terminal statt als stumme 500.

Test: `.venv312/Scripts/python scripts/test_windows_compat.py` prüft (1) kein Text-open() ohne encoding, (2) utf8_console in den Einstiegsskripten, (3) das ConPTY-Terminal (starten, lesen, schreiben, Größe, Beenden, Exit-Code).

Nicht getestet: "Neu rendern" im Cockpit, `test_echo_clamp.py` (braucht Schnitte aus dem Cockpit), Codex-Terminal (Node-Bridge) unter Windows, tmux-Persistenz (gibt es unter Windows nicht).

Regel daraus: Neue Skripte öffnen Textdateien immer mit `encoding="utf-8"` und importieren `utf8_console` als Erstes. `test_windows_compat.py` fängt beides ab.
