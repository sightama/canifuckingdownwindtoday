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

    # Apply 90s styling
    ui.add_head_html("""
    <style>
        body {
            background-color: #FFFFFF;
            color: #000000;
            font-family: Arial, sans-serif;
        }
        .title {
            font-size: 48px;
            font-weight: bold;
            margin-top: 30px;
            text-align: center;
        }
        .rating {
            font-size: 120px;
            font-weight: bold;
            margin-top: 30px;
            text-align: center;
        }
        .description {
            font-size: 18px;
            margin-top: 20px;
            max-width: 700px;
            text-align: center;
            line-height: 1.6;
        }
        .toggle-container {
            margin-top: 30px;
            text-align: center;
        }
        .recommendations {
            margin-top: 40px;
            text-align: center;
        }
        .rec-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .rec-item {
            font-size: 16px;
            margin: 5px 0;
        }
        .timestamp {
            margin-top: 30px;
            font-size: 12px;
            color: #666666;
            text-align: center;
        }
    </style>
    """)

    with ui.column().classes('w-full items-center'):
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

        def update_display():
            """Update display based on toggle selection"""
            try:
                mode = 'sup' if toggle.value == 'SUP Foil' else 'parawing'

                if mode == 'sup':
                    rating = orchestrator.get_sup_rating()
                else:
                    rating = orchestrator.get_parawing_rating()

                if rating:
                    rating_label.content = f'<div class="rating">{rating.score}/10</div>'
                    description_label.content = f'<div class="description">{rating.description}</div>'
                else:
                    rating_label.content = '<div class="rating">N/A</div>'
                    description_label.content = '<div class="description">Weather data unavailable. Try again later or just send it.</div>'

                # Update foil recommendations
                try:
                    recommendations = orchestrator.get_foil_recommendations()
                    code_rec.content = f'<div class="rec-item">CODE: {recommendations["code"]}</div>'
                    kt_rec.content = f'<div class="rec-item">KT: {recommendations["kt"]}</div>'
                except Exception as e:
                    code_rec.content = '<div class="rec-item">CODE: Error loading</div>'
                    kt_rec.content = '<div class="rec-item">KT: Error loading</div>'

                # Update timestamp
                from datetime import datetime
                timestamp_label.content = f'<div class="timestamp">Last updated: {datetime.now().strftime("%I:%M %p")}</div>'

            except Exception as e:
                print(f"UI update error: {e}")
                rating_label.content = '<div class="rating">ERROR</div>'
                description_label.content = '<div class="description">Something broke. Try refreshing the page.</div>'

        # Update on toggle change
        toggle.on_value_change(lambda: update_display())

        # Initial load
        ui.timer(0.1, update_display, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Can I Fucking Downwind Today', port=8080)
