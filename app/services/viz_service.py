# app/services/viz_service.py
import plotly.express as px
import pandas as pd
import json

def create_bar_chart(data: list[dict], x_col: str, y_col: str, title: str) -> str:
    """
    Takes data as a list of dicts, creates a bar chart with Plotly, and returns it as JSON.
    """
    print(f"Generating bar chart for: {title}")
    try:
        df = pd.DataFrame(data)
        if x_col not in df.columns or y_col not in df.columns:
            return json.dumps({"error": f"Invalid columns. Available: {list(df.columns)}"})
        fig = px.bar(df, x=x_col, y=y_col, title=title, template="plotly_dark")
        return fig.to_json()
    except Exception as e:
        return json.dumps({"error": f"Could not generate chart: {e}"})

def create_pie_chart(data: list[dict], names_col: str, values_col: str, title: str) -> str:
    """
    Takes data as a list of dicts, creates a pie chart with Plotly, and returns it as JSON.
    """
    print(f"Generating pie chart for: {title}")
    try:
        df = pd.DataFrame(data)
        if names_col not in df.columns or values_col not in df.columns:
            return json.dumps({"error": f"Invalid columns. Available: {list(df.columns)}"})
        fig = px.pie(df, names=names_col, values=values_col, title=title, template="plotly_dark")
        return fig.to_json()
    except Exception as e:
        return json.dumps({"error": f"Could not generate chart: {e}"})