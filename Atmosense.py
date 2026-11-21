from datetime import datetime
import json
import os
import threading
import pandas as pd
import plotly.express as px
import paho.mqtt.client as mqtt
from streamlit_js_eval import get_geolocation
import streamlit as st

from utils.utils import (
    format_value,
    get_file_data,
    get_latest_value,
    load_css,
    metric_card,
    style_chart,
)
from utils.weather import get_week_forecast, get_weather_description

# Configurações do MQTT e caminhos do arquivo
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "prof_thiago/unip/pd2/atmosense/dados"
CSV_PATH = os.path.join("data/", "station_data.csv")

# Garante a criação da pasta e do CSV com o cabeçalho correto
def garantir_cabecalho_csv():
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="w", encoding="utf-8") as f:
            f.write("id,data_hora,temperatura,pressao,umidade,qualidade_ar\n")

# Callback executado ao conectar no broker MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[OK] Backend conectado ao broker MQTT!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"[FALHA] Falha na conexão MQTT, rc={rc}")

# Recebe a mensagem MQTT, extrai o ID direto do JSON e salva no CSV
def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode("utf-8").strip()
        dados = json.loads(payload_str)

        garantir_cabecalho_csv()

        # Pega o ID exato enviado pelo ESP32 dentro do JSON
        medicao_id = int(dados.get("id", 1))

        data_hora = str(dados.get("data_hora", "")).strip()
        if not data_hora or len(data_hora) < 10:
            data_hora = "09/11/2026 00:00:00"

        temperatura = float(dados.get("temperatura", 0.0))
        pressao = float(dados.get("pressao", 0.0))
        umidade = float(dados.get("umidade", 0.0))
        qualidade_ar = float(dados.get("qualidade_ar", 0.0))

        # Gravação blindada com quebra de linha limpa
        with open(CSV_PATH, mode="a", encoding="utf-8", newline="") as f:
            f.write(
                f"{medicao_id},{data_hora},{temperatura},{pressao},{umidade},{qualidade_ar}\n"
            )

        print(f"[SALVO NO CSV] ID #{medicao_id} -> {data_hora} | Temp: {temperatura}°C")
    except Exception as e:
        print(f"[ERRO MQTT] Falha ao processar mensagem: {e}")
        
# Inicializa o cliente MQTT em background usando Thread
@st.cache_resource
def iniciar_mqtt_background():
    garantir_cabecalho_csv()
    client = mqtt.Client(
        client_id="Atmosense-Python-Backend",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    def run_mqtt():
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f"[ERRO CONEXÃO MQTT] {e}")

    t = threading.Thread(target=run_mqtt, daemon=True)
    t.start()

# Inicia o serviço MQTT em segundo plano
iniciar_mqtt_background()

