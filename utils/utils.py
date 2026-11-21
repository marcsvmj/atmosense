from pathlib import Path
import pandas as pd
import streamlit as st


@st.cache_data(max_entries=2, show_spinner=False)
def load_data(file_path, modified_ns, file_size):
    df = pd.read_csv(file_path)

    if "data_hora" in df.columns:
        df["data_hora"] = pd.to_datetime(
            df["data_hora"],
            errors="coerce"
        )

        df = df.sort_values(
            "data_hora",
            kind="stable"
        ).reset_index(drop=True)

    return df


def get_file_data(file_path):
    file = Path(file_path)

    if not file.exists():
        return pd.DataFrame()

    file_stats = file.stat()

    return load_data(
        str(file.resolve()),
        file_stats.st_mtime_ns,
        file_stats.st_size
    )


def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def data_summary(df):
    summary = {
        "num_rows": df.shape[0],
        "num_columns": df.shape[1],
        "column_names": df.columns.tolist(),
        "data_types": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict()
    }
    return summary


def date_convert(df, column_name, date_format="%Y-%m-%d"):
    df[column_name] = pd.to_datetime(df[column_name], format=date_format)
    return df


def average_value(df, column_name):
    try:
        if column_name not in df.columns:
            return None
        return df[column_name].mean()
    except (TypeError, ValueError):
        return None


def min_value(df, column_name):
    try:
        if column_name not in df.columns:
            return None
        return df[column_name].min() 
    except (TypeError, ValueError):
        return None


def max_value(df, column_name):
    return df[column_name].max()


def get_latest_value(df, column_name):
    if column_name not in df.columns:
        return None
    
    try:
        value = df[column_name].iloc[-1]
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError, KeyError, IndexError):
        return None


def format_value(value, unit="", decimals=1):
    if value is None:
        return "—"
    return f"{value:.{decimals}f}{unit}"


def metric_card(title, value, description):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    
def style_chart(fig, height=260):
    is_dark = st.context.theme.type == "dark"

    if is_dark:
        template = "plotly_dark"
        font_color = "#cbd5e1"
        grid_color = "rgba(148, 163, 184, 0.12)"
    else:
        template = "plotly_white"
        font_color = "#334155"
        grid_color = "rgba(51, 65, 85, 0.12)"

    fig.update_layout(
        template=template,
        height=height,
        margin=dict(l=12, r=12, t=42, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=font_color, size=11),
        title=dict(
            font=dict(size=14, color=font_color),
            x=0.02
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            gridcolor=grid_color,
            zeroline=False
        )
    )

    return fig