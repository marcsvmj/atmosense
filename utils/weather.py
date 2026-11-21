import requests
import streamlit as st

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_CODES = {
    0: ("Céu limpo", "☀️"),
    1: ("Predominantemente limpo", "🌤️"),
    2: ("Parcialmente nublado", "⛅"),
    3: ("Nublado", "☁️"),
    45: ("Neblina", "🌫️"),
    48: ("Neblina com geada", "🌫️"),
    51: ("Garoa leve", "🌦️"),
    53: ("Garoa moderada", "🌦️"),
    55: ("Garoa intensa", "🌧️"),
    61: ("Chuva leve", "🌧️"),
    63: ("Chuva moderada", "🌧️"),
    65: ("Chuva intensa", "🌧️"),
    71: ("Neve leve", "🌨️"),
    73: ("Neve moderada", "🌨️"),
    75: ("Neve intensa", "❄️"),
    80: ("Pancadas de chuva leves", "🌦️"),
    81: ("Pancadas de chuva moderadas", "🌧️"),
    82: ("Pancadas de chuva intensas", "⛈️"),
    95: ("Trovoadas", "⛈️"),
    96: ("Trovoadas com granizo leve", "⛈️"),
    99: ("Trovoadas com granizo intenso", "⛈️"),
}


@st.cache_data(ttl=1800, show_spinner=False)
def get_week_forecast(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "precipitation_sum",
        ],
        "forecast_days": 7,
        "timezone": "auto",
    }

    try:
        response = requests.get(
            WEATHER_API_URL,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:
        st.error(f"Não foi possível consultar a previsão: {error}")
        return None


def get_weather_description(code):
    return WEATHER_CODES.get(
        code,
        ("Condição não identificada", "🌡️")
    )