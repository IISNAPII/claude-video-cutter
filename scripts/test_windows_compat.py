#!/usr/bin/env python3
"""Regressionstest für die Windows-Fixes (06.11.2026).

Prüft drei Dinge, die unter Windows still kaputtgingen:
1. Kein Text-open()/read_text()/write_text() ohne encoding (sonst cp1252 statt UTF-8,
   words_aai.json wird für das Cockpit unlesbar, Review-Liste bricht bei Emoji ab).
2. Die Einstiegsskripte importieren utf8_console (Logs mit Umlauten und Emoji).
3. Nur unter Windows: Das eingebettete Terminal läuft über pywinpty (ConPTY):
   starten, lesen, schreiben, Größe ändern, beenden.

Aufruf: .venv312/Scripts/python scripts/test_windows_compat.py
"""
import ast
import glob
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Aufrufe, die nichts mit Text-Dateien zu tun haben
SKIP_OWNERS = {"os", "Image", "av", "webbrowser", "urllib", "request", "tarfile", "zipfile",
               "gzip", "cv2", "sf", "wave", "subprocess", "io"}
ENTRY = ("broll_auftrag broll_brief broll_sync_pass build_playback_proxy captions_from_words "
         "clip_register cockpit_server cockpit_setup cut_v5 generate_review merge_decisions "
         "pause_map qa_repair qa_stage_a rerender solver_v5 transcribe_aai").split()
ergebnisse = []


def melde(name, ok, detail=""):
    ergebnisse.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (": " + detail if detail else ""))


def modus(call, attr_style):
    index = 0 if attr_style else 1
    if len(call.args) > index and isinstance(call.args[index], ast.Constant):
        return call.args[index].value
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return "?" if len(call.args) > index or any(k.arg == "mode" for k in call.keywords) else "r"


def text_oeffnen_ohne_encoding(pfad):
    quelle = open(pfad, encoding="utf-8").read()
    treffer = []
    for knoten in ast.walk(ast.parse(quelle)):
        if not isinstance(knoten, ast.Call):
            continue
        func = knoten.func
        if isinstance(func, ast.Name) and func.id == "open":
            name, attr = "open", False
        elif isinstance(func, ast.Attribute) and func.attr in ("open", "read_text", "write_text"):
            if isinstance(func.value, ast.Name) and func.value.id in SKIP_OWNERS:
                continue
            name, attr = func.attr, True
        else:
            continue
        if any(k.arg == "encoding" for k in knoten.keywords):
            continue
        m = modus(knoten, attr) if name == "open" else "r"
        if "b" in str(m):
            continue
        treffer.append("%s:%d" % (os.path.basename(pfad), knoten.lineno))
    return treffer


def test_encoding():
    offen = []
    for pfad in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        offen += text_oeffnen_ohne_encoding(pfad)
    melde("Text-open() immer mit encoding", not offen, ", ".join(offen[:8]))


def test_utf8_console():
    fehlt = [n for n in ENTRY
             if "import utf8_console" not in open(os.path.join(HERE, n + ".py"), encoding="utf-8").read()]
    melde("Einstiegsskripte importieren utf8_console", not fehlt, ", ".join(fehlt))


def test_conpty():
    if sys.platform != "win32":
        print("SKIP ConPTY-Terminal (nur Windows)")
        return
    import cutter_provider as cp
    crlf = bytes([13, 10])

    def builder(workdir, project_dir, provider, shortform=False):
        return cp.Launch(("cmd.exe", "/k", "echo BEREIT"), project_dir, dict(os.environ), provider)

    def warte(session, text, sekunden=8):
        ende = time.time() + sekunden
        while time.time() < ende:
            if text in session.buf:
                return True
            time.sleep(0.1)
        return False

    melde("pywinpty importierbar", cp.winpty is not None)
    if cp.winpty is None:
        return
    with tempfile.TemporaryDirectory() as workdir:
        manager = cp.TerminalManager(workdir, workdir, launch_builder=builder, resume_fallback=False)
        session = manager.start("claude", cols=100, rows=30)
        melde("Terminal startet unter ConPTY", session.alive and session.proc is not None)
        melde("Terminal liefert Ausgabe", warte(session, b"BEREIT"))
        melde("Terminal nimmt Eingabe an", session.write(b"echo ECHO123" + crlf) and warte(session, b"ECHO123"))
        session.resize(120, 40)
        melde("Fenstergröße änderbar", tuple(session.proc.getwinsize()) == (40, 120))
        manager.close()
        melde("close beendet die Session", not session.alive)
        zweite = manager.start("claude", cols=100, rows=30)
        warte(zweite, b"BEREIT")
        zweite.write(b"exit" + crlf)
        ende = time.time() + 8
        while zweite.alive and time.time() < ende:
            time.sleep(0.2)
        melde("regulärer Exit wird erkannt", not zweite.alive and zweite.exit_code == 0,
              "exit_code=%s" % zweite.exit_code)
        manager.close()


def main():
    test_encoding()
    test_utf8_console()
    test_conpty()
    ok = all(ergebnisse)
    print("=> GESAMT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
