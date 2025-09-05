# app.py
import flet as ft
import psycopg2
import os
from urllib.parse import urlparse

def main(page: ft.Page):
    page.title = "Simple Form App"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # Login state
    logged_in = False
    user_id = None

    # Database connection
    database_url = os.getenv("DATABASE_URL")
    parsed_url = urlparse(database_url)
    conn = psycopg2.connect(
        dbname=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port
    )
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS form_data (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            conditions TEXT,
            weather TEXT,
            questions TEXT,
            needs_help BOOLEAN,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    #  Added to detect if dark
    # Detect browser's color scheme
    #is_dark_mode = page.evaluate_js(
    #    'window.matchMedia("(prefers-color-scheme: dark)").matches'
    #)

    page.theme_mode = ft.ThemeMode.SYSTEM

    if page.theme_mode == ft.ThemeMode.DARK:
        page.theme_mode = ft.ThemeMode.LIGHT
        page.update()   


    # Login UI
    username = ft.TextField(label="Username")
    password = ft.TextField(label="Password", password=True)
    login_message = ft.Text()

    def login(e):
        nonlocal logged_in, user_id
        # Simple authentication (replace with secure auth in production)
        if username.value and password.value:
            user_id = username.value
            logged_in = True
            page.controls.clear()
            show_form()
            page.update()
        else:
            login_message.value = "Please enter username and password"
            page.update()

    # Form UI
    conditions = ft.TextField(label="Current Conditions")
    weather = ft.TextField(label="Weather")
    questions = ft.TextField(label="Other Questions")
    needs_help = ft.Checkbox(label="Do you need help?")
    submit_message = ft.Text()

    def submit_form(e):
        cursor.execute(
            "INSERT INTO form_data (user_id, conditions, weather, questions, needs_help) VALUES (%s, %s, %s, %s, %s)",
            (user_id, conditions.value, weather.value, questions.value, needs_help.value)
        )
        conn.commit()
        submit_message.value = "Data saved successfully!"
        conditions.value = ""
        weather.value = ""
        questions.value = ""
        needs_help.value = False
        page.update()

    def show_form():
        page.add(
            conditions,
            weather,
            questions,
            needs_help,
            ft.ElevatedButton("Submit", on_click=submit_form),
            submit_message
        )

    # Initial login page
    if not logged_in:
        page.add(
            username,
            password,
            ft.ElevatedButton("Login", on_click=login),
            login_message
        )

# Run locally with `flet run`
if __name__ == "__main__":
    ft.app(target=main, port=8000)