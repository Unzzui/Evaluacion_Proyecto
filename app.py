import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
import dash_html_components as html
import dash_core_components as dcc
import numpy_financial as npf
import numpy as np
import pandas as pd
import plotly.graph_objs as go
import csv
import uuid

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])

app.layout = html.Div(
    [
        html.H1("Evaluación de Proyectos"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.CardGroup(
                            [
                                dbc.Label("Inversión Inicial:"),
                                dbc.Input(id="inversion-input", type="number", min=0, step=0.01),
                            ]
                        ),
                        dbc.CardGroup(
                            [
                                dbc.Label("Cantidad de años:"),
                                dbc.Input(id="anios-input", type="number", min=1, step=1, value=1),
                            ]
                        ),
                        dbc.CardGroup(
                            [
                                dbc.Label("Costo de capital (%):"),
                                dbc.Input(id="costo-capital-input", type="number", min=0, step=0.01, value=10),
                            ]
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.Div(id="flujos-container"),
                        dbc.Button("Calcular", id="calcular-button", color="primary", className="mr-1"),
                        #dbc.Button("Exportar a CSV", id="export-csv-button", color="secondary", className="mr-1"),
                    ],
                    md=8,
                ),
            ]
        ),
        dbc.Alert(id="van-output", color="info"),
        dbc.Alert(id="tir-output", color="info"),
        dcc.Graph(id="flujos-grafico"),
        dcc.Graph(id="roi-grafico"),
        dcc.Store(id="result-store"),
    ]
)


@app.callback(
    Output("flujos-container", "children"),
    Input("anios-input", "value"),
)
def generar_campos_flujos(anios):
    if anios is None:
        raise dash.exceptions.PreventUpdate

    campos_flujos = []
    for i in range(anios):
        campos_flujos.append(
            dbc.CardGroup(
                [
                    dbc.Label(f"Flujo de efectivo año {i + 1}:"),
                    dbc.Input(id={"type": "flujo", "index": i}, type="number", min=0, step=0.01, value=0),
                ]
            )
        )
    return campos_flujos


@app.callback(
    [
        Output("van-output", "children"),
        Output("van-output", "color"),
        Output("tir-output", "children"),
        Output("tir-output", "color"),
        Output("result-store", "data"),
    ],
    [Input("calcular-button", "n_clicks")],
    [State("inversion-input", "value"),
     State("costo-capital-input", "value"),
     State("anios-input", "value"),
     State({"type": "flujo", "index": ALL}, "value")],
)
def calcular_van_tir(n_clicks, inversion, costo_capital, anios, flujos):
    if n_clicks is None or n_clicks == 0:
        raise dash.exceptions.PreventUpdate

    inversion = -inversion or 0  # La inversión debe ser un valor negativo
    costo_capital = costo_capital / 100 or 0
    flujos = list(flujos) or [0] * anios
    flujos.insert(0, inversion)  # Inserta la inversión como el primer flujo

    van = npf.npv(costo_capital, flujos)  # Calcula el VAN
    tir = npf.irr(flujos)  # Calcula la TIR

    color_van = "success" if van > 0 else "danger"
    color_tir = "success" if tir > costo_capital else "danger"

    data = {
        "inversion": inversion,
        "costo_capital": costo_capital,
        "flujos": flujos[1:],
        "van": van,
        "tir": tir,
    }

    return (
        f"El VAN del proyecto es: {van:.2f}",
        color_van,
        f"La TIR del proyecto es: {tir * 100:.2f}%",
        color_tir,
        data,
    )


@app.callback(
    Output("flujos-grafico", "figure"),
    Output("roi-grafico", "figure"),
    Input("result-store", "data"),
)
def actualizar_graficos(data):
    if data is None:
        raise dash.exceptions.PreventUpdate

    # Define los colores para los gráficos
    color_bar = '#2E91E5'  # azul para las barras
    color_scatter = '#E91E63'  # rosa para la línea

    # Configuración de los flujos de efectivo proyectados
    fig_flujos = go.Figure(data=go.Bar(x=list(range(1, len(data["flujos"]) + 1)), y=data["flujos"], marker_color=color_bar))
    fig_flujos.update_layout(
        title_text="Flujos de Efectivo Proyectados", 
        xaxis_title="Año", 
        yaxis_title="Flujo de Efectivo",
        plot_bgcolor='rgba(0,0,0,0)', # background transparente
        xaxis_showgrid=True,  # Mostrar cuadrícula
        yaxis_showgrid=True,
        font=dict(  # Cambiar la fuente
            family="Courier New, monospace",
            size=12,
            color="#7f7f7f"
        )
    )

    # Configuración del Retorno de la Inversión a lo Largo del Tiempo
    roi = np.cumsum(data["flujos"]) / -data["inversion"]  # Convertir a porcentaje
    fig_roi = go.Figure(data=go.Scatter(x=list(range(1, len(roi) + 1)), y=roi, mode='lines+markers', marker_color=color_scatter))
    fig_roi.update_layout(
        title_text="Retorno de la Inversión a lo Largo del Tiempo", 
        xaxis_title="Año", 
        yaxis_title="ROI (%)",  # Agregar el signo de porcentaje al título del eje y
        plot_bgcolor='rgba(0,0,0,0)', # background transparente
        xaxis_showgrid=True,  # Mostrar cuadrícula
        yaxis_showgrid=True,
        yaxis_tickformat = '.0%',  # Formatear los valores del eje y como porcentajes
        font=dict(  # Cambiar la fuente
            family="Courier New, monospace",
            size=12,
            color="#7f7f7f"
        )
    )

    return fig_flujos, fig_roi


# @app.callback(
#     Output("export-csv-button", "href"),
#     [Input("export-csv-button", "n_clicks"),  # Evento de clic del botón "Exportar a CSV"
#      Input("data-store", "data")],  # Los datos a exportar
# )
# def exportar_csv(n_clicks, data):
#     if n_clicks is None or data is None:  # Verificar si el botón "Exportar a CSV" ha sido presionado
#         raise dash.exceptions.PreventUpdate

#     filename = f"resultados_{uuid.uuid4()}.csv"
#     df = pd.DataFrame(data)
#     df.to_csv(filename, index=False)

#     return f"/download/{filename}"


if __name__ == "__main__":
    app.run_server(debug=True)
