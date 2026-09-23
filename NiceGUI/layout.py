from nicegui import ui


def render_sticky_header(page: str = "home"):
    """
    page: "home" | "about" | "demo" — controls header visibility.
    """
    is_home = page == "home"

    ui.add_head_html("""
        <style>
            .dynamic-header {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                width: 100% !important;
                z-index: 1000 !important;
                background: #1D2A78 !important;
                box-shadow: 0 4px 20px rgba(0,0,0,0.18) !important;
                min-height: 48px !important;
                padding-top: 4px !important;
                padding-bottom: 4px !important;

                opacity: 0 !important;
                visibility: hidden !important;
                pointer-events: none !important;
                transition: opacity 0.3s ease, visibility 0.3s ease;
            }
            .dynamic-header.scrolled,
            .dynamic-header.always-on {
                opacity: 1 !important;
                visibility: visible !important;
                pointer-events: auto !important;
            }

            .dynamic-header .header-logo {
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.3s ease, visibility 0.3s ease;
            }
            .dynamic-header.scrolled .header-logo,
            .dynamic-header.always-on .header-logo {
                opacity: 1;
                visibility: visible;
            }

            .dynamic-header .header-btn,
            .dynamic-header .header-btn *,
            .dynamic-header .header-logo-text,
            .dynamic-header .header-logo-text span,
            .dynamic-header .q-icon,
            .dynamic-header .q-btn__content,
            .dynamic-header .q-btn__content span {
                color: #FFFFFF !important;
            }
        </style>
        <script>
            (function () {
                function updateHeader() {
                    const header = document.getElementById('main-nav-header');
                    if (!header || header.classList.contains('always-on')) return;
                    const threshold = Math.max(280, window.innerHeight * 0.45);
                    if (window.scrollY > threshold) {
                        header.classList.add('scrolled');
                    } else {
                        header.classList.remove('scrolled');
                    }
                }
                window.addEventListener('scroll', updateHeader, { passive: true });
                window.addEventListener('resize', updateHeader);
                window.addEventListener('load', updateHeader);

                function killTopGap() {
                    const selectors = [
                        '#app', '.q-layout', '.q-page-container',
                        '.q-page', '.nicegui-content', 'body'
                    ];
                    selectors.forEach(function (sel) {
                        document.querySelectorAll(sel).forEach(function (el) {
                            el.style.setProperty('padding-top', '0px', 'important');
                            el.style.setProperty('margin-top', '0px', 'important');
                        });
                    });
                }
                window.addEventListener('load', killTopGap);
                window.addEventListener('resize', killTopGap);
                new MutationObserver(killTopGap).observe(document.documentElement, {
                    attributes: true,
                    subtree: true,
                    attributeFilter: ['style', 'class']
                });
                killTopGap();
            })();
        </script>
    """)

    header_classes = "dynamic-header items-center justify-between px-6 py-0 w-full"
    if not is_home:
        header_classes += " always-on"

    header_el = ui.row().classes(header_classes).props('id="main-nav-header"')
    with header_el:
        with (
            ui.row()
            .classes("items-center gap-2 cursor-pointer header-logo")
            .on("click", lambda: ui.navigate.to("/"))
        ):
            ui.label("BASEERA").classes(
                "text-sm font-bold tracking-widest cursor-pointer header-logo-text"
            ).style('font-family: "Cinzel", serif; color: #FFFFFF !important;')

        with ui.row().classes("items-center gap-1 ml-auto"):
            if is_home:
                ui.button(
                    "Home",
                    icon="home",
                    on_click=lambda: ui.run_javascript(
                        'window.scrollTo({top: 0, behavior: "smooth"});'
                    ),
                ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")
            else:
                ui.button(
                    "Home", icon="home", on_click=lambda: ui.navigate.to("/")
                ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")

            ui.button(
                "About", icon="info", on_click=lambda: ui.navigate.to("/about")
            ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")

            if is_home:
                ui.button(
                    "Architecture",
                    icon="schema",
                    on_click=lambda: ui.run_javascript(
                        'document.getElementById("architecture")?.scrollIntoView({behavior: "smooth"});'
                    ),
                ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")
                ui.button(
                    "Team",
                    icon="groups",
                    on_click=lambda: ui.run_javascript(
                        'document.getElementById("team")?.scrollIntoView({behavior: "smooth"});'
                    ),
                ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")
            else:
                ui.button(
                    "Architecture",
                    icon="schema",
                    on_click=lambda: ui.navigate.to("/#architecture"),
                ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")

            ui.button(
                "Live Demo", icon="play_circle", on_click=lambda: ui.navigate.to("/demo")
            ).props("flat dense").classes("cursor-pointer header-btn text-weight-bold text-xs")

            ui.button(
                icon="dark_mode",
                on_click=lambda: ui.run_javascript('document.body.classList.toggle("dark-mode")'),
            ).props("flat round dense").classes("cursor-pointer header-btn")

    # Initialize guide_bot once in layout
    try:
        from guide_bot import init_guide_bot
        init_guide_bot()
    except Exception:
        pass