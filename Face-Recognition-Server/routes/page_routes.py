from flask import render_template


def register_page_routes(app):
    @app.route("/")
    def home():
        html = render_template("index.html")

        marker_without_id = '<div id="med-rec-tab" class="tab-pane">\n          <div class="recognition-card">'
        marker_with_id = '<div id="med-rec-tab" class="tab-pane">\n          <div class="recognition-card" id="med-feed-card">'

        if marker_without_id in html and "id=\"med-feed-card\"" not in html:
            html = html.replace(marker_without_id, marker_with_id, 1)

        return html