# Configuração inicial da página do Streamlit
st.set_page_config(
    page_title="Atmosense",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_css("style/atmosense.css")

# Renderiza todo o painel visual e atualiza a cada 5 segundos
@st.fragment(run_every="5s")
def render_dashboard():
    df = get_file_data("data/station_data.csv")

    if df.empty:
        st.warning("Aguardando novas medições do ESP32...")
        return

    temperature = get_latest_value(df, "temperatura")
    humidity = get_latest_value(df, "umidade")
    pressure = get_latest_value(df, "pressao")
    air_quality = get_latest_value(df, "qualidade_ar")

    # Cabeçalho visual da aplicação
    st.markdown(
        """
        <div class="dashboard-header">
            <div>
                <div class="dashboard-title">Atmosense</div>
                <div class="dashboard-subtitle">
                    ● Monitoramento ambiental em tempo real
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 2.2, 1], gap="large")

    # Coluna Esquerda: Exibição dos cartões de métricas atuais
    with col_left:
        st.markdown(
            '<div class="section-label">Medições atuais</div>',
            unsafe_allow_html=True,
        )
        metric_card(
            "Temperatura 🌡️",
            format_value(temperature, " °C"),
            "Última medição registrada",
        )
        metric_card(
            "Pressão Atmosférica ☁️",
            format_value(pressure, " hPa", decimals=0),
            "Dado não disponível" if pressure is None else "Última medição registrada",
        )
        metric_card(
            "Umidade💧",
            format_value(humidity, " %", decimals=0),
            "Última medição registrada",
        )
        metric_card(
            "Qualidade do Ar 🌬️",
            format_value(air_quality, " IQAr", decimals=0),
            "Dado não disponível" if air_quality is None else "Última medição registrada",
        )

    # Coluna Central: Destaque principal de temperatura e os gráficos Plotly
    with col_center:
        st.markdown(
            """
            <div class="main-temperature-card">
                <div class="main-temperature-label">TEMPERATURA ATUAL</div>
                <div class="main-temperature-value">
                    """
            + (f"{temperature:.1f}" if temperature is not None else "—")
            + """<span>°C</span>
                </div>
                <div class="main-temperature-footer">
                    <span>Atmosense</span>
                    <span>Última medição disponível</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="section-label">Gráficos de monitoramento</div>',
            unsafe_allow_html=True,
        )

        if "data_hora" not in df.columns:
            st.warning("A coluna 'data_hora' não foi encontrada no arquivo CSV.")
        else:
            chart_df = df.copy()
            chart_df["data_hora"] = pd.to_datetime(
                chart_df["data_hora"],
                errors="coerce",
            )
            chart_df = chart_df.dropna(subset=["data_hora"]).sort_values("data_hora")

            # Gráfico de Temperatura
            if "temperatura" in chart_df.columns:
                fig_temperature = px.line(
                    chart_df,
                    x="data_hora",
                    y="temperatura",
                    title="Temperatura por horário",
                    markers=True,
                    labels={"data_hora": "Horário", "temperatura": "Temperatura (°C)"},
                )
                fig_temperature.update_traces(
                    line=dict(color="#00c9e8", width=2.5),
                    marker=dict(size=5),
                )
                st.plotly_chart(
                    style_chart(fig_temperature, height=280),
                    width='stretch',
                    config={"displayModeBar": False, "responsive": True},
                )

            # Gráfico de Umidade
            if "umidade" in chart_df.columns:
                fig_humidity = px.line(
                    chart_df,
                    x="data_hora",
                    y="umidade",
                    title="Umidade por horário",
                    markers=True,
                    labels={"data_hora": "Horário", "umidade": "Umidade (%)"},
                )
                fig_humidity.update_traces(
                    line=dict(color="#38bdf8", width=2.5),
                    marker=dict(size=5),
                )
                st.plotly_chart(
                    style_chart(fig_humidity, height=260),
                    width='stretch',
                    config={"displayModeBar": False, "responsive": True},
                )

            # Gráfico de Qualidade do Ar (IQAr)
            if "qualidade_ar" in chart_df.columns:
                fig_air_quality = px.line(
                    chart_df,
                    x="data_hora",
                    y="qualidade_ar",
                    title="Qualidade do Ar por horário",
                    markers=True,
                    labels={"data_hora": "Horário", "qualidade_ar": "Qualidade do Ar (IQAr)"},
                )
                fig_air_quality.update_traces(
                    line=dict(color="#a78bfa", width=2.5),
                    marker=dict(size=5),
                )
                st.plotly_chart(
                    style_chart(fig_air_quality, height=260),
                    width='stretch',
                    config={"displayModeBar": False, "responsive": True},
                )

            # Gráfico de Pressão Atmosférica
            if "pressao" in chart_df.columns:
                fig_pressure = px.line(
                    chart_df,
                    x="data_hora",
                    y="pressao",
                    title="Pressão Atmosférica por horário",
                    markers=True,
                    labels={"data_hora": "Horário", "pressao": "Pressão (hPa)"},
                )
                fig_pressure.update_traces(
                    line=dict(color="#facc15", width=2.5),
                    marker=dict(size=5),
                )
                st.plotly_chart(
                    style_chart(fig_pressure, height=260),
                    width='stretch',
                    config={"displayModeBar": False, "responsive": True},
                )

            # Tabela de dados brutos do CSV (contendo o ID)
            st.dataframe(
                df,
                width='stretch',
                hide_index=True,
            )

    # Coluna Direita: Previsão do tempo baseada na geolocalização do usuário
    with col_right:
        st.markdown(
            '<div class="section-label">Previsão 7 dias</div>',
            unsafe_allow_html=True,
        )

        coordinates = st.session_state.get("weather_location")

        if coordinates is None:
            st.markdown(
                """
                <div class="panel-card">
                    <div class="section-label">Localização necessária</div>
                        Permita o acesso à sua localização para consultar
                        a previsão meteorológica da sua região.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button("Usar localização atual", key="ask_location"):
                st.session_state["requesting_location"] = True

            if st.session_state.get("requesting_location"):
                loc = get_geolocation()
                if loc and "coords" in loc:
                    st.session_state["weather_location"] = {
                        "latitude": loc["coords"]["latitude"],
                        "longitude": loc["coords"]["longitude"],
                    }
                    st.session_state["requesting_location"] = False
                    st.rerun()

        else:
            latitude = coordinates["latitude"]
            longitude = coordinates["longitude"]

            forecast = get_week_forecast(latitude, longitude)

            if forecast and "daily" in forecast:
                daily = forecast["daily"]

                weekdays = [
                    "Segunda-feira",
                    "Terça-feira",
                    "Quarta-feira",
                    "Quinta-feira",
                    "Sexta-feira",
                    "Sábado",
                    "Domingo",
                ]

                for i, date in enumerate(daily["time"]):
                    current_date = datetime.strptime(date, "%Y-%m-%d")
                    weekday = weekdays[current_date.weekday()]

                    weather_code = daily["weather_code"][i]
                    description, icon = get_weather_description(weather_code)

                    max_temp = daily["temperature_2m_max"][i]
                    min_temp = daily["temperature_2m_min"][i]
                    rain_probability = daily["precipitation_probability_max"][i]
                    precipitation = daily["precipitation_sum"][i]

                    min_temp = f"{min_temp:.1f} °C" if min_temp is not None else "—"
                    max_temp = f"{max_temp:.1f} °C" if max_temp is not None else "—"
                    rain_probability = f"{rain_probability}%" if rain_probability is not None else "—"
                    precipitation = f"{precipitation:.1f} mm" if precipitation is not None else "—"

                    st.markdown(
                        f"""
                        <div class="panel-card forecast-card">
                            <div class="forecast-header">
                                <span class="forecast-day">{weekday}</span>
                                <span class="forecast-date">{current_date.strftime('%d/%m')}</span>
                            </div>
                            <div class="forecast-condition">
                                <span class="forecast-icon">{icon}</span>
                                <span class="forecast-description">{description}</span>
                            </div>
                            <div class="forecast-temperatures">
                                <div class="forecast-temperature">
                                    <span class="data-note">Mínima</span>
                                    <strong style="color: white !important;">{min_temp}</strong>
                                </div>
                                <div class="forecast-temperature">
                                    <span class="data-note">Máxima</span>
                                    <strong style="color: white !important;">{max_temp}</strong>
                                </div>
                            </div>
                            <div class="forecast-details">
                                <span>🌧️ Chuva: {rain_probability}</span>
                                <span>Volume: {precipitation}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    """
                    <div class="panel-card">
                        <div class="data-note">
                            Não foi possível obter a previsão meteorológica.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

if __name__ == "__main__":
    render_dashboard()