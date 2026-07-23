import asyncio
import os
import sys
import threading
from pathlib import Path
from queue import Empty, Queue

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import MemoryEngine, wants_slides
import chatstore
import webbrowser

from nicegui import ui, run, app

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = MemoryEngine()
    return _engine


ICON_BRAND = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l2.35 6.26L21 10.6l-6.65 2.34L12 22l-2.35-9.06L3 10.6l6.65-2.34z"/></svg>'
ICON_PLUS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>'
ICON_SEND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>'
ICON_SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>'
ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8A8.4 8.4 0 0 1 12.5 3 8.4 8.4 0 0 1 21 11.5z"/></svg>'
ICON_GRAPH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="6" r="2.4"/><circle cx="19" cy="6" r="2.4"/><circle cx="12" cy="18" r="2.4"/><path d="M6.8 7.4l4 8.4M17.2 7.4l-4 8.4"/></svg>'
ICON_INGEST = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>'
ICON_INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/></svg>'
ICON_CLIP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;450;500;600&display=swap');
:root{ --accent:#e0906a; --accent-2:#c9704e; --text:#ececee; --text-2:rgba(236,236,238,0.60); --text-3:rgba(236,236,238,0.34);
  --glass:rgba(255,255,255,0.045); --glass-2:rgba(255,255,255,0.08); --stroke:rgba(255,255,255,0.09); --stroke-2:rgba(255,255,255,0.15); }
