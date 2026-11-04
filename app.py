# MAIN ENTRY POINT FOR PROGRAM
"""
app.py - Entry point, router and home page
============================================
Owns: st.session_state setup, the shared home page (FR01), and running
the right module based on st.session_state.page.

Run from the repo root:
    streamlit run app.py

Reference: Report section 3.3.1 (Application architecture) and
Table 3.4.2 (app.py row).

Teammates' modules are NOT modified. Each module's entry file is run
as a normal Streamlit script (via runpy) from inside its own folder, so
relative paths such as emails.json / oshc.json keep working.

The look of every page comes from ui/theme.py, assets/theme/*.css and
.streamlit/config.toml, so modules are restyled without editing them.

Scores: each module keeps its own score. Nothing is saved to disk and
no personal data is collected.
"""

import os
import runpy
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from ui import theme
from ui.theme import page_html

# set_page_config must be the first Streamlit call, and only once per page.
st.set_page_config(
    page_title="Medibank OSHC & Cyber Awareness",
    page_icon="🛡️",
    layout="centered",
)
# Directory definitions
ROOT = Path(__file__).resolve().parent
MODULES_DIR = ROOT / "modules"
# ---------------------------------------------------------------
# Where each module lives.
#   page key -> (folder, entry file, mode)
#   mode "script": the file runs top-level Streamlit code (like app.py)
#   mode "render": the file defines render(); it is called after loading
# If oshc/oshc.py defines render() and oshc/app.py is only a launcher,
# change the oshc line to: (MODULES_DIR / "oshc", "oshc.py", "render")
# ---------------------------------------------------------------
MODULE_CONFIG = {
    "phishing": (MODULES_DIR / "PhishGuard", "app.py", "script"),
    "vishing":  (MODULES_DIR / "Vishguard",  "app.py", "script"),
    "oshc":     (MODULES_DIR / "oshc",       "app.py", "script"),
}

# Each module on the home page: page key, line icon, title, one-line description,
# what the student does, and whether it is ready to play.
MODULES = [
    ("phishing", "mail-warning", "Phishing Awareness",
     "Spot the fake email before it spots you.",
     "3 levels · earn badges", True),
    ("vishing", "phone-call", "Social Engineering Awareness",
     "Audio required for this module, please use headphones or speakers!",
     "Voice-call scenarios", True),
    ("oshc", "heart-pulse", "Medibank OSHC Awareness",
     "What your Overseas Student Health Cover is and how to use it.",
     "Short sections · one question each", True),
]

# Set to True to show labelled boxes describing the photos still to be added.
SHOW_PHOTO_PLACEHOLDERS = False

# Shown on every page so nobody mistakes this for an official Medibank site.
STUDENT_NOTICE = (
    "This is a practice tool developed by students from Swinburne University "
    "of Technology. It is not an official Medibank service."
)


# ---------------------------------------------------------------
# FUNCTION: init_state()
# PURPOSE: Set up default session_state values on first load only.
# The root only owns "page"; modules manage their own keys.
# ---------------------------------------------------------------
def init_state():
    st.session_state.setdefault("page", "menu")


# ---------------------------------------------------------------
# FUNCTION: go_to(page_name)
# PURPOSE: Switch screens (FR07). Used as an on_click callback so it
# runs BEFORE the rerun.
# ---------------------------------------------------------------
def go_to(page_name):
    st.session_state.page = page_name


def back_to_menu():
    st.session_state.page = "menu"

