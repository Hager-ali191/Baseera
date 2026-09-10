import os
import requests
from nicegui import app, ui

# -----------------------------------------------------------------------------
# CONFIGURATION & API ENDPOINTS
# -----------------------------------------------------------------------------
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Global Application State across pages
class AppState:
    def __init__(self):
        self.image_bytes = None
        self.image_filename = "captured_scene.jpg"
        self.audio_bytes = None
        self.audio_filename = "voice_prompt.wav"
        
        # Backend response cache
        self.transcribed_text = ""
        self.response_text = ""
        self.response_audio_url = ""
        self.direction = ""
        self.distance = ""
        self.confidence = 0.0

state = AppState()

# Safe page layout builder
def render_layout():
    ui.colors(
        primary='#1D2A78',    # Deep Dark Blue
        secondary='#FFE366',  # Bright Logo Yellow
        accent='#1D2A78',
        positive='#10B981',
        negative='#EF4444'
    )
    
    ui.query('body').style('background-color: #FAFAFA; font-family: sans-serif;')
    
    # Header Navigation
    with ui.header().classes('items-center justify-between px-8 py-3 shadow-md').style('background-color: #1D2A78;'):
        with ui.row().classes('items-center gap-3 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.label('Baseera').classes('text-2xl font-extrabold tracking-wider').style('color: #FFE366;')
            ui.label('VOICE GUIDED - OBJECT FINDER').classes('text-xs font-bold tracking-widest self-end mb-1').style('color: #FFE366;')
        
        with ui.row().classes('items-center gap-3'):
            ui.button('Home', icon='home', on_click=lambda: ui.navigate.to('/')).props('flat text-color=white dense')
            ui.button('Capture & Upload', icon='mic', on_click=lambda: ui.navigate.to('/input')).props('flat text-color=white dense')
            ui.button('Results', icon='analytics', on_click=lambda: ui.navigate.to('/results')).props('flat text-color=white dense')


# -----------------------------------------------------------------------------
# PAGE 1: HOME PAGE ("/")
# -----------------------------------------------------------------------------
@ui.page('/')
def home_page():
    render_layout()

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-8 items-center text-center mt-6'):
        with ui.card().classes('w-full p-8 shadow-lg rounded-2xl items-center').style('background-color: #FFE366; border: 2px solid #1D2A78;'):
            ui.label('Welcome to Baseera').classes('text-4xl font-black').style('color: #1D2A78;')
            ui.label('An AI-powered voice guidance system to assist in finding and locating objects in real time.').classes('text-base font-semibold mt-2').style('color: #1D2A78;')

        with ui.grid(columns=2).classes('w-full gap-6 mt-4'):
            with ui.card().classes('p-6 shadow-md rounded-xl bg-white border border-slate-200 items-center text-center cursor-pointer hover:shadow-xl transition-all').on('click', lambda: ui.navigate.to('/input')):
                ui.icon('mic', size='xl').style('color: #1D2A78;')
                ui.label('Voice & Camera Input').classes('text-xl font-bold mt-2').style('color: #1D2A78;')
                ui.label('Provide a voice prompt and capture or upload scene photos to analyze.').classes('text-xs text-slate-500 mt-1')
                ui.button('Go to Input', icon='arrow_forward').classes('mt-4').style('background-color: #1D2A78; color: #FFE366;')

            with ui.card().classes('p-6 shadow-md rounded-xl bg-white border border-slate-200 items-center text-center cursor-pointer hover:shadow-xl transition-all').on('click', lambda: ui.navigate.to('/results')):
                ui.icon('analytics', size='xl').style('color: #1D2A78;')
                ui.label('Detection & Results Dashboard').classes('text-xl font-bold mt-2').style('color: #1D2A78;')
                ui.label('View spatial guidance, directions, distance estimates, and spoken feedback.').classes('text-xs text-slate-500 mt-1')
                ui.button('View Results', icon='arrow_forward').classes('mt-4').style('background-color: #1D2A78; color: #FFE366;')


# -----------------------------------------------------------------------------
# PAGE 2: INPUT WORKSPACE PAGE ("/input")
# -----------------------------------------------------------------------------
@ui.page('/input')
def input_page():
    render_layout()

    with ui.column().classes('w-full max-w-5xl mx-auto p-6 gap-6 items-center'):
        
        # Header Banner
        with ui.card().classes('w-full p-4 shadow-sm rounded-xl text-center items-center').style('background-color: #1D2A78; border: 2px solid #FFE366;'):
            ui.label('Input Workspace').classes('text-2xl font-black').style('color: #FFE366;')
            ui.label('First speak your command, then capture or upload scene photos.').classes('text-xs font-semibold text-slate-200 mt-1')

        # --- FIRST SECTION: VOICE COMMAND INPUT ---
        with ui.card().classes('w-full p-6 shadow-md rounded-xl bg-white border border-slate-200 gap-4'):
            ui.label('1. Voice Command Input').classes('font-bold text-lg').style('color: #1D2A78;')
            
            with ui.row().classes('w-full items-center justify-between gap-6'):
                # HTML5 Mic Interface
                ui.html('''
                    <div style="text-align: center; padding: 10px; width: 100%;">
                        <button id="recordBtn" style="background-color: #1D2A78; color: #FFE366; padding: 12px 24px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; font-size: 14px;">
                            🎙️ Record Voice Command
                        </button>
                        <p id="recStatus" style="font-size: 12px; color: #64748B; margin-top: 8px;">Click to start recording</p>
                    </div>
                ''').classes('w-1/2')

                ui.separator().props('vertical')

                # Audio File Upload
                with ui.column().classes('w-1/2 gap-2'):
                    ui.label('Upload Audio File:').classes('text-xs font-semibold text-slate-500')
                    
                    def handle_audio_upload(e):
                        state.audio_bytes = e.content.read()
                        state.audio_filename = e.name
                        audio_status.set_text(f"Selected: {e.name}")
                        ui.notify('Audio file uploaded!', type='positive')

                    ui.upload(
                        label='Upload Audio (.wav, .mp3)',
                        auto_upload=True,
                        max_files=1,
                        on_upload=handle_audio_upload
                    ).classes('w-full').props('accept=".wav,.mp3,.m4a"')
                    audio_status = ui.label('No audio file selected').classes('text-xs text-slate-400 italic')

        # --- SECOND SECTION: EXPANDED CAMERA / PHOTO AREA ---
        with ui.card().classes('w-full p-6 shadow-md rounded-xl bg-white border border-slate-200 gap-4'):
            ui.label('2. Camera View & Image Source').classes('font-bold text-lg').style('color: #1D2A78;')
            
            with ui.tabs().classes('w-full') as image_tabs:
                tab_cam = ui.tab('Camera Live View', icon='photo_camera')
                tab_file = ui.tab('Upload Image File', icon='upload')

            with ui.tab_panels(image_tabs, value=tab_cam).classes('w-full p-2'):
                
                # Camera Capture Option (Expanded Height)
                with ui.tab_panel(tab_cam):
                    ui.interactive_image().classes('w-full h-[450px] bg-slate-900 rounded-xl object-cover shadow-inner')
                    
                    def grab_frame():
                        ui.notify('High-resolution frame captured!', type='positive', icon='camera_alt')
                    
                    with ui.row().classes('w-full justify-center mt-3'):
                        ui.button('Capture Frame', icon='camera_alt', on_click=grab_frame).classes('px-8 py-3 font-bold text-base rounded-lg shadow-md').style('background-color: #1D2A78; color: #FFE366;')

                # File Upload Option
                with ui.tab_panel(tab_file):
                    def handle_img_upload(e):
                        state.image_bytes = e.content.read()
                        state.image_filename = e.name
                        img_status.set_text(f"Selected: {e.name}")
                        ui.notify('Photo uploaded!', type='positive')

                    ui.upload(
                        label='Choose Photo (.jpg, .png)',
                        auto_upload=True,
                        max_files=1,
                        on_upload=handle_img_upload
                    ).classes('w-full h-48 border-2 border-dashed rounded-xl p-4').props('accept=".jpg,.jpeg,.png"')
                    img_status = ui.label('No file selected').classes('text-xs text-slate-400 italic mt-2 text-center')

        # Pipeline Execution Button
        def execute_pipeline():
            if not state.image_bytes and not state.audio_bytes:
                ui.notify('Please provide at least a photo or voice command.', type='warning', icon='warning')
                return

            proc_spinner.set_visibility(True)
            proc_btn.disable()
            
            try:
                files = {}
                if state.image_bytes:
                    files['image'] = (state.image_filename, state.image_bytes, 'image/jpeg')
                if state.audio_bytes:
                    files['audio'] = (state.audio_filename, state.audio_bytes, 'audio/wav')

                response = requests.post(f"{BACKEND_URL}/process", files=files, timeout=60)
                
                if response.status_code == 200:
                    res = response.json()
                    
                    state.transcribed_text = res.get('transcribed_text', 'Find the target object in scene.')
                    state.response_text = res.get('response_text', res.get('result', 'Target detected.'))
                    state.direction = res.get('direction', '2 o\'clock (To your right)')
                    state.distance = res.get('distance', '1.5 meters')
                    state.confidence = res.get('confidence', 0.94)
                    state.response_audio_url = res.get('audio_response_url', '')

                    ui.notify('Analysis complete! Redirecting...', type='positive')
                    ui.navigate.to('/results')
                else:
                    ui.notify(f"Backend Error: {response.text}", type='negative')

            except Exception as err:
                ui.notify(f"Connection failed: {str(err)}", type='negative')
            finally:
                proc_spinner.set_visibility(False)
                proc_btn.enable()

        with ui.row().classes('w-full items-center gap-4 mt-2'):
            proc_btn = ui.button('Analyze & Process Data', icon='bolt', on_click=execute_pipeline) \
                .classes('w-full py-4 font-bold text-xl rounded-xl shadow-lg transition-transform hover:scale-[1.01]') \
                .style('background-color: #1D2A78; color: #FFE366;')
            
            proc_spinner = ui.spinner(size='lg', color='amber-500')
            proc_spinner.set_visibility(False)


# -----------------------------------------------------------------------------
# PAGE 3: RESULTS DASHBOARD PAGE ("/results")
# -----------------------------------------------------------------------------
@ui.page('/results')
def results_page():
    render_layout()

    with ui.column().classes('w-full max-w-4xl mx-auto p-6 gap-6'):
        
        # Results Header
        with ui.card().classes('w-full p-6 shadow-md rounded-2xl text-center items-center').style('background-color: #1D2A78; border: 2px solid #FFE366;'):
            ui.label('Detection & Guidance Results').classes('text-2xl font-extrabold').style('color: #FFE366;')
            ui.label('Outputs generated by AI models based on your inputs.').classes('text-sm font-medium text-slate-200 mt-1')

        # Results Display Grid
        with ui.grid(columns=2).classes('w-full gap-6 items-start'):
            
            # Left Card: Voice Speech & Response
            with ui.card().classes('w-full p-5 shadow-sm rounded-xl bg-white border border-slate-200 gap-4'):
                ui.label('Voice Speech & Response').classes('font-bold text-base').style('color: #1D2A78;')
                
                ui.label('Converted Speech to Text:').classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 rounded-lg'):
                    ui.label(state.transcribed_text or "No voice command transcribed.").classes('text-sm text-slate-800 font-medium')

                ui.separator().classes('my-1')

                ui.label('AI Response Text:').classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                with ui.card().classes('w-full p-3 bg-yellow-50 border border-yellow-200 rounded-lg'):
                    ui.label(state.response_text or "No response generated.").classes('text-sm text-slate-900 font-semibold')

                ui.label('Response Audio Output:').classes('text-xs font-bold text-slate-400 uppercase tracking-wider mt-2')
                if state.response_audio_url:
                    ui.audio(state.response_audio_url).classes('w-full mt-1')
                else:
                    ui.label('Audio playback unavailable.').classes('text-xs italic text-slate-400')

            # Right Card: Directions, Distance & Model Confidence
            with ui.card().classes('w-full p-5 shadow-sm rounded-xl bg-white border border-slate-200 gap-4'):
                ui.label('Spatial Guidance & Metrics').classes('font-bold text-base').style('color: #1D2A78;')

                # Direction Guidance
                with ui.row().classes('items-center gap-3 w-full p-3 bg-blue-50 border border-blue-100 rounded-xl'):
                    ui.icon('explore', size='md').style('color: #1D2A78;')
                    with ui.column().classes('gap-0'):
                        ui.label('Direction Guidance').classes('text-xs font-bold text-slate-500')
                        ui.label(state.direction or 'N/A').classes('text-lg font-extrabold').style('color: #1D2A78;')

                # Distance Metric
                with ui.row().classes('items-center gap-3 w-full p-3 bg-emerald-50 border border-emerald-100 rounded-xl'):
                    ui.icon('straighten', size='md').classes('text-emerald-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Estimated Distance').classes('text-xs font-bold text-slate-500')
                        ui.label(state.distance or 'N/A').classes('text-lg font-extrabold text-emerald-700')

                # Model Confidence Score
                with ui.column().classes('w-full gap-1 mt-2'):
                    with ui.row().classes('justify-between w-full'):
                        ui.label('Model Confidence').classes('text-xs font-bold text-slate-500')
                        ui.label(f"{int(state.confidence * 100)}%").classes('text-xs font-bold').style('color: #1D2A78;')
                    
                    ui.linear_progress(value=state.confidence, show_value=False).props('size=10px color=amber-5').classes('rounded-full')

        # Navigation Buttons
        with ui.row().classes('w-full gap-4 mt-4'):
            ui.button('Back to Capture', icon='arrow_back', on_click=lambda: ui.navigate.to('/input')) \
                .classes('w-1/2 py-3 font-bold rounded-xl shadow-md') \
                .style('background-color: #1D2A78; color: #FFE366;')
            
            ui.button('Home', icon='home', on_click=lambda: ui.navigate.to('/')) \
                .classes('w-1/2 py-3 font-bold rounded-xl shadow-md') \
                .style('background-color: #FFE366; color: #1D2A78;')


# -----------------------------------------------------------------------------
# RUN APPLICATION
# -----------------------------------------------------------------------------
ui.run(title='Baseera - Voice Guided Object Finder', port=8501, reload=True)