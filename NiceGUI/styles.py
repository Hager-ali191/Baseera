from nicegui import ui


def render_global_styles():
    ui.colors(
        primary="#1D2A78",
        secondary="#FAD02C",
        accent="#1D2A78",
        positive="#10B981",
        negative="#EF4444",
    )

    ui.add_head_html("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css"/>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800;900&family=Montserrat:wght@300;400;600;700&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            ::-webkit-scrollbar { display: none !important; width: 0px !important; }
            html, body { -ms-overflow-style: none !important; scrollbar-width: none !important; }

            button, .q-btn, [role="button"], a, .cursor-pointer, .q-chip, .hover-up {
                cursor: pointer !important;
            }

            *, *::before, *::after { box-sizing: border-box !important; }

            html, body, #app, .q-layout, .q-page-container, .q-page, main {
                margin: 0 !important;
                padding: 0 !important;
                top: 0 !important;
                width: 100% !important;
                max-width: 100vw !important;
                overflow-x: hidden !important;
                scroll-behavior: smooth !important;
                background-color: transparent !important;
            }

            .q-page-container { padding-top: 0px !important; margin-top: 0px !important; }
            body { background-color: #FFFFFF; }

            @keyframes softGradientBG {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }

            .hero-section {
                position: relative;
                width: 100vw !important;
                min-width: 100vw !important;
                left: 50% !important;
                right: 50% !important;
                margin-left: -50vw !important;
                margin-right: -50vw !important;
                margin-top: 0 !important;
                padding-top: 0px !important;
                min-height: 100vh !important;
                box-sizing: border-box !important;
                overflow: hidden !important;
                background: linear-gradient(135deg, #FAD02C, #FFE885, #F4C430, #FFF1B0);
                background-size: 300% 300%;
                animation: softGradientBG 10s ease-in-out infinite alternate;
            }

            .bg-shape {
                position: absolute;
                pointer-events: none;
                z-index: 1;
                background: transparent !important;
                border-color: #1D2A78 !important;
                opacity: 0.25;
            }
            .shape-circle { border-style: solid; border-radius: 50%; }
            .shape-square { border-style: solid; border-radius: 4px; }
            .shape-ring { border-style: dashed; border-radius: 50%; }

            @keyframes floatSlow1 {
                0%, 100% { transform: translateY(0px) rotate(0deg); }
                50% { transform: translateY(-12px) rotate(25deg); }
            }
            @keyframes floatSlow2 {
                0%, 100% { transform: translateY(0px) rotate(0deg); }
                50% { transform: translateY(15px) rotate(-20deg); }
            }
            .anim-1 { animation: floatSlow1 7s ease-in-out infinite; }
            .anim-2 { animation: floatSlow2 9s ease-in-out infinite; }
            .anim-3 { animation: floatSlow1 6s ease-in-out infinite reverse; }

            .hero-content { position: relative; z-index: 2; }

            .skill-chip {
                background-color: #1D2A78 !important;
                color: #FAD02C !important;
                font-weight: 600 !important;
                font-size: 11px !important;
                border-radius: 8px !important;
                padding: 4px 10px !important;
            }

            .dark-mode { background-color: #0A0F24 !important; color: #FFFFFF !important; }
            .dark-mode .bg-white-card { background-color: #131C38 !important; color: #FFFFFF !important; border-color: #2D3A6E !important; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
            .dark-mode .text-custom-dark { color: #FAD02C !important; }
            .dark-mode p, .dark-mode label, .dark-mode .q-field__label, .dark-mode .q-field__native { color: #FFFFFF !important; }
            .dark-mode input, .dark-mode textarea { background-color: #0F172A !important; color: #FFFFFF !important; }

            .fancy-title {
                font-family: 'Cinzel', serif !important;
                font-weight: 900 !important;
                letter-spacing: 14px !important;
                color: #1D2A78 !important;
                text-shadow: 2px 4px 12px rgba(29, 42, 120, 0.18);
            }

            .hover-up { transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); }
            .hover-up:hover { transform: translateY(-8px); box-shadow: 0 12px 24px rgba(0,0,0,0.15); }

            @keyframes pulse-glow {
                0% { opacity: 0.88; transform: scale(1); }
                50% { opacity: 1; transform: scale(1.02); }
                100% { opacity: 0.88; transform: scale(1); }
            }
            .pulse-glow { animation: pulse-glow 3s ease-in-out infinite; }
            .recording-active { animation: rec-pulse 1.5s infinite !important; background-color: #EF4444 !important; color: #FFFFFF !important; }
        </style>
    """)