@contextmanager
def module_context(folder):
    """Run a teammate's script as if it were launched from its own folder."""
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    old_config = st.set_page_config
    old_page = st.Page
    old_switch = st.switch_page
    old_chart = st.plotly_chart
    before = set(sys.modules)

    def _local(p):
        # Streamlit resolves page paths against the ROOT script's folder.
        # Point relative paths at the module's folder when the file exists there.
        if isinstance(p, (str, os.PathLike)) and not os.path.isabs(p):
            candidate = folder / p
            if candidate.exists():
                return str(candidate)
        return p

    def _page(page, *a, **k):
        return old_page(_local(page), *a, **k)

    def _switch(page, *a, **k):
        return old_switch(_local(page), *a, **k)

    def _chart(fig, *a, **k):
        # Modules draw dark charts; move them onto the light theme.
        k.setdefault("theme", None)   # keep our colours, not Streamlit's
        return old_chart(theme.style_figure(fig), *a, **k)

    st.set_page_config = lambda *a, **k: None   # root already set it
    st.Page = _page
    st.switch_page = _switch
    st.plotly_chart = _chart
    os.chdir(folder)
    sys.path.insert(0, str(folder))             # so "import content" works
    try:
        yield
    finally:
        st.set_page_config = old_config
        st.Page = old_page
        st.switch_page = old_switch
        st.plotly_chart = old_chart
        os.chdir(old_cwd)
        sys.path[:] = old_path
        folder_resolved = folder.resolve()
        for name in set(sys.modules) - before:
            file = getattr(sys.modules[name], "__file__", None)
            if file:
                try:
                    if Path(file).resolve().is_relative_to(folder_resolved):
                        sys.modules.pop(name, None)
                except (OSError, ValueError):
                    pass


def render_module(page):
    folder, entry, mode = MODULE_CONFIG[page]
    path = folder / entry

    page_html(f"<div class='ui-notice'>{STUDENT_NOTICE}</div>")
    with st.container(key="topbar"):
        page_html(logo_html())
        st.button("← Back to menu", key=f"back_{page}", on_click=back_to_menu)

    with st.container(key="module-body"):
        if not path.exists():
            st.info("This module isn't ready yet.")
            return

        try:
            with module_context(folder):
                if mode == "script":
                    # Streamlit runs app files as __main__, so do the same.
                    runpy.run_path(str(path), run_name="__main__")
                else:
                    ns = runpy.run_path(str(path), run_name=f"mod_{page}")
                    ns["render"]()
        except Exception:
            st.error("This module hit an error.")
            st.code(traceback.format_exc())


# ---------------------------------------------------------------
# Helpers for the home page
# ---------------------------------------------------------------
def logo_html():
    logo = theme.image_uri("medibank.png")
    if logo:
        return f"<img class='ui-logo' src='{logo}' alt='Medibank'>"
    return "<span class='ui-wordmark'>OSHC &amp; Cyber Awareness</span>"


def art_html(tiles, photo_file, shot):
    """Mosaic artwork, with a cut-out photo on top if the file exists in
    assets/images. Without one, the tiles show alone or, if
    SHOW_PHOTO_PLACEHOLDERS is on, a labelled box describes the shot."""
    photo = theme.image_uri(photo_file)
    front = ""
    if photo:
        front = f"<img class='hm-art__photo' src='{photo}' alt=''>"
    elif SHOW_PHOTO_PLACEHOLDERS:
        front = f"""<div class='hm-placeholder'>
            {theme.icon('user-round', 48)}
            <strong>Photo placeholder</strong>
            {shot}<br><code>assets/images/{photo_file}</code>
        </div>"""
    return f"""<div class='hm-art'>
        <img class='hm-art__tiles' src='{theme.image_uri(tiles)}' alt=''>
        {front}
    </div>"""


# ---------------------------------------------------------------
# Home page sections, top to bottom
# ---------------------------------------------------------------
def render_header():
    links = """<a href='#activities'>Activities</a>
        <a href='#how-it-works'>How it works</a>
        <a href='#practise'>What you'll practise</a>
        <a href='#get-help'>Get help</a>"""
    page_html(f"""<div class='ui-notice'>{STUDENT_NOTICE}</div>
    <header class='hm-header'>
        {logo_html()}
        <nav class='hm-nav' aria-label='Main'>{links}</nav>
        <details class='hm-menu'>
            <summary>{theme.icon('menu', 24)}Menu</summary>
            <nav aria-label='Menu'>{links}</nav>
        </details>
        <a class='ui-btn ui-btn--pill' href='#activities'>Get started</a>
    </header>""")


def render_hero():
    with st.container(key="sec-hero"):
        page_html("""<div class='hm-hero'>
            <p class='hm-eyebrow'>OSHC &amp; Cyber Awareness</p>
            <h1>New to Australia? Learn to spot scams and understand your health cover.</h1>
            <p class='hm-intro'>A few short, game-style activities, built for international
            students. No personal data is collected. Nothing you do here is
            <span class='hm-nowrap'>saved.<a href='#small-print'
            aria-label='Read the privacy details'>*</a></span></p>
        </div>""")
        with st.container(key="hero-actions"):
            st.button("Start spotting scams", key="hero_start", on_click=go_to, args=("phishing",))
            page_html("<a class='ui-btn ui-btn--lg ui-btn--outline-white' href='#activities'>See all activities</a>")
        with st.container(key="hero-art"):
            page_html(art_html(
                "art_hero.svg", "hero_photo.png",
                "International student laughing at their phone, waist up, cut out on a transparent background.",
            ))


