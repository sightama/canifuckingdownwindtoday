# ABOUTME: Main NiceGUI web application entry point
# ABOUTME: Provides simple 90s-style UI for downwind condition ratings

from nicegui import ui, Client
from app.config import Config
from app.orchestrator import AppOrchestrator
from app.ui.crayon_graph import CrayonGraph


# Initialize orchestrator
orchestrator = AppOrchestrator(api_key=Config.GEMINI_API_KEY)


@ui.page('/')
async def index(client: Client):
    """Main page with 90s aesthetic"""

    # Apply 90s styling with responsive scaling
    ui.add_head_html("""
    <style>
        * {
            box-sizing: border-box;
        }
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow-x: hidden;
        }
        body {
            background-color: #FFFFFF;
            color: #000000;
            font-family: Arial, sans-serif;
        }
        .container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2vh 4vw;
            width: 100%;
            margin: 0 auto;
        }
        /* Override NiceGUI's default column alignment */
        .nicegui-column {
            align-items: center !important;
        }
        .title {
            font-size: clamp(24px, 6vw, 48px);
            font-weight: bold;
            margin-top: 2vh;
            text-align: center;
        }
        .rating {
            font-size: clamp(60px, 20vw, 120px);
            font-weight: bold;
            margin-top: 2vh;
            text-align: center;
        }
        .description {
            font-size: clamp(14px, 3vw, 18px);
            margin-top: 2vh;
            max-width: 90vw;
            text-align: center;
            line-height: 1.6;
            padding: 0 2vw;
        }
        .toggle-container {
            margin-top: 2vh;
            text-align: center;
        }
        .recommendations {
            margin-top: 3vh;
            text-align: center;
        }
        .rec-title {
            font-size: clamp(16px, 4vw, 24px);
            font-weight: bold;
            margin-bottom: 1vh;
        }
        .rec-item {
            font-size: clamp(12px, 3vw, 16px);
            margin: 0.5vh 0;
        }
        .timestamp {
            margin-top: 2vh;
            font-size: clamp(10px, 2vw, 12px);
            color: #666666;
            text-align: center;
        }
        @media (max-width: 600px) {
            .description {
                font-size: 14px;
                line-height: 1.4;
            }
        }

        /* Loading overlay */
        #loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: white;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            transition: opacity 0.5s ease-out;
        }

        #loading-overlay.fade-out {
            opacity: 0;
            pointer-events: none;
        }

        #loading-text {
            font-family: monospace;
            font-size: 24px;
            color: #333;
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }

        /* Main content - hidden until loaded */
        #main-content {
            opacity: 0;
            transition: opacity 0.5s ease-in;
        }

        #main-content.visible {
            opacity: 1;
        }
    </style>
    """)

    # JavaScript for persona tracking in localStorage
    ui.add_head_html("""
    <script>
        function getLastPersona() {
            return localStorage.getItem('lastPersonaId') || '';
        }

        function setLastPersona(personaId) {
            localStorage.setItem('lastPersonaId', personaId);
        }
    </script>
    """)

    # Loading overlay - shown until data is ready
    ui.html('<div id="loading-overlay"><span id="loading-text">LOADING</span></div>', sanitize=False)

    with ui.column().classes('w-full items-center container').props('id="main-content"'):
        # Title
        ui.html('<div class="title">CAN I FUCKING DOWNWIND TODAY</div>', sanitize=False)

        # WHY button in top-right corner
        with ui.element('div').style('position: absolute; top: 20px; right: 20px;'):
            why_button = ui.label('WHY').style(
                'font-size: 14px; cursor: pointer; text-decoration: underline;'
            )

        # WHY dialog/overlay
        with ui.dialog() as why_dialog, ui.card().style('width: 90vw; max-width: 600px; max-height: 90vh; overflow-y: auto; text-align: center;'):
            ui.label('WHY THIS SCORE?').style('font-size: 24px; font-weight: bold; margin-bottom: 16px; width: 100%; text-align: center;')

            # Weather conditions section
            conditions_container = ui.column().style('width: 100%; margin-bottom: 24px; align-items: center;')

            ui.label('--- LIVE CAMS ---').style('font-size: 18px; font-weight: bold; margin: 16px 0; width: 100%; text-align: center;')

            # Video streams section
            with ui.column().style('width: 100%; gap: 16px; align-items: center;'):
                # Palm Beach Marriott cam
                ui.label('Palm Beach Marriott').style('font-size: 14px; font-weight: bold;')
                ui.html('''
                    <iframe src="https://video-monitoring.com/beachcams/palmbeachmarriott/stream.htm"
                            style="width: 100%; height: 200px; border: 1px solid #000;"
                            allow="autoplay" allowfullscreen></iframe>
                ''', sanitize=False)

                # Jupiter Inlet cam (YouTube)
                ui.label('Jupiter Inlet').style('font-size: 14px; font-weight: bold;')
                ui.html('''
                    <iframe src="https://www.youtube.com/embed/4y7kDbwBuh0?autoplay=1&mute=1"
                            style="width: 100%; height: 200px; border: 1px solid #000;"
                            allow="autoplay; encrypted-media" allowfullscreen></iframe>
                ''', sanitize=False)

                # Juno Beach cam (YouTube)
                ui.label('Juno Beach').style('font-size: 14px; font-weight: bold;')
                ui.html('''
                    <iframe src="https://www.youtube.com/embed/1FYgBpkM7SA?autoplay=1&mute=1"
                            style="width: 100%; height: 200px; border: 1px solid #000;"
                            allow="autoplay; encrypted-media" allowfullscreen></iframe>
                ''', sanitize=False)

            ui.label('* Recommendations for 195lb/88kg rider').style(
                'font-size: 12px; color: #666; margin-top: 16px; font-style: italic;'
            )

        def show_why():
            """Populate and show the WHY dialog"""
            conditions_container.clear()

            if cached_data:
                is_offline = cached_data.get("is_offline", False)
                weather_raw = cached_data.get('weather', {})
                timestamp = cached_data.get('timestamp')

                with conditions_container:
                    if is_offline:
                        ui.label('--- SENSOR OFFLINE ---').style('font-size: 18px; font-weight: bold; color: #c00; margin-bottom: 8px;')

                        last_known = cached_data.get("last_known_reading")
                        if last_known:
                            ui.label(f"Last reading: {last_known.wind_speed_kts:.1f}kts {last_known.wind_direction}").style('font-size: 14px; color: #666;')
                    else:
                        # Render crayon graph
                        graph = CrayonGraph()
                        wind_dir = weather_raw.get('wind_direction', 'N')
                        svg = graph.render(wind_direction=wind_dir)

                        ui.html(svg, sanitize=False).style('width: 100%; display: flex; justify-content: center; margin: 20px 0;')

                        ui.label('--- CONDITIONS ---').style('font-size: 18px; font-weight: bold; margin-bottom: 8px;')
                        ui.label(f"Wind: {weather_raw.get('wind_speed', 0):.1f} kts {weather_raw.get('wind_direction', 'N')}").style('font-size: 16px;')

                        # Show gust/lull if available
                        if weather_raw.get('wind_gust'):
                            ui.label(f"Gusts: {weather_raw['wind_gust']:.1f} kts / Lulls: {weather_raw.get('wind_lull', 0):.1f} kts").style('font-size: 14px; color: #666;')

                        if weather_raw.get('air_temp'):
                            ui.label(f"Air Temp: {weather_raw['air_temp']:.0f}°F").style('font-size: 14px; color: #666;')

                        # Note about no wave data
                        ui.label('Wave/swell data not available from sensor').style('font-size: 12px; color: #999; font-style: italic; margin-top: 8px;')

                        if timestamp:
                            ui.label(f"Data from: {timestamp.strftime('%Y-%m-%d %H:%M UTC')}").style('font-size: 12px; color: #666; margin-top: 8px;')
            else:
                with conditions_container:
                    ui.label('Weather data unavailable').style('font-size: 16px; color: #666;')

            why_dialog.open()

        why_button.on('click', show_why)

        # Toggle between SUP and Parawing
        with ui.row().classes('toggle-container'):
            toggle = ui.toggle(
                ['SUP Foil', 'Trashbaggers'],
                value='SUP Foil'
            ).style('border: 2px solid #000000; padding: 5px;')

        # Rating display (will update based on toggle)
        rating_label = ui.html('<div class="rating">--/10</div>', sanitize=False)
        description_label = ui.html('<div class="description">Loading conditions...</div>', sanitize=False)

        # Foil recommendations
        with ui.column().classes('recommendations'):
            ui.html('<div class="rec-title">--- FOIL RECOMMENDATIONS ---</div>', sanitize=False)
            code_rec = ui.html('<div class="rec-item">CODE: Loading...</div>', sanitize=False)
            kt_rec = ui.html('<div class="rec-item">KT: Loading...</div>', sanitize=False)

        # Last updated timestamp
        timestamp_label = ui.html('<div class="timestamp">Last updated: --</div>', sanitize=False)

        # Pre-fetch data
        cached_data = None
        current_persona_id = None
        cached_recommendations = None

        async def fast_initial_load():
            """Fast path: fetch sensor + 1 persona only, show page immediately"""
            nonlocal cached_data, current_persona_id, cached_recommendations
            try:
                from app.ai.personas import get_random_persona

                # Wait for client WebSocket connection before running JavaScript
                await client.connected()

                # Get last persona from localStorage via JS
                last_persona = await ui.run_javascript('getLastPersona()')
                exclude_id = last_persona if last_persona else None

                # Select a random persona (excluding last one)
                persona = get_random_persona(exclude_id=exclude_id)
                current_persona_id = persona["id"]

                # Store the new persona ID
                await ui.run_javascript(f"setLastPersona('{current_persona_id}')")

                # FAST PATH: Get initial data with single persona
                cached_data = orchestrator.get_initial_data(persona_id=current_persona_id)

                # Get foil recommendations
                ratings = cached_data.get('ratings') if cached_data else None
                if ratings and ratings.get('sup', 0) > 0:
                    cached_recommendations = orchestrator.get_foil_recommendations(
                        score=cached_data['ratings']['sup']
                    )
                else:
                    cached_recommendations = orchestrator.get_foil_recommendations()

            except Exception as e:
                print(f"Fast initial load error: {e}")
                # Fallback to full load on error
                cached_data = orchestrator.get_cached_data()

        async def background_refresh():
            """Background: fetch remaining personas and parawing mode"""
            try:
                if current_persona_id and cached_data and not cached_data.get("is_offline"):
                    # Run in executor to not block UI
                    import asyncio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: orchestrator.refresh_remaining_variations(
                            initial_persona_id=current_persona_id,
                            initial_mode="sup"
                        )
                    )
            except Exception as e:
                print(f"Background refresh error: {e}")

        def update_display():
            """Update display based on toggle selection using cached data"""
            try:
                mode = 'sup' if toggle.value == 'SUP Foil' else 'parawing'

                if cached_data:
                    is_offline = cached_data.get("is_offline", False)

                    if is_offline:
                        # OFFLINE STATE
                        rating_label.content = '<div class="rating" style="color: #999;">OFFLINE</div>'

                        # Get offline variation
                        description = orchestrator.get_random_variation(mode, current_persona_id)
                        description_label.content = f'<div class="description">{description}</div>'

                        # Show last known info
                        last_known = cached_data.get("last_known_reading")
                        if last_known:
                            from datetime import datetime, timezone, timedelta
                            from zoneinfo import ZoneInfo

                            # Calculate how long ago
                            now = datetime.now(timezone.utc)
                            age = now - last_known.timestamp_utc
                            age_minutes = int(age.total_seconds() / 60)

                            if age_minutes < 60:
                                age_str = f"{age_minutes} min ago"
                            else:
                                age_str = f"{age_minutes // 60}h {age_minutes % 60}m ago"

                            timestamp_label.content = (
                                f'<div class="timestamp" style="color: #c00;">'
                                f'Sensor offline - Last reading: {last_known.wind_speed_kts:.0f}kts '
                                f'{last_known.wind_direction} ({age_str})'
                                f'</div>'
                            )
                        else:
                            timestamp_label.content = '<div class="timestamp" style="color: #c00;">Sensor offline - No recent data</div>'

                        # Hide recommendations when offline
                        code_rec.content = '<div class="rec-item">CODE: --</div>'
                        kt_rec.content = '<div class="rec-item">KT: --</div>'

                    else:
                        # ONLINE STATE
                        if current_persona_id:
                            score = cached_data['ratings'][mode]
                            description = orchestrator.get_random_variation(mode, current_persona_id)

                            rating_label.content = f'<div class="rating">{score}/10</div>'
                            description_label.content = f'<div class="description">{description}</div>'
                        else:
                            rating_label.content = '<div class="rating">N/A</div>'
                            description_label.content = '<div class="description">Weather data unavailable.</div>'

                        # Update foil recommendations
                        if cached_recommendations:
                            code_rec.content = f'<div class="rec-item">CODE: {cached_recommendations["code"]}</div>'
                            kt_rec.content = f'<div class="rec-item">KT: {cached_recommendations["kt"]}</div>'

                        # Update timestamp
                        from datetime import datetime
                        from zoneinfo import ZoneInfo

                        est_time = datetime.now(ZoneInfo("America/New_York"))
                        timestamp_label.content = f'<div class="timestamp">Last updated: {est_time.strftime("%I:%M %p")} EST</div>'

                else:
                    rating_label.content = '<div class="rating">N/A</div>'
                    description_label.content = '<div class="description">Weather data unavailable. Try again later.</div>'

            except Exception as e:
                print(f"UI update error: {e}")
                rating_label.content = '<div class="rating">ERROR</div>'
                description_label.content = '<div class="description">Something broke. Try refreshing the page.</div>'

        async def show_content():
            """Fade out loading overlay and fade in main content"""
            try:
                await ui.run_javascript('''
                    document.getElementById('loading-overlay').classList.add('fade-out');
                    document.getElementById('main-content').classList.add('visible');
                    // Remove overlay from DOM after animation
                    setTimeout(() => {
                        const overlay = document.getElementById('loading-overlay');
                        if (overlay) overlay.remove();
                    }, 500);
                ''', timeout=5.0)
            except TimeoutError:
                # Client may have disconnected - content is already displayed
                pass

        # Update on toggle change (instant since data is cached)
        toggle.on_value_change(lambda: update_display())

        # Initial load: fast path then background refresh
        async def initial_load():
            await fast_initial_load()
            update_display()
            await show_content()
            # Start background refresh after page is visible (if client still connected)
            try:
                ui.timer(0.5, background_refresh, once=True)
            except Exception:
                # Client disconnected before we could start background refresh - that's fine
                pass

        ui.timer(0.1, initial_load, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    import os
    port = int(os.environ.get('PORT', 8080))
    ui.run(
        title='Can I Fucking Downwind Today',
        host='0.0.0.0',
        port=port,
        reload=False  # Disable reload in production
    )