*{ font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif; box-sizing:border-box; }
html,body,#app,.q-page-container,.q-page,.nicegui-content{ margin:0; background:transparent !important; color:var(--text) !important; }
body{ background: radial-gradient(1100px 560px at 10% -10%, rgba(224,144,106,0.12), transparent 60%),
  radial-gradient(900px 520px at 105% 115%, rgba(120,130,255,0.09), transparent 55%), #0c0c0f !important; background-attachment:fixed; }
.nicegui-content{ padding:0 !important; gap:0 !important; }
::-webkit-scrollbar{ width:8px; height:8px; } ::-webkit-scrollbar-thumb{ background:rgba(255,255,255,0.12); border-radius:8px; }
::-webkit-scrollbar-thumb:hover{ background:rgba(255,255,255,0.22); }
.rail{ width:56px; height:100%; display:flex; flex-direction:column; align-items:center; padding:16px 0; gap:6px;
  background:rgba(255,255,255,0.02); backdrop-filter:blur(30px) saturate(140%); -webkit-backdrop-filter:blur(30px) saturate(140%); border-right:1px solid var(--stroke); }
.railmark{ width:32px; height:32px; border-radius:9px; background:linear-gradient(135deg,var(--accent),var(--accent-2)); display:flex; align-items:center; justify-content:center; margin-bottom:12px; box-shadow:0 4px 16px rgba(224,144,106,0.4); }
.railmark svg{ width:17px; height:17px; color:#fff; }
.railbtn{ width:40px; height:40px; border-radius:11px; display:flex; align-items:center; justify-content:center; color:var(--text-3); cursor:pointer; transition:all .14s; }
.railbtn:hover{ background:var(--glass); color:var(--text-2); } .railbtn.on{ background:var(--glass-2); color:var(--accent); } .railbtn svg{ width:20px; height:20px; }
.side{ width:280px; height:100%; display:flex; flex-direction:column; background:rgba(255,255,255,0.028);
  backdrop-filter:blur(30px) saturate(140%); -webkit-backdrop-filter:blur(30px) saturate(140%); border-right:1px solid var(--stroke); }
.newbtn{ margin:16px 16px 8px; padding:11px 14px; border-radius:13px; background:var(--glass-2); border:1px solid var(--stroke-2);
  color:var(--text); font-size:13.5px; font-weight:500; display:flex; align-items:center; gap:9px; cursor:pointer; transition:all .16s; }
.newbtn:hover{ background:rgba(255,255,255,0.13); border-color:rgba(255,255,255,0.22); transform:translateY(-1px); } .newbtn svg{ width:15px; height:15px; }
.scroll{ flex:1; overflow-y:auto; padding:4px 12px 16px; }
.sectitle{ color:var(--text-3); font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.12em; margin:14px 8px 7px; }
.scard{ padding:9px 12px; border-radius:11px; border:1px solid transparent; cursor:pointer; transition:all .14s; margin-bottom:2px; display:flex; align-items:center; gap:9px; }
.scard:hover{ background:var(--glass); border-color:var(--stroke); } .scard.on{ background:var(--glass); border-color:var(--stroke-2); }
.sdot{ width:6px; height:6px; border-radius:50%; background:var(--accent); flex-shrink:0; } .sdot.full{ background:var(--text-3); }
.stitle{ flex:1; min-width:0; font-size:12.5px; color:var(--text); font-weight:450; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.memcard{ padding:9px 12px; border-radius:11px; border:1px solid transparent; cursor:pointer; transition:all .14s; margin-bottom:2px; overflow:hidden; }
.memcard .memid,.memcard .memsum{ overflow:hidden; text-overflow:ellipsis; }
.memcard:hover{ background:var(--glass); border-color:var(--stroke); }
.memid{ font-size:12.5px; font-weight:500; color:var(--text); margin-bottom:2px; } .memsum{ font-size:11px; color:var(--text-3); line-height:1.4; }
.main{ flex:1; height:100%; display:flex; flex-direction:column; min-width:0; }
/* ---- live pipeline visualisation (replaces the opaque spinner) ---- */
.wf{ max-width:760px; margin:6px auto 2px; padding:15px 20px 12px; border-radius:16px;
  background:var(--glass); border:1px solid var(--stroke); backdrop-filter:blur(22px); animation:wfin .45s ease both; }
@keyframes wfin{ from{opacity:0; transform:translateY(10px)} to{opacity:1; transform:none} }
.wf-title{ font-size:10px; letter-spacing:.16em; text-transform:uppercase; color:var(--text-3); margin-bottom:13px; }
.wf-row{ display:flex; align-items:flex-start; }
.wf-step{ width:96px; display:flex; flex-direction:column; align-items:center; gap:6px; }
.wf-dot{ width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  border:1.5px solid var(--stroke-2); background:rgba(255,255,255,0.03); color:var(--text-3);
  font-size:12.5px; font-weight:600; transition:all .35s; }
.wf-step.active .wf-dot{ border-color:var(--accent); color:var(--accent); background:rgba(224,144,106,0.10);
  animation:wfpulse 1.35s ease-out infinite; }
.wf-step.done .wf-dot{ border-color:var(--accent); background:var(--accent); color:#fff; transform:scale(1.06); }
.wf-step.skip .wf-dot{ opacity:.35; border-style:dashed; }
.wf-step.fail .wf-dot{ border-color:#e07b7b; color:#e07b7b; background:rgba(224,123,123,0.12); }
@keyframes wfpulse{ 0%{box-shadow:0 0 0 0 rgba(224,144,106,.55)} 70%{box-shadow:0 0 0 13px rgba(224,144,106,0)} 100%{box-shadow:0 0 0 0 rgba(224,144,106,0)} }
.wf-label{ font-size:11.5px; color:var(--text-3); text-align:center; transition:color .3s; }
.wf-step.active .wf-label, .wf-step.done .wf-label{ color:var(--text); }
.wf-detail{ font-size:10px; color:var(--accent); text-align:center; line-height:1.3; min-height:26px;
  opacity:0; transform:translateY(-3px); transition:all .35s; max-width:94px; }
.wf-step.active .wf-detail, .wf-step.done .wf-detail, .wf-step.skip .wf-detail{ opacity:.85; transform:none; }
.wf-step.skip .wf-detail{ color:var(--text-3); }
.wf-conn{ flex:1; height:2px; margin-top:16px; background:var(--stroke); border-radius:2px; position:relative; overflow:hidden; }
.wf-conn::after{ content:""; position:absolute; left:0; top:0; height:100%; width:0; border-radius:2px;
  background:linear-gradient(90deg,var(--accent),#8b7bff); transition:width .6s cubic-bezier(.4,0,.2,1); }
.wf-conn.on::after{ width:100%; }
.chatinner{ max-width:760px; margin:0 auto; padding:32px 24px 12px; display:flex; flex-direction:column; gap:16px; width:100%; }
.row-u{ display:flex; justify-content:flex-end; } .row-a{ display:flex; justify-content:flex-start; }
.bubble-u, .bubble-a{ user-select:text; -webkit-user-select:text; cursor:text; }
.bubble-u{ background:var(--accent); color:#fff; padding:11px 15px; border-radius:19px 19px 6px 19px; max-width:78%; font-size:14px;
  line-height:1.55; white-space:pre-wrap; word-break:break-word; box-shadow:0 6px 20px rgba(224,144,106,0.28); }
.bubble-a{ background:var(--glass); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); border:1px solid var(--stroke); color:var(--text);
  padding:11px 15px; border-radius:19px 19px 19px 6px; max-width:78%; font-size:14px; line-height:1.6; white-space:pre-wrap; word-break:break-word; }
.welcome{ margin:auto; text-align:center; display:flex; flex-direction:column; align-items:center; gap:13px; padding-top:11vh; }
.welcome .wm{ width:54px; height:54px; border-radius:17px; background:linear-gradient(135deg,var(--accent),var(--accent-2)); display:flex; align-items:center; justify-content:center; box-shadow:0 12px 38px rgba(224,144,106,0.45); }
.welcome .wm svg{ width:28px; height:28px; color:#fff; } .welcome h2{ font-size:19px; font-weight:600; color:var(--text); margin:0; }
.welcome p{ font-size:13.5px; color:var(--text-3); margin:0; max-width:330px; line-height:1.5; }
.inputwrap{ padding:14px 24px 22px; }
.inputbar{ max-width:760px; margin:0 auto; display:flex; align-items:center; gap:8px; background:var(--glass-2);
  backdrop-filter:blur(24px) saturate(150%); -webkit-backdrop-filter:blur(24px) saturate(150%); border:1px solid var(--stroke-2);
  border-radius:18px; padding:6px 8px; box-shadow:0 10px 34px rgba(0,0,0,0.34); }
.inputbar .q-field, .inputbar .q-field__control, .inputbar .q-field__control::before, .inputbar .q-field__control::after{ background:transparent !important; box-shadow:none !important; border:none !important; }
.inputbar .q-field__control{ padding:0 8px !important; min-height:38px !important; } .inputbar .q-field__native{ color:var(--text) !important; font-size:14px !important; }
.sendbtn{ width:36px; height:36px; min-width:36px; border-radius:12px; background:var(--accent); display:flex; align-items:center; justify-content:center;
  cursor:pointer; transition:all .15s; box-shadow:0 4px 15px rgba(224,144,106,0.45); } .sendbtn:hover{ filter:brightness(1.08); transform:translateY(-1px); } .sendbtn svg{ width:17px; height:17px; color:#fff; }
.savebtn{ color:var(--text-3); font-size:12px; cursor:pointer; padding:0 8px; transition:color .15s; } .savebtn:hover{ color:var(--text-2); }
.capnote{ max-width:760px; margin:0 auto 8px; text-align:center; color:var(--text-3); font-size:12.5px; }
.spinoff{ max-width:760px; margin:0 auto; padding:13px 18px; border-radius:16px; background:var(--accent); color:#fff; font-size:14px; font-weight:500;
  display:flex; align-items:center; justify-content:center; gap:9px; cursor:pointer; transition:all .15s; box-shadow:0 8px 26px rgba(224,144,106,0.4); }
.spinoff:hover{ filter:brightness(1.08); transform:translateY(-1px); } .spinoff svg{ width:16px; height:16px; }
.formwrap{ max-width:640px; margin:0 auto; padding:44px 24px; width:100%; display:flex; flex-direction:column; gap:14px; }
.formtitle{ font-size:20px; font-weight:600; color:var(--text); } .formsub{ font-size:13px; color:var(--text-3); margin:-6px 0 6px; }
.glassfield{ background:var(--glass); border:1px solid var(--stroke); border-radius:14px; padding:2px 12px; }
.glassfield .q-field__control, .glassfield .q-field__control::before, .glassfield .q-field__control::after{ background:transparent !important; box-shadow:none !important; border:none !important; }
.glassfield .q-field__native, .glassfield textarea{ color:var(--text) !important; font-size:14px !important; }
.primarybtn{ margin-top:6px; padding:12px 18px; border-radius:14px; background:var(--accent); color:#fff; font-weight:500; font-size:14px;
  display:flex; align-items:center; justify-content:center; gap:8px; cursor:pointer; transition:all .15s; box-shadow:0 8px 24px rgba(224,144,106,0.4); }
.primarybtn:hover{ filter:brightness(1.08); transform:translateY(-1px); } .primarybtn svg{ width:16px; height:16px; }
.q-dialog .dlgcard{ background:rgba(22,22,26,0.86) !important; backdrop-filter:blur(34px) saturate(140%); -webkit-backdrop-filter:blur(34px) saturate(140%);
  border:1px solid var(--stroke-2) !important; border-radius:18px !important; color:var(--text) !important; }
.spin{ width:34px; height:20px; display:flex; align-items:center; gap:5px; padding-left:4px; }
.spin i{ width:7px; height:7px; border-radius:50%; background:var(--text-3); animation:bp 1.2s infinite ease-in-out; }
.spin i:nth-child(2){ animation-delay:.2s } .spin i:nth-child(3){ animation-delay:.4s }
@keyframes bp{ 0%,60%,100%{ transform:translateY(0); opacity:.4 } 30%{ transform:translateY(-5px); opacity:1 } }
.clipbtn{ width:34px; height:34px; min-width:34px; border-radius:11px; display:flex; align-items:center; justify-content:center; color:var(--text-3); cursor:pointer; transition:all .14s; }
.clipbtn:hover{ background:var(--glass); color:var(--accent); } .clipbtn svg{ width:16px; height:16px; }
.attchip{ display:flex; gap:7px; align-items:center; padding:5px 11px; border-radius:11px; background:var(--glass); border:1px solid var(--stroke); font-size:11.5px; color:var(--text-2); }
</style>
"""

BRANCH_ORDER = ["owner", "sources", "learnings", "past-chats", "rules"]
GRAPH_COLORS = ["#8b7bff", "#e0906a", "#7bd0a0", "#e07b9a", "#7ba7d0"]


def _docx_text(data):
    """Text from a .docx without extra dependencies: it's a zip, paragraphs live
    in word/document.xml as w:t runs."""
    import zipfile
    from io import BytesIO
    from xml.etree import ElementTree
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with zipfile.ZipFile(BytesIO(data)) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    paras = ("".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p"))
    return "\n".join(p for p in paras if p.strip())


def extract_text_from_path(path):
    """Text from a local .pdf / .docx / .txt / .md file. Native app -> files are
    read straight from disk; no browser upload involved."""
    p = Path(path.strip().strip('"'))
    if not p.is_file():
        raise FileNotFoundError(f"Not a file: {p}")
    data = p.read_bytes()
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        from io import BytesIO
        from pypdf import PdfReader
        return p.name, "\n".join((page.extract_text() or "") for page in PdfReader(BytesIO(data)).pages)
    if suffix == ".docx":
        return p.name, _docx_text(data)
    if suffix in (".txt", ".md", ".markdown"):
        return p.name, data.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type '{suffix}' - use .pdf, .docx, .txt or .md")


async def pick_file():
    """Native OS file dialog (pywebview). Returns a path or None (e.g. browser mode)."""
    try:
        files = await app.native.main_window.create_file_dialog(
            allow_multiple=False,
            file_types=("Documents (*.pdf;*.docx;*.txt;*.md)", "All files (*.*)"),
        )
    except Exception:
        return None
    return files[0] if files else None


@ui.page("/")
def main_page():
    ui.add_head_html(CSS)
    ui.dark_mode(value=True)
    engine = get_engine()
    refs = {"welcome": True, "view": "chat"}

    engine.set_session(chatstore.new_session())  # every launch starts fresh

    # ---------- shared ----------
    def refresh_current():
        render_sidebar() if refs["view"] == "chat" else render_content()

    def open_memory(m):
        m = engine.get_memory(m["id"]) or m
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("min-width:560px;max-width:720px;gap:8px;padding:22px"):
            ui.label(m["id"]).style("font-weight:600;font-size:15px")
            ui.label(f'{m["branch"]}  ·  {m.get("type", "")}').style("font-size:10px;color:var(--accent);text-transform:uppercase;letter-spacing:.06em;font-weight:600")
            ui.html('<div style="height:1px;background:var(--stroke);margin:4px 0 6px"></div>')
            editor = ui.textarea(value=m["body"]).props("borderless dark").classes("glassfield").style("min-height:150px;width:100%")
            links = m.get("links") or []
            if links:
                ui.html('<div class="formsub" style="margin:2px 0 0">links</div>')
                ui.label(", ".join(f"{to} ({t})" for to, t in links)).style("font-size:11px;color:var(--text-3)")
            traces = m.get("found_by") or []
            if traces:
                ui.html('<div class="formsub" style="margin:2px 0 0">patikalar (bunlarla bulundu)</div>')
                with ui.row().style("gap:6px;flex-wrap:wrap"):
                    for ti, t in enumerate(traces):
                        with ui.element("div").classes("attchip"):
                            ui.label(t[:44])
                            rm = ui.label("×").style("cursor:pointer;opacity:.65")

                            def kill(e, mid=m["id"], idx=ti):
                                engine.remove_trace(mid, idx)
                                dlg.close()
                                refresh_current()
                                ui.notify("Patika silindi")

                            rm.on("click", kill)
            with ui.row().style("align-self:flex-end;gap:14px;align-items:center;margin-top:6px"):
                if m["id"] == "owner" and m["branch"] == "owner":
                    async def do_split():
                        dlg.close()
                        note = ui.notification("Analyzing the owner profile…", spinner=True, timeout=None)
                        try:
                            res = await run.io_bound(engine.analyze_owner)
                        except Exception as ex:
                            note.dismiss()
                            ui.notify(f"Analyze failed: {ex}", type="negative")
                            return
                        note.dismiss()
                        if not res:
                            ui.notify("Owner memory not found", type="negative")
                            return
                        open_owner_split(res)

                    with ui.element("div").classes("savebtn").style("color:var(--accent)").on("click", do_split):
                        ui.label("Split into aspects")

                def do_delete():
                    engine.delete_memory(m["id"])
                    dlg.close()
                    refresh_current()
                    ui.notify("Deleted")

                def do_save():
                    engine.update_memory(m["id"], editor.value)
                    dlg.close()
                    refresh_current()
                    ui.notify("Saved")

                with ui.element("div").classes("savebtn").style("color:#e07b7b").on("click", do_delete):
                    ui.label("Delete")
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Cancel")
                with ui.element("div").classes("newbtn").style("margin:0").on("click", do_save):
                    ui.label("Save")
        dlg.open()

    def open_owner_split(res):
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:720px;max-width:92vw;gap:0;padding:0"):
            with ui.element("div").style("padding:22px 24px 12px;border-bottom:1px solid var(--stroke)"):
                ui.label("Split owner into aspects").style("font-weight:600;font-size:16px")
                ui.label("owner.md keeps the distilled core; each aspect becomes its own memory (part-of owner). Edit anything, then save.").style("font-size:12px;color:var(--text-3);margin-top:3px")
            editors = {}
            with ui.scroll_area().style("height:52vh;padding:2px 24px 8px"):
                ui.label("core (stays in owner.md)").style("display:block;font-weight:600;font-size:12px;color:var(--accent);margin:14px 0 6px")
                core_in = ui.textarea(value=res["core"]).props("borderless dark autogrow").classes("glassfield").style("width:100%")
                for cat, body in res["aspects"].items():
                    ui.label(cat).style("display:block;font-weight:600;font-size:12px;color:var(--accent);text-transform:capitalize;margin:16px 0 6px")
                    editors[cat] = ui.textarea(value=body).props("borderless dark autogrow").classes("glassfield").style("width:100%")
            with ui.row().style("padding:12px 24px;border-top:1px solid var(--stroke);justify-content:flex-end;gap:14px;align-items:center;width:100%"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Cancel")

                async def do_split_save():
                    aspects = {c: e.value for c, e in editors.items() if e.value.strip()}
                    await run.io_bound(engine.save_owner_aspects, core_in.value.strip(), aspects)
                    dlg.close()
                    refresh_current()
                    ui.notify("Owner split into aspects")

                with ui.element("div").classes("newbtn").style("margin:0").on("click", do_split_save):
                    ui.label("Split & save")
        dlg.open()

    # ---------- chat view ----------
    def render_sidebar():
        refs["side"].clear()
        with refs["side"]:
            sessions = chatstore.list_sessions()
            ui.html('<div class="sectitle">history</div>')
            if not sessions:
                ui.html('<div class="memsum" style="padding:4px 8px">No past chats yet.</div>')
            for s in sessions:
                on = " on" if engine.session and s["id"] == engine.session["id"] else ""
                card = ui.element("div").classes(f"scard{on}")
                with card:
                    ui.html(f'<div class="sdot {"full" if s["status"] == "full" else ""}"></div>')
                    ui.html(f'<div class="stitle">{s["title"]}</div>')
                card.on("click", lambda e, sid=s["id"]: switch_session(sid))

    def add_bubble(text, user):
        if refs["welcome"]:
            refs["chatcol"].clear()
            refs["welcome"] = False
        with refs["chatcol"]:
            with ui.element("div").classes("row-u" if user else "row-a"):
                ui.label(text).classes("bubble-u" if user else "bubble-a")
        refs["chatsa"].scroll_to(percent=1.0)

    def render_chat():
        refs["chatcol"].clear()
        msgs = engine.session.get("messages", []) if engine.session else []
        if not msgs:
            refs["welcome"] = True
            with refs["chatcol"]:
                with ui.element("div").classes("welcome"):
                    ui.html(f'<div class="wm">{ICON_BRAND}</div>')
                    ui.html("<h2>Your memory</h2>")
                    ui.html("<p>Ask anything grounded in what you've saved, or open a memory on the left.</p>")
        else:
            refs["welcome"] = False
            with refs["chatcol"]:
                for m in msgs:
                    with ui.element("div").classes("row-u" if m["role"] == "user" else "row-a"):
                        ui.label(m["content"]).classes("bubble-u" if m["role"] == "user" else "bubble-a")
        rebuild_input()

    async def do_research():
        q = (refs["inp"].value or "").strip()
        if not q:
            return
        refs["inp"].value = ""
        add_bubble(q, True)
        wf = build_workflow(RESEARCH_STEPS, "internette araştırma")
        pq, DONE = Queue(), object()
        out = {"res": None, "err": None}

        def worker():
            try:
                out["res"] = engine.research_answer(q, progress=lambda s, st, d="": pq.put((s, st, d)))
            except Exception as ex:
                out["err"] = str(ex)
            finally:
                pq.put(DONE)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            try:
                item = pq.get_nowait()
            except Empty:
                await asyncio.sleep(0.08)
                continue
            if item is DONE:
                break
            wf_set(wf, item[0], item[1], item[2])
            refs["chatsa"].scroll_to(percent=1.0)

        if out["err"]:
            ui.notify(f"Araştırma başarısız: {out['err']}", type="negative")
            return
        res = out["res"] or {}
        src = f'\n\n[araştırma · {res["source"]}]' if res.get("source") else ""
        add_bubble(res.get("answer", "Sonuç alınamadı.") + src, False)

    def rebuild_input():
        refs["inputwrap"].clear()
        with refs["inputwrap"]:
            if engine.session_full():
                ui.html('<div class="capnote">This chat reached its limit.</div>')
                with ui.element("div").classes("spinoff").style("margin-bottom:8px;background:var(--glass-2);color:var(--text);box-shadow:none;border:1px solid var(--stroke-2)").on("click", save_chat):
                    ui.label("Review memories from this chat")
                with ui.element("div").classes("spinoff").on("click", spinoff):
                    ui.html(ICON_PLUS)
                    ui.label("Start a new chat with this context")
            else:
                atts = (engine.session or {}).get("attachments") or []
                if atts:
                    with ui.element("div").style("max-width:760px;margin:0 auto 8px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap"):
                        for i, a in enumerate(atts):
                            with ui.element("div").classes("attchip"):
                                ui.label(a.get("name", "doc")[:30])
                                rm = ui.label("×").style("cursor:pointer;opacity:.65;font-size:13px")
                                rm.on("click", lambda e, idx=i: remove_attachment(idx))
                with ui.element("div").classes("inputbar"):
                    with ui.element("div").classes("clipbtn").on("click", open_attach):
                        ui.html(ICON_CLIP)
                    refs["inp"] = ui.input(placeholder="Sor, ya da 🔎 ile internette araştır...").props("borderless dense dark").classes("flex-grow").on("keydown.enter", send)
                    with ui.element("div").classes("savebtn").on("click", save_chat):
                        ui.label("Save")
                    with ui.element("div").classes("savebtn").style("padding:0 10px").on("click", do_research):
                        ui.html(ICON_SEARCH)
                    with ui.element("div").classes("sendbtn").on("click", send):
                        ui.html(ICON_SEND)

    def remove_attachment(idx):
        atts = engine.session.get("attachments") or []
        if 0 <= idx < len(atts):
            atts.pop(idx)
            chatstore.save_session(engine.session)
        rebuild_input()

    def open_attach():
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("min-width:540px;gap:10px;padding:22px"):
            ui.label("Attach a document to this chat").style("font-weight:600;font-size:15px")
            ui.label("PDF, DOCX, TXT or MD. Its text is given to the assistant for this session only - it is not saved to memory.").style("font-size:12px;color:var(--text-3)")

            async def attach():
                raw = (path_in.value or "").strip()
                if not raw:
                    return
                try:
                    name, text = await run.io_bound(extract_text_from_path, raw)
                except Exception as ex:
                    ui.notify(f"Could not read file: {ex}", type="negative")
                    return
                if not text.strip():
                    ui.notify("No readable text in that file", type="negative")
                    return
                engine.session.setdefault("attachments", []).append({"name": name, "text": text[:20000]})
                chatstore.save_session(engine.session)
                dlg.close()
                rebuild_input()
                ui.notify(f"Attached: {name}")

            async def browse():
                path = await pick_file()
                if path:
                    path_in.value = str(path)

            with ui.element("div").classes("inputbar").style("box-shadow:none;margin:2px 0"):
                path_in = ui.input(placeholder="File path (e.g. D:\\docs\\notes.pdf)").props("borderless dense dark").classes("flex-grow").on("keydown.enter", attach)
                with ui.element("div").classes("savebtn").on("click", browse):
                    ui.label("Browse")
            with ui.row().style("align-self:flex-end;gap:14px;align-items:center"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Cancel")
                with ui.element("div").classes("newbtn").style("margin:0").on("click", attach):
                    ui.label("Attach")
        dlg.open()

    def show_deck_card(res):
        """Result card for a generated deck: open the animated HTML or the editable pptx."""
        deck = res["deck"]
        with refs["chatcol"]:
            with ui.element("div").classes("row-a"):
                with ui.element("div").classes("bubble-a").style("width:100%"):
                    ui.label(f'📊  {deck["title"]}').style("font-weight:600;font-size:14.5px")
                    if deck.get("subtitle"):
                        ui.label(deck["subtitle"]).style("font-size:12px;color:var(--text-3);margin-top:2px")
                    ui.label(f'{len(deck["slides"])} slayt · hafızandan üretildi').style(
                        "font-size:11.5px;color:var(--accent);margin-top:6px")
                    with ui.row().style("gap:10px;margin-top:10px;align-items:center"):
                        with ui.element("div").classes("newbtn").style("margin:0;padding:7px 12px;font-size:12.5px") \
                                .on("click", lambda: webbrowser.open(Path(res["html"]).as_uri())):
                            ui.label("Sunumu aç (animasyonlu)")
                        if res.get("pptx"):
                            with ui.element("div").classes("savebtn").style("padding:7px 12px;font-size:12.5px") \
                                    .on("click", lambda: os.startfile(res["pptx"])):
                                ui.label("PPTX")
        refs["chatsa"].scroll_to(percent=1.0)

    WF_STEPS = [("triage", "Ayrıştır"), ("plan", "Planla"), ("research", "Araştır"),
                ("gather", "Topla"), ("structure", "Yapılandır"), ("render", "Oluştur")]
    RESEARCH_STEPS = [("search", "Kaynak ara"), ("read", "Oku"), ("answer", "Damıt")]

    def build_workflow(steps=None, title="canlı akış"):
        """Live pipeline strip: each stage lights up as the engine actually reaches it,
        connectors fill behind it. Shows the system thinking instead of hiding it."""
        steps = steps or WF_STEPS
        wf = {}
        with refs["chatcol"]:
            with ui.element("div").classes("wf"):
                ui.html(f'<div class="wf-title">{title}</div>')
                with ui.element("div").classes("wf-row"):
                    for i, (key, label) in enumerate(steps):
                        if i:
                            wf[f"conn{i - 1}"] = ui.element("div").classes("wf-conn")
                        step = ui.element("div").classes("wf-step")
                        with step:
                            with ui.element("div").classes("wf-dot"):
                                num = ui.label(str(i + 1))
                            ui.label(label).classes("wf-label")
                            det = ui.label("").classes("wf-detail")
                        wf[key] = {"step": step, "num": num, "detail": det, "idx": i}
        refs["chatsa"].scroll_to(percent=1.0)
        return wf

    def wf_set(wf, key, status, detail=""):
        r = wf.get(key)
        if not r:
            return
        r["step"].classes(replace=f"wf-step {status}".strip())
        if detail:
            r["detail"].text = detail
        if status in ("done", "skip"):
            r["num"].text = "✓" if status == "done" else "–"
            conn = wf.get(f"conn{r['idx']}")
            if conn:
                conn.classes(add="on")
        elif status == "fail":
            r["num"].text = "!"

    async def make_deck(q):
        wf = build_workflow()
        pq, DONE = Queue(), object()
        out = {"res": None, "err": None}

        def worker():
            try:
                out["res"] = engine.handle(q, progress=lambda s, st, d="": pq.put((s, st, d)))
            except Exception as ex:
                out["err"] = str(ex)
            finally:
                pq.put(DONE)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            try:
                item = pq.get_nowait()
            except Empty:
                await asyncio.sleep(0.08)
                continue
            if item is DONE:
                break
            wf_set(wf, item[0], item[1], item[2])
            refs["chatsa"].scroll_to(percent=1.0)

        if out["err"]:
            ui.notify(f"Sunum başarısız: {out['err']}", type="negative")
            return
        if not out["res"]:
            add_bubble("Sunumu üretemedim — model geçerli bir yapı vermedi. Konuyu biraz daha net yazar mısın?", False)
            return
        show_deck_card(out["res"])

    async def send():
        q = refs["inp"].value.strip()
        if not q:
            return
        refs["inp"].value = ""
        add_bubble(q, True)
        if wants_slides(q):                 # rule-based tool routing (not the weak model's call)
            await make_deck(q)
            return
        with refs["chatcol"]:
            with ui.element("div").classes("row-a"):
                bubble = ui.label("...").classes("bubble-a")
        refs["chatsa"].scroll_to(percent=1.0)

        stream_q = Queue()
        DONE = object()

        def worker():
            try:
                for tok in engine.answer_stream(q):
                    stream_q.put(tok)
            finally:
                stream_q.put(DONE)

        threading.Thread(target=worker, daemon=True).start()
        acc = ""
        while True:
            try:
                item = stream_q.get_nowait()
            except Empty:
                await asyncio.sleep(0.02)
                continue
            if item is DONE:
                break
            acc += item
            bubble.set_text(acc)
            refs["chatsa"].scroll_to(percent=1.0)

        chatstore.save_session(engine.session)
        render_sidebar()
        if engine.session_full():
            rebuild_input()

    def new_chat():
        engine.set_session(chatstore.new_session())
        render_chat()
        render_sidebar()

    def switch_session(sid):
        engine.set_session(chatstore.load_session(sid))
        render_chat()
        render_sidebar()

    async def spinoff():
        draft = await run.io_bound(engine.draft_consolidation)
        engine.set_session(chatstore.new_session(seed_context=draft))
        render_chat()
        render_sidebar()
        ui.notify("New chat started with the previous context")

    async def save_chat():
        """Reflection loop: the model proposes summary/decisions/lessons/owner updates;
        the owner edits, unchecks, and approves - only then anything is written."""
        if not engine.session or not engine.session.get("messages"):
            ui.notify("Nothing to save yet.")
            return
        note = ui.notification("Reflecting on this chat…", spinner=True, timeout=None)
        try:
            prop = await run.io_bound(engine.propose_reflection)
        except Exception as ex:
            note.dismiss()
            ui.notify(f"Reflection failed: {ex}", type="negative")
            return
        note.dismiss()

        rows = []
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:680px;max-width:92vw;gap:6px;padding:22px"):
            ui.label("Here's what I'd remember - approve or edit").style("font-weight:600;font-size:15px")
            ui.html('<div class="formsub">Chat summary -> memory (past-chats)</div>')
            sum_in = ui.textarea(value=prop["summary"]).props("borderless dark autogrow").classes("glassfield").style("width:100%")
            ui.html('<div class="formsub">Decisions (one per line)</div>')
            dec_in = ui.textarea(value="\n".join(f"- {d}" for d in prop["decisions"]) or "- none").props("borderless dark autogrow").classes("glassfield").style("width:100%")

            def proposal_rows(title, items, kind):
                ui.html(f'<div class="formsub" style="margin-top:6px">{title}</div>')
                if not items:
                    ui.label("none proposed").style("font-size:12px;color:var(--text-3)")
                for it in items:
                    with ui.row().style("align-items:center;gap:8px;width:100%;flex-wrap:nowrap"):
                        cb = ui.checkbox(value=True).props("dark dense size=xs")
                        inp = ui.input(value=it).props("borderless dense dark").classes("glassfield flex-grow")
                    rows.append((kind, cb, inp))

            proposal_rows("Lessons -> learnings branch", prop["lessons"], "lesson")
            proposal_rows("About you -> owner memory", prop["owner"], "owner")
            if prop.get("rules"):
                proposal_rows("Rule change -> rules/scoring.md", prop["rules"], "rule")

            with ui.row().style("align-self:flex-end;gap:14px;align-items:center;margin-top:8px"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Cancel")

                async def do_save():
                    lessons = [i.value.strip() for k, c, i in rows if k == "lesson" and c.value and i.value.strip()]
                    owner_u = [i.value.strip() for k, c, i in rows if k == "owner" and c.value and i.value.strip()]
                    rules_a = [i.value.strip() for k, c, i in rows if k == "rule" and c.value and i.value.strip()]
                    decisions = [l.strip().lstrip("-*• ").strip() for l in dec_in.value.splitlines()
                                 if l.strip().lstrip("-*• ").strip().lower() not in ("", "none")]
                    report = await run.io_bound(engine.save_reflection, sum_in.value.strip(), decisions, lessons, owner_u, rules_a)
                    dlg.close()
                    refresh_current()
                    ui.notify("Saved: " + ("; ".join(report) if report else "nothing selected"))

                with ui.element("div").classes("newbtn").style("margin:0").on("click", do_save):
                    ui.label("Save selected")
        dlg.open()

    def build_chat_view():
        with refs["content"]:
            with ui.row().classes("h-full no-wrap gap-0").style("flex:1;min-width:0"):
                with ui.element("div").classes("side"):
                    with ui.element("div").classes("newbtn").on("click", new_chat):
                        ui.html(ICON_PLUS)
                        ui.label("New chat")
                    refs["side"] = ui.element("div").classes("scroll")
                with ui.element("div").classes("main"):
                    with ui.scroll_area().classes("flex-grow w-full") as sa:
                        refs["chatsa"] = sa
                        refs["chatcol"] = ui.element("div").classes("chatinner")
                    refs["inputwrap"] = ui.element("div").classes("inputwrap")
        render_sidebar()
        render_chat()

    # ---------- graph view ----------
    async def health_test():
        note = ui.notification("Saklambaç: her memory kendini arıyor…", spinner=True, timeout=None)
        try:
            rep = await run.io_bound(engine.self_test)
        except Exception as ex:
            note.dismiss()
            ui.notify(f"Test failed: {ex}", type="negative")
            return
        note.dismiss()
        lost = [e for e in rep["results"] if not e["found"]]
        repair_rows = []
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:720px;max-width:92vw;gap:8px;padding:22px"):
            ui.label(f"Bulunabilirlik sağlığı: %{rep['score']}").style("font-weight:600;font-size:17px")
            ui.html('<div class="formsub">Her memory, gövdesinin özüyle arandı - kendini ilk 3\'te bulmalı.</div>')
            with ui.scroll_area().style("max-height:46vh"):
                for e in rep["results"]:
                    color = "var(--text-2)" if e["found"] else "#e0b06a"
                    mark = "✓" if e["found"] else "✗"
                    ui.label(f'{mark}  {e["id"]}  ·  sıra {e["rank"]}').style(f"font-size:12.5px;color:{color}")
                if lost:
                    ui.html('<div class="formsub" style="margin-top:10px;color:#e0b06a">Kayıp düğümler - onarım soruları ("/" ile ayrılır; düzenle, onayla)</div>')
                    for e in lost:
                        ui.label(e["id"]).style("font-size:12px;font-weight:500;margin-top:6px")
                        inp = ui.input(value=" / ".join(e["questions"])).props("borderless dense dark").classes("glassfield").style("width:100%")
                        repair_rows.append((e["id"], inp))
            with ui.row().style("align-self:flex-end;gap:14px;align-items:center"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Kapat")

                if lost:
                    async def do_repair():
                        fixed = []
                        for mid, inp in repair_rows:
                            qs = [q.strip() for q in (inp.value or "").split("/") if q.strip()]
                            if not qs:
                                continue
                            r = await run.io_bound(engine.repair_memory, mid, qs)
                            if r:
                                fixed.append(f"{mid.split('-')[-1]}: sıra {r[0]} → {r[1]}")
                        dlg.close()
                        refresh_current()
                        ui.notify("Onarıldı: " + ("; ".join(fixed) if fixed else "değişiklik yok"))

                    with ui.element("div").classes("newbtn").style("margin:0").on("click", do_repair):
                        ui.label("Onar")
        dlg.open()

    async def consolidate_ui():
        note = ui.notification("Konsolidasyon: saklambaç + otomatik onarım + çelişki/budama taraması…", spinner=True, timeout=None)
        try:
            rep = await run.io_bound(engine.run_consolidation)
        except Exception as ex:
            note.dismiss()
            ui.notify(f"Konsolidasyon başarısız: {ex}", type="negative")
            return
        note.dismiss()
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:680px;max-width:92vw;gap:8px;padding:22px"):
            ui.label(f"Konsolidasyon tamam — sağlık %{rep['health_before']} → %{rep['health_after']}").style("font-weight:600;font-size:16px")
            with ui.scroll_area().style("max-height:52vh"):
                if rep["repaired"]:
                    ui.html('<div class="formsub" style="margin-top:6px">Otomatik onarılan düğümler</div>')
                    for r in rep["repaired"]:
                        ui.label(f'  {r["id"]}: sıra {r["old_rank"]} → {r["new_rank"]}').style("font-size:12px;color:var(--text-2)")
                else:
                    ui.html('<div class="formsub" style="margin-top:6px">Onarım gerekmedi — her düğüm bulunabilir.</div>')
                if rep["conflicts"]:
                    ui.html('<div class="formsub" style="margin-top:10px;color:#e0b06a">Olası çelişki / tekrar (owner uzlaştırmalı)</div>')
                    for c in rep["conflicts"]:
                        ui.label(f'  {c["a"]}  ↔  {c["b"]}   (benzerlik {c["sim"]})').style("font-size:12px;color:var(--text-2)")
                if rep["prunable"]:
                    ui.html('<div class="formsub" style="margin-top:10px">Budama adayları (düşük önem + uzun kullanılmamış)</div>')
                    for p in rep["prunable"]:
                        ui.label(f'  {p["id"]}   (önem {p["imp"]}, aktiflik {p["act"]})').style("font-size:12px;color:var(--text-3)")
                pol = rep.get("policy") or {}
                if pol:
                    ui.html('<div class="formsub" style="margin-top:10px">Retrieval politikası (self-tune)</div>')
                    ui.label(f'  rel_floor = {pol.get("rel_floor")}   ·   {pol.get("reason", "")}').style("font-size:12px;color:var(--text-2)")
                if rep.get("gate"):
                    ui.html('<div class="formsub" style="margin-top:10px">Validation gate (held-out kontrol)</div>')
                    ui.label(f'  {rep["gate"]}').style("font-size:12px;color:var(--text-2)")

            def close_refresh():
                dlg.close()
                refresh_current()

            with ui.row().style("align-self:flex-end;margin-top:6px"):
                with ui.element("div").classes("newbtn").style("margin:0").on("click", close_refresh):
                    ui.label("Kapat")
        dlg.open()

    async def learn_ability_ui():
        state = {}
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:640px;max-width:92vw;gap:8px;padding:22px"):
            ui.label("Yeni yetenek öğren").style("font-weight:600;font-size:16px")
            ui.html('<div class="formsub">Bir beceri/metod konusu yaz (ör. "hisse temel analizi"). Sistem internetten '
                    'araştırıp metodu damıtır; onaylarsan beyne kalıcı yetenek (ability) olarak kaydeder. Uçucu veriler atılır.</div>')
            topic_in = ui.input(placeholder="Yetenek konusu").props("borderless dense dark").classes("glassfield")
            box = ui.column().style("width:100%;gap:4px")

            async def research_it():
                topic = (topic_in.value or "").strip()
                if not topic:
                    return
                note = ui.notification(f"Araştırılıyor: {topic}…", spinner=True, timeout=None)
                try:
                    draft = await run.io_bound(engine.acquire_ability, topic)
                except Exception as ex:
                    note.dismiss()
                    ui.notify(f"Başarısız: {ex}", type="negative")
                    return
                note.dismiss()
                if not draft:
                    ui.notify("Kaynak bulunamadı (internet / rate-limit).", type="negative")
                    return
                state["draft"] = draft
                box.clear()
                with box:
                    ui.html(f'<div class="formsub" style="color:var(--accent)">Kaynak · {draft["source"]}</div>')
                    state["editor"] = ui.textarea(value=draft["method"]).props("borderless dark autogrow").classes("glassfield").style("width:100%")

            def save_it():
                if not state.get("draft"):
                    ui.notify("Önce Araştır.")
                    return
                topic = (topic_in.value or "").strip()
                engine.save_ability(topic, state["editor"].value, state["draft"]["source"])
                dlg.close()
                refresh_current()
                ui.notify(f"Yetenek kaydedildi: {topic}")

            with ui.row().style("align-self:flex-end;gap:14px;align-items:center;margin-top:4px"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Kapat")
                with ui.element("div").classes("savebtn").on("click", research_it):
                    ui.label("Araştır")
                with ui.element("div").classes("newbtn").style("margin:0").on("click", save_it):
                    ui.label("Beyne kaydet")
        dlg.open()

    async def evolve_ui():
        abilities = [m for m in engine.memory_index() if m["type"] == "ability"]
        if not abilities:
            ui.notify("Önce bir yetenek öğret (Yetenek öğren).")
            return
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:680px;max-width:92vw;gap:8px;padding:22px"):
            ui.label("Yetenek evrimi").style("font-weight:600;font-size:16px")
            ui.html('<div class="formsub">AlphaEvolve tarzı, yerel ölçekte: metodun varyantları üretilir, her biri '
                    'deterministik değerlendiriciyle (parse + yapı + grounding) skorlanır. Kazanan ancak SEN onaylarsan '
                    'benimsenir; kaybedenler bir daha önerilmemek üzere arşivlenir. Yavaştır (~5-10 dk).</div>')
            sel = ui.select({m["id"]: m["id"] for m in abilities},
                            value=abilities[0]["id"]).props("borderless dense dark").classes("glassfield").style("width:100%")
            box = ui.column().style("width:100%;gap:6px")

            async def run_evo():
                aid = sel.value
                note = ui.notification(f"Evrim çalışıyor: {aid} — varyantlar üretilip skorlanıyor…",
                                       spinner=True, timeout=None)
                try:
                    rep = await run.io_bound(engine.evolve_ability, aid)
                except Exception as ex:
                    note.dismiss()
                    ui.notify(f"Evrim başarısız: {ex}", type="negative")
                    return
                note.dismiss()
                if not rep:
                    ui.notify("Bu id bir yetenek değil.", type="negative")
                    return
                box.clear()
                with box:
                    ui.label(f'Mevcut metod skoru (baseline): {rep["baseline"]}').style(
                        "font-size:13px;font-weight:600;color:var(--text)")
                    for c in rep["candidates"]:
                        mark = "🏆 " if (rep["winner"] and c is not None and c["body"] == rep["winner"]["body"]) else ""
                        ui.label(f'{mark}{c["score"]}  ·  {c["angle"]}').style("font-size:12px;color:var(--text-2)")
                    if rep["winner"]:
                        ui.html('<div class="formsub" style="color:var(--accent);margin-top:6px">Kazanan metod — onaylarsan benimsenecek</div>')
                        editor = ui.textarea(value=rep["winner"]["body"]).props("borderless dark autogrow") \
                            .classes("glassfield").style("width:100%")

                        def adopt():
                            engine.adopt_evolution(aid, editor.value)
                            dlg.close()
                            refresh_current()
                            ui.notify(f'Evrim benimsendi: {aid}  ({rep["baseline"]} → {rep["winner"]["score"]})')

                        with ui.element("div").classes("newbtn").style("margin:6px 0 0").on("click", adopt):
                            ui.label("Benimse")
                    else:
                        ui.label("Hiçbir varyant baseline'ı geçemedi — mevcut metod kalır (gate ilkesi).").style(
                            "font-size:12.5px;color:var(--text-3)")

            with ui.row().style("align-self:flex-end;gap:14px;align-items:center;margin-top:4px"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Kapat")
                with ui.element("div").classes("newbtn").style("margin:0").on("click", run_evo):
                    ui.label("Evrimi başlat")
        dlg.open()

    async def rescore_ui():
        note = ui.notification("Anayasa uygulanıyor: her memory rubrikle puanlanıyor…", spinner=True, timeout=None)
        try:
            props = await run.io_bound(engine.rescore_all)
        except Exception as ex:
            note.dismiss()
            ui.notify(f"Rescore failed: {ex}", type="negative")
            return
        note.dismiss()
        rows = []
        with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:760px;max-width:92vw;gap:8px;padding:22px"):
            ui.label("Retro puanlama - rubriğe göre öneriler").style("font-weight:600;font-size:15px")
            ui.html('<div class="formsub">Sayıyı düzenleyebilirsin; kayıtta türünün bandına kelepçelenir.</div>')
            with ui.scroll_area().style("max-height:50vh"):
                for p in props:
                    with ui.row().style("align-items:center;gap:8px;width:100%;flex-wrap:nowrap"):
                        ui.label(p["id"][:36]).style("font-size:12px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis")
                        ui.label(f'{p["current"]} →').style("font-size:12px;color:var(--text-3)")
                        inp = ui.input(value=str(p["proposed"])).props("borderless dense dark type=number").classes("glassfield").style("width:76px")
                        ui.label(f'({p["floor"]}-{p["cap"]})').style("font-size:11px;color:var(--text-3)")
                    if p["why"]:
                        ui.label(p["why"]).style("font-size:11px;color:var(--text-3);margin:0 0 4px 4px")
                    rows.append((p["id"], inp))
            with ui.row().style("align-self:flex-end;gap:14px;align-items:center"):
                with ui.element("div").classes("savebtn").on("click", dlg.close):
                    ui.label("Cancel")

                async def do_apply():
                    mapping = {mid: inp.value for mid, inp in rows}
                    n = await run.io_bound(engine.apply_rescore, mapping)
                    dlg.close()
                    refresh_current()
                    ui.notify(f"{n} memory yeniden puanlandı")

                with ui.element("div").classes("newbtn").style("margin:0").on("click", do_apply):
                    ui.label("Uygula")
        dlg.open()

    def build_graph_view():
        mems = engine.memory_index()
        by_id = {m["id"]: m for m in mems}
        ids = set(by_id)
        cats = ["system"] + BRANCH_ORDER
        catmap = {c: i + 1 for i, c in enumerate(BRANCH_ORDER)}
        HUB_LABEL = {"sources": "projects", "owner": "owner", "learnings": "learnings", "past-chats": "memory", "rules": "rules"}

        # real hierarchy from part-of links: entity (parent) -> aspect (child)
        parent = {}
        for m in mems:
            for to, typ in m["links"]:
                if typ == "part-of" and to in ids:
                    parent[m["id"]] = to

        def node_label(m):
            s = m["summary"] or m["id"]
            if " - " in s:
                head, tail = s.split(" - ", 1)
                s = head if m["type"] in ("source", "fact") else tail
            return s[:26]

        # root -> branch hub -> entity (top-level memory) -> aspect (part-of child)
        nodes = [{"name": "system", "category": 0, "symbolSize": 52, "value": "system root",
                  "itemStyle": {"color": "#d0d0d0"}, "label": {"formatter": "system", "fontSize": 13, "fontWeight": "bold"}}]
        links = []
        hubs = set()

        def hub_of(branch):
            key = f"hub::{branch}"
            if key not in hubs:
                nodes.append({"name": key, "category": catmap.get(branch, 1), "symbolSize": 34,
                              "value": f"{HUB_LABEL.get(branch, branch)} branch",
                              "label": {"formatter": HUB_LABEL.get(branch, branch), "fontSize": 12, "fontWeight": "bold"}})
                links.append({"source": "system", "target": key})
                hubs.add(key)
            return key

        used = set(getattr(engine, "last_selected_ids", []) or [])

        def salience_size(m, base):
            sal = (m.get("imp", 50) + m.get("act", 50)) / 200.0
            return max(10, round(base * (0.7 + 0.9 * sal)))

        for m in mems:
            par = parent.get(m["id"])
            source = par if (par in ids) else hub_of(m["branch"])
            node = {"name": m["id"], "category": catmap.get(m["branch"], 1),
                    "symbolSize": salience_size(m, 16 if par else 26),
                    "value": f'{m["summary"] or m["id"]}  ·  önem {m.get("imp", "?")}  ·  aktiflik {m.get("act", "?")}',
                    "label": {"formatter": node_label(m), "fontWeight": "normal" if par else "bold"}}
            if m["id"] in used:
                node["itemStyle"] = {"borderColor": "#f2b84b", "borderWidth": 3}
            elif m.get("act", 50) < 25:
                node["itemStyle"] = {"opacity": 0.55}   # fading = forgetting, made visible
            nodes.append(node)
            links.append({"source": source, "target": m["id"]})

        if used:
            path_edges = set()
            for mid in used:
                cur = mid
                while cur in parent and parent[cur] in ids:
                    path_edges.add((parent[cur], cur))
                    cur = parent[cur]
                if cur in by_id:
                    hub = f'hub::{by_id[cur]["branch"]}'
                    path_edges.add((hub, cur))
                    path_edges.add(("system", hub))
            for l in links:
                if (l["source"], l["target"]) in path_edges:
                    l["lineStyle"] = {"color": "#f2b84b", "width": 2.5, "opacity": 0.95}

        option = {
            "backgroundColor": "transparent",
            "tooltip": {"formatter": "{c}"},
            "legend": [{"data": cats, "top": 14, "textStyle": {"color": "#9a9a9a"}}],
            "color": ["#9a9a9a"] + GRAPH_COLORS,
            "series": [{
                "type": "graph", "layout": "force", "roam": True, "draggable": True,
                "categories": [{"name": c} for c in cats],
                "label": {"show": True, "position": "right", "color": "#cfcfcf", "fontSize": 11},
                "force": {"repulsion": 260, "edgeLength": 94, "gravity": 0.05},
                "lineStyle": {"color": "rgba(255,255,255,0.16)", "width": 1, "curveness": 0.05},
                "emphasis": {"focus": "adjacency"},
                "data": nodes, "links": links,
            }],
        }

        def on_node_click(e):
            name = getattr(e, "name", None)          # EChartPointClickEventArguments.name
            if name and name in by_id:                # hubs aren't memories -> ignored
                open_memory(engine.get_memory(name) or by_id[name])

        with refs["content"]:
            with ui.element("div").classes("main").style("padding:8px"):
                with ui.row().style("gap:10px;align-items:center;margin:4px 4px 0"):
                    with ui.element("div").classes("newbtn").style("margin:0;padding:8px 12px;font-size:12.5px").on("click", consolidate_ui):
                        ui.label("Konsolidasyon")
                    with ui.element("div").classes("newbtn").style("margin:0;padding:8px 12px;font-size:12.5px").on("click", learn_ability_ui):
                        ui.label("Yetenek öğren")
                    with ui.element("div").classes("newbtn").style("margin:0;padding:8px 12px;font-size:12.5px").on("click", evolve_ui):
                        ui.label("Yetenek evrimi")
                    with ui.element("div").classes("newbtn").style("margin:0;padding:8px 12px;font-size:12.5px").on("click", health_test):
                        ui.label("Sağlık testi")
                    with ui.element("div").classes("newbtn").style("margin:0;padding:8px 12px;font-size:12.5px").on("click", rescore_ui):
                        ui.label("Retro puanla")
                if mems:
                    ui.html('<div class="capnote" style="margin:4px 0 0">Halka büyüklüğü = güncel önem (taban + aktiflik) · altın yol = son cevabın bağlamı · soluk düğüm = unutulmaya yüz tutmuş</div>')
                    ui.echart(option, on_point_click=on_node_click).style("width:100%;height:100%")
                else:
                    ui.html('<div class="capnote" style="margin-top:20vh">No memories yet — add a source or analyze a project.</div>')

    # ---------- RAG / sources view (list) ----------
    def build_ingest_view():
        async def ingest_text(text, suggested_name=""):
            res = await run.io_bound(engine.ingest_document, text, suggested_name, "")
            similar = await run.io_bound(engine.find_similar, res["overview"], "sources")
            with ui.dialog() as dlg, ui.card().classes("dlgcard").style("min-width:560px;max-width:720px;gap:10px;padding:22px"):
                ui.label("Here's what I understood - add it to RAG?").style("font-weight:600;font-size:15px")
                with ui.row().style("gap:10px;align-items:center;width:100%;flex-wrap:nowrap"):
                    name_in = ui.input(value=suggested_name, placeholder="Source name (e.g. meld)").props("borderless dense dark").classes("glassfield flex-grow")
                    imp_in = ui.input(value=str(res.get("importance", 65))).props("borderless dense dark type=number").classes("glassfield").style("width:86px")
                ui.html(f'<div class="formsub">önem önerisi: {res.get("importance", "?")} — {res.get("why", "") or "rubrik bandı: source 55-80"}</div>')
                ui.html('<div class="formsub" style="margin-top:4px">Overview</div>')
                ui.label(res["overview"]).style("white-space:pre-wrap;font-size:13px;color:var(--text-2);line-height:1.55")
                ui.html(f'<div class="formsub">Split into {len(res["chunks"])} chunk(s)</div>')
                if similar:
                    score, sim = similar
                    ui.html(f'<div class="formsub" style="color:#e0b06a">Looks similar to existing <b>{sim["id"]}</b> (match {score:.2f}). Updating it avoids duplicates.</div>')
                with ui.row().style("align-self:flex-end;gap:14px;align-items:center"):
                    with ui.element("div").classes("savebtn").on("click", dlg.close):
                        ui.label("Cancel")

                    if similar:
                        async def do_update():
                            await run.io_bound(engine.append_to_source, similar[1]["id"], res["overview"], res["chunks"])
                            dlg.close()
                            render_content()
                            ui.notify(f"Updated {similar[1]['id']}")

                        with ui.element("div").classes("savebtn").style("color:var(--accent)").on("click", do_update):
                            ui.label("Update existing")

                    async def do_new():
                        await run.io_bound(engine.save_ingested, (name_in.value or "source").strip(),
                                           res["overview"], res["chunks"], imp_in.value)
                        dlg.close()
                        render_content()
                        ui.notify("Source added")

                    with ui.element("div").classes("newbtn").style("margin:0").on("click", do_new):
                        ui.label("Add as new" if similar else "Add source")
            dlg.open()

        async def create_src():
            text = (refs["ragbox"].value or "").strip()
            if not text:
                return
            refs["ragbox"].value = ""
            await ingest_text(text)

        def open_rag_upload():
            with ui.dialog() as dlg, ui.card().classes("dlgcard").style("min-width:540px;gap:10px;padding:22px"):
                ui.label("Add a document file as a source").style("font-weight:600;font-size:15px")
                ui.label("PDF, DOCX, TXT or MD - distilled into memory after your approval.").style("font-size:12px;color:var(--text-3)")

                async def add():
                    raw = (path_in.value or "").strip()
                    if not raw:
                        return
                    try:
                        name, text = await run.io_bound(extract_text_from_path, raw)
                    except Exception as ex:
                        ui.notify(f"Could not read file: {ex}", type="negative")
                        return
                    if not text.strip():
                        ui.notify("No readable text in that file", type="negative")
                        return
                    dlg.close()
                    await ingest_text(text, Path(name).stem)

                async def browse():
                    path = await pick_file()
                    if path:
                        path_in.value = str(path)

                with ui.element("div").classes("inputbar").style("box-shadow:none;margin:2px 0"):
                    path_in = ui.input(placeholder="File path (e.g. D:\\docs\\spec.pdf)").props("borderless dense dark").classes("flex-grow").on("keydown.enter", add)
                    with ui.element("div").classes("savebtn").on("click", browse):
                        ui.label("Browse")
                with ui.row().style("align-self:flex-end;gap:14px;align-items:center"):
                    with ui.element("div").classes("savebtn").on("click", dlg.close):
                        ui.label("Cancel")
                    with ui.element("div").classes("newbtn").style("margin:0").on("click", add):
                        ui.label("Add source")
            dlg.open()

        async def analyze_proj():
            path = (refs["projpath"].value or "").strip()
            if not path:
                return
            name = (refs["projname"].value or "").strip() or path.replace("\\", "/").rstrip("/").split("/")[-1]
            note = ui.notification(f"Reading & analyzing '{name}'…", spinner=True, timeout=None)
            try:
                res = await run.io_bound(engine.analyze_project, path, name)
            except Exception as ex:
                note.dismiss()
                ui.notify(f"Analyze failed: {ex}", type="negative")
                return
            note.dismiss()
            if not res:
                ui.notify("Folder not found or unreadable — check the path", type="negative")
                return
            with ui.dialog() as dlg, ui.card().classes("dlgcard").style("width:760px;max-width:92vw;gap:0;padding:0"):
                with ui.element("div").style("padding:22px 24px 12px;border-bottom:1px solid var(--stroke)"):
                    ui.label(f"How I understood '{name}'").style("font-weight:600;font-size:16px")
                    ui.label(f"Local repo pointer: {path}").style("font-size:11px;color:var(--accent);margin-top:3px")
                    ui.label("Edit any section, then add it to your brain.").style("font-size:12px;color:var(--text-3);margin-top:3px")
                editors = {}
                with ui.scroll_area().style("height:56vh;padding:2px 24px 8px"):
                    for cat, body in res["categories"].items():
                        ui.label(cat).style("display:block;font-weight:600;font-size:12px;color:var(--accent);"
                                            "text-transform:capitalize;letter-spacing:.04em;margin:18px 0 6px")
                        editors[cat] = ui.textarea(value=body).props("borderless dark autogrow").classes("glassfield").style("width:100%")
                with ui.row().style("padding:12px 24px;border-top:1px solid var(--stroke);justify-content:flex-end;gap:14px;align-items:center"):
                    with ui.element("div").classes("savebtn").on("click", dlg.close):
                        ui.label("Cancel")

                    def do_proj():
                        engine.save_project(name, path, {c: e.value for c, e in editors.items()})
                        dlg.close()
                        render_content()
                        ui.notify(f"'{name}' added to brain")

                    with ui.element("div").classes("newbtn").style("margin:0").on("click", do_proj):
                        ui.label("Add to brain")
            dlg.open()

        with refs["content"]:
            with ui.element("div").classes("main"):
                with ui.scroll_area().classes("flex-grow w-full"):
                    with ui.element("div").classes("chatinner"):
                        ui.html('<div class="formtitle">RAG Sources</div>')
                        ui.html('<div class="formsub">Your RAG knowledge. Click any to view / edit / delete. Add one below.</div>')
                        ui.html('<div class="formsub" style="margin-top:14px;color:var(--accent)">Analyze a whole project folder — AI reads it and writes structured memory</div>')
                        with ui.element("div").classes("inputbar").style("margin:6px 0 4px"):
                            refs["projpath"] = ui.input(placeholder="Project folder path (e.g. D:\\meld)").props("borderless dense dark").classes("flex-grow").on("keydown.enter", analyze_proj)
                            refs["projname"] = ui.input(placeholder="name").props("borderless dense dark").style("width:110px")
                            with ui.element("div").classes("newbtn").style("margin:0").on("click", analyze_proj):
                                ui.label("Analyze")
                        srcs = [m for m in engine.memory_index() if m["branch"] == "sources"]
                        if not srcs:
                            ui.html('<div class="capnote" style="margin-top:26px">No sources yet — add one below.</div>')
                        for m in srcs:
                            card = ui.element("div").classes("memcard").style("margin-top:6px")
                            with card:
                                ui.html(f'<div class="memid">{m["id"]}  ·  {m["type"]}</div>')
                                ui.html(f'<div class="memsum">{m["summary"]}</div>')
                            card.on("click", lambda e, mm=m: open_memory(mm))
                with ui.element("div").classes("inputwrap"):
                    with ui.element("div").classes("inputbar"):
                        with ui.element("div").classes("clipbtn").on("click", open_rag_upload):
                            ui.html(ICON_CLIP)
                        refs["ragbox"] = ui.input(placeholder="Paste or describe a new source...").props("borderless dense dark").classes("flex-grow").on("keydown.enter", create_src)
                        with ui.element("div").classes("sendbtn").on("click", create_src):
                            ui.html(ICON_PLUS)

    # ---------- about: the animated story of how the system works, in-app ----------
    def build_about_view():
        with refs["content"]:
            ui.element("iframe").props('src="/docs/story.html"').style(
                "flex:1;width:100%;height:100%;border:none;background:#0c0c0f")

    # ---------- view switching ----------
    def render_content():
        refs["content"].clear()
        if refs["view"] == "chat":
            build_chat_view()
        elif refs["view"] == "graph":
            build_graph_view()
        elif refs["view"] == "about":
            build_about_view()
        else:
            build_ingest_view()
        for name, el in refs["railbtns"].items():
            el.classes(replace="railbtn on" if name == refs["view"] else "railbtn")

    def set_view(v):
        refs["view"] = v
        render_content()

    # ---------- layout ----------
    with ui.row().classes("w-screen h-screen no-wrap gap-0"):
        with ui.element("div").classes("rail"):
            ui.html(f'<div class="railmark">{ICON_BRAND}</div>')
            refs["railbtns"] = {}
            for name, icon in (("chat", ICON_CHAT), ("graph", ICON_GRAPH), ("ingest", ICON_INGEST), ("about", ICON_INFO)):
                btn = ui.element("div").classes("railbtn")
                with btn:
                    ui.html(icon)
                btn.on("click", lambda e, n=name: set_view(n))
                refs["railbtns"][name] = btn
        refs["content"] = ui.element("div").style("flex:1;height:100%;display:flex;min-width:0")

    render_content()


if __name__ in {"__main__", "__mp_main__"}:
    app.add_static_files("/docs", str(Path(__file__).resolve().parent.parent / "docs"))
    app.on_startup(get_engine)
    native = os.getenv("PRAG_NATIVE", "1") != "0"
    ui.run(native=native, port=8080, title="project-rag", window_size=(1200, 780), reload=False)