def render_activities():
    with st.container(key="sec-task"):
        with st.container(key="task-card"):
            page_html("""<span class='hm-anchor' id='activities'></span>
            <div class='hm-task-head'><h2>Where do you want to start?</h2></div>""")
            with st.container(key="tiles"):
                columns = st.columns(len(MODULES))
                for column, (page, icon, name, desc, meta, ready) in zip(columns, MODULES):
                    with column, st.container(key=f"tile-{page}"):
                        page_html(f"""<div class='hm-tile'>
                            {theme.icon(icon, 40, '#FFFFFF')}
                            <p class='hm-tile__meta'>{meta}</p>
                            <p class='hm-tile__name'>{name}</p>
                            <p class='hm-tile__desc'>{desc}</p>
                        </div>""")
                        st.button(
                            "Start" if ready else "Coming soon",
                            key=f"home_{page}",
                            disabled=not ready,
                            on_click=go_to,
                            args=(page,),
                        )


def render_steps():
    steps = [
        ("mouse-pointer-click", "1. Pick an activity",
         "Start with scams or with your health cover. You choose the order."),
        ("list-checks", "2. Play through it",
         "Read emails, listen to calls or answer short questions, with feedback as you go."),
        ("trophy", "3. See how you did",
         "Each activity keeps its own score, so you can see what to practise next."),
    ]
    with st.container(key="sec-steps"):
        columns = "".join(
            f"<div>{theme.icon(icon, 40)}<h4>{title}</h4><p>{text}</p></div>"
            for icon, title, text in steps
        )
        page_html(f"""<span class='hm-anchor' id='how-it-works'></span>
        <h2 class='hm-section-title'>How it works</h2>
        <div class='hm-steps'>{columns}</div>
        <div class='hm-pair'>
            <a class='ui-btn ui-btn--primary' href='#activities'>Choose an activity</a>
            <a class='ui-btn ui-btn--outline' href='#small-print'>Your privacy</a>
        </div>""")


def render_why():
    with st.container(key="sec-why"), st.container(key="why-card"):
        text, art = st.columns([3, 2])
        with text, st.container(key="why-text"):
            page_html("""<div class='hm-why'>
                <h3>Unsure how OSHC works? That can make scams harder to spot.</h3>
                <p>International students moving to Australia are often unsure about OSHC and
                healthcare, and that may make them more susceptible to scams. These activities
                cover both, so you can start early in your student journey or before you arrive.</p>
            </div>""")
            st.button("Learn about OSHC", key="why_oshc", type="primary", on_click=go_to, args=("oshc",))
        with art:
            page_html(f"<img class='hm-why-art' src='{theme.image_uri('art_why.svg')}' alt=''>")


def render_practise():
    items = [
        ("phishing", "mail-warning", "Spot a fake email",
         "Flag anything suspicious, preview where a link really goes, then report it or mark it safe.",
         "Start phishing practice"),
        ("vishing", "phone-call", "Tell a real caller from a fake",
         "Listen to voice-call scenarios and decide who to trust. Use headphones or speakers.",
         "Start voice-call practice"),
        ("oshc", "heart-pulse", "Understand your cover",
         "Learn what OSHC is, why you need it and how to use it, in short sections with one question each.",
         "Start OSHC basics"),
    ]
    with st.container(key="sec-practise"):
        page_html("""<span class='hm-anchor' id='practise'></span>
        <h2 class='hm-section-title'>What you'll practise</h2>""")
        with st.container(key="practise-grid"):
            first, second = st.columns(2), st.columns(2)
            cells = [first[0], first[1], second[0]]
            for cell, (page, icon, title, text, action) in zip(cells, items):
                with cell, st.container(key=f"benefit-{page}"):
                    page_html(f"""<div class='hm-benefit'>
                        {theme.icon(icon, 40)}<h4>{title}</h4><p>{text}</p>
                    </div>""")
                    st.button(action, key=f"benefit_{page}", on_click=go_to, args=(page,))
            with second[1], st.container(key="benefit-privacy"):
                page_html(f"""<div class='hm-benefit'>
                    {theme.icon('lock-keyhole', 40)}<h4>Practise privately</h4>
                    <p>No personal data is collected. Nothing you do here is saved.</p>
                </div>
                <a class='hm-text-link' href='#small-print'>Read the details</a>""")


