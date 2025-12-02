import plotly.graph_objects as go
import pandas as pd


def price_chart(df: pd.DataFrame, title: str = "Price") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close"))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Price")
    return fig


def drawdown_chart(df: pd.DataFrame, title: str = "Drawdown") -> go.Figure:
    prices = df["Close"].copy()
    roll_max = prices.cummax()
    drawdown = (prices - roll_max) / roll_max
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown, name="Drawdown"))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Drawdown")
    return fig


def rolling_volatility_chart(df: pd.DataFrame, window: int = 21, title: str = "Rolling Volatility") -> go.Figure:
    df = df.copy()
    df["ret"] = df["Close"].pct_change()
    df["roll_vol"] = df["ret"].rolling(window).std() * (252 ** 0.5)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["roll_vol"], name=f"{window}-day rolling vol"))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title="Annualized Volatility")
    return fig
