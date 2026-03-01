from flask import render_template


def register_page_routes(app):
    @app.route("/")
    def home():
        return render_template("index.html")