def render_help():
    chevron = theme.icon("chevron-right", 24, "#FFFFFF")
    links = [
        ("tel:000", "Life-threatening emergency: call <b>000</b>"),
        ("tel:1800887283", "Student Health and Support Line (OSHC members): <b>1800&nbsp;887&nbsp;283</b>"),
        ("tel:132331", "Unsure if a message is really from Medibank? Call <b>132&nbsp;331</b>"),
    ]
    stack = "".join(f"<a href='{href}'><span>{label}</span>{chevron}</a>" for href, label in links)
    with st.container(key="sec-help"):
        art = art_html(
            "art_help.svg", "help_photo.png",
            "Student on a phone call, relaxed and smiling, waist up, cut out on a transparent background.",
        )
        page_html(f"""<span class='hm-anchor' id='get-help'></span>
        <h2 class='hm-section-title'>Worried about something real?</h2>
        <div class='hm-help-grid'>
            {art}
            <div class='hm-stack'>{stack}</div>
        </div>""")


def render_small_print():
    with st.container(key="sec-print"):
        page_html(f"""<span class='hm-anchor' id='small-print'></span>
        <div class='hm-print'>
            <h5>Things you should know</h5>
            <p>{STUDENT_NOTICE} The emails and calls in the activities are practice examples.</p>
            <p>* We do not ask for your name or any personal information, and scores last only
            for your current session. The Advanced voice-call level can use your microphone. If you
            record a response there, the audio is sent to Google's speech recognition service
            to turn it into text.</p>
            <p>Font: DM Sans (SIL Open Font License). Icons: Lucide (ISC License).</p>
        </div>""")


def render_footer():
    activities = "".join(f"<li><a href='#activities'>{name}</a></li>" for _, _, name, *_ in MODULES)
    columns = [
        ("Activities", f"<ul>{activities}</ul>"),
        ("On this page", """<ul>
            <li><a href='#how-it-works'>How it works</a></li>
            <li><a href='#practise'>What you'll practise</a></li>
            <li><a href='#get-help'>Get help</a></li>
        </ul>"""),
        ("Your privacy", """<p>No personal data is collected. Nothing you do here is saved.
            <a href='#small-print'><u>Read the details</u></a></p>"""),
        ("About", "<p>Built for international students.</p>"),
    ]
    desktop = "".join(f"<div><h4>{title}</h4>{body}</div>" for title, body in columns)
    phone = "".join(f"<details><summary>{title}</summary>{body}</details>" for title, body in columns)
    page_html(f"""<footer class='hm-footer'>
        <div class='hm-footer__cols'>{desktop}</div>
        <div class='hm-footer__accordions'>{phone}</div>
        <div class='hm-footer__bar'>
            <span>OSHC &amp; Cyber Awareness</span>
            <span>Developed by students from Swinburne University of Technology</span>
            <a href='#small-print'>Things you should know</a>
        </div>
    </footer>""")


# ---------------------------------------------------------------
# FUNCTION: render_menu()
# PURPOSE: Draw the shared starting page (FR01).
# ---------------------------------------------------------------
def render_menu():
    st.html(theme.stylesheet("home.css"))
    render_header()
    render_hero()
    render_activities()
    render_steps()
    render_why()
    render_practise()
    render_help()
    render_small_print()
    render_footer()


# ---------------------------------------------------------------
# FUNCTION: main()
# PURPOSE: Read current page and call the matching render function.
# This is the "router" - it replaces needing separate page files.
# ---------------------------------------------------------------
PAGES = {
    "menu": render_menu,
    "phishing": lambda: render_module("phishing"),
    "vishing":  lambda: render_module("vishing"),
    "oshc":     lambda: render_module("oshc"),
}


def main():
    init_state()
    st.html(theme.stylesheet("theme.css"))
    PAGES.get(st.session_state.page, render_menu)()   # unknown page -> home


# ---- SCRIPT ENTRY POINT ----
main()
