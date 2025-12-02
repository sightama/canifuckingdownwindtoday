# ABOUTME: Main NiceGUI web application entry point
# ABOUTME: Provides simple 90s-style UI for downwind condition ratings

from nicegui import ui
from app.config import Config
from app.orchestrator import AppOrchestrator


# Initialize orchestrator
orchestrator = AppOrchestrator(api_key=Config.GEMINI_API_KEY)


@ui.page('/')
def index():
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
    </style>
    """)

    with ui.column().classes('w-full items-center container'):
        # Title
        ui.html('<div class="title">CAN I FUCKING DOWNWIND TODAY</div>', sanitize=False)

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

        # Pre-fetch both ratings to enable instant toggle switching
        cached_ratings = {'sup': None, 'parawing': None}
        cached_recommendations = None

        def prefetch_all():
            """Pre-fetch both ratings on page load for instant switching"""
            nonlocal cached_recommendations
            try:
                cached_ratings['sup'] = orchestrator.get_sup_rating()
                cached_ratings['parawing'] = orchestrator.get_parawing_rating()
                cached_recommendations = orchestrator.get_foil_recommendations()
            except Exception as e:
                print(f"Prefetch error: {e}")

        def update_display():
            """Update display based on toggle selection using cached data"""
            try:
                mode = 'sup' if toggle.value == 'SUP Foil' else 'parawing'
                rating = cached_ratings.get(mode)

                if rating:
                    rating_label.content = f'<div class="rating">{rating.score}/10</div>'
                    description_label.content = f'<div class="description">{rating.description}</div>'
                else:
                    rating_label.content = '<div class="rating">N/A</div>'
                    description_label.content = '<div class="description">Weather data unavailable. Try again later or just send it.</div>'

                # Update foil recommendations from cache
                if cached_recommendations:
                    code_rec.content = f'<div class="rec-item">CODE: {cached_recommendations["code"]}</div>'
                    kt_rec.content = f'<div class="rec-item">KT: {cached_recommendations["kt"]}</div>'

                # Update timestamp
                from datetime import datetime
                timestamp_label.content = f'<div class="timestamp">Last updated: {datetime.now().strftime("%I:%M %p")}</div>'

            except Exception as e:
                print(f"UI update error: {e}")
                rating_label.content = '<div class="rating">ERROR</div>'
                description_label.content = '<div class="description">Something broke. Try refreshing the page.</div>'

        # Update on toggle change (instant since data is cached)
        toggle.on_value_change(lambda: update_display())

        # Initial load: prefetch all data then update display
        def initial_load():
            prefetch_all()
            update_display()

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
