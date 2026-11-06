"""Stellt stdout und stderr auf UTF-8, damit Umlaute und Sonderzeichen in Logs stimmen.

Unter Windows nutzt Python für umgeleitete Ausgabe (> datei.log) cp1252.
Ein print() mit Emoji oder Gedankenstrich würde dann abstürzen oder
verstümmelte Logs schreiben. Dieses Modul ganz oben in Einstiegsskripten
importieren: `import utf8_console  # noqa: F401`
"""
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
