#Librerias que se utilizarton para generar las graficas
import mysql.connector
import plotly.graph_objects as go
from datetime import datetime, timedelta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.io as pio
import pytz
import plotly.express as px
import pandas as pd 
import os
from dotenv import load_dotenv

load_dotenv()  # Carga variables desde .env

# Conectar a la base de datos
mydb = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME")
)
mycursor = mydb.cursor()

# Obtener la lista de estaciones
mycursor.execute("SELECT DISTINCT station FROM StationsData")
stations = mycursor.fetchall()
station_options = [{'label': station[0], 'value': station[0]} for station in stations]

# Crear la aplicación Dash
app = dash.Dash(__name__)
server = app.server

# Layout de la aplicación
app.layout = html.Div([
    dcc.Dropdown(
        id='station-dropdown',
        options=station_options,
        value=station_options[0]['value'],  # Valor por defecto
        clearable=False,
        style={'width': '50%'}
    ),
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=(datetime.now() - timedelta(days=2)).date(),
        end_date=datetime.now().date(),
        display_format='YYYY-MM-DD'
    ),
    dcc.Graph(id='graph'),
    dcc.Graph(id='graph2'),
    dcc.Graph(id='graph3'),
    dcc.Graph(id='graph5')
])

@app.callback(
    [Output('graph', 'figure'),
     Output('graph2', 'figure'),
     Output('graph3', 'figure'),
     Output('graph5', 'figure')],
    [Input('station-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graph(station, start_date, end_date):
    # Consultar los datos del rango de fechas seleccionado y la estación seleccionada
    query = """
    SELECT timestamp, wind_speed, wind_direction,temperature, dew_point, humidity, bar_sea_level, rainfall
    FROM StationsData
    WHERE station = %s AND DATE(timestamp) BETWEEN %s AND %s
    """
    mycursor.execute(query, (station, start_date, end_date))
    data = mycursor.fetchall()

    # Filtrar los datos para que solo incluyan horas enteras
    filtered_data = [row for row in data if row[0].minute == 0]

    # Convertir las horas a formato local
    local_tz = pytz.timezone('America/Mexico_City')  # Cambia esto a tu zona horaria local
    timestamps = [row[0].replace(tzinfo=pytz.utc).astimezone(local_tz) for row in filtered_data]

    # Mapeo de abreviaturas cardinales a grados
    cardinal_to_degrees = {
        'N': 0.0,
        'NNE': 22.5,
        'NE': 45.0,
        'ENE': 67.5,
        'E': 90.0,
        'ESE': 112.5,
        'SE': 135.0,
        'SSE': 157.5,
        'S': 180.0,
        'SSW': 202.5,
        'SW': 225.0,
        'WSW': 247.5,
        'W': 270.0,
        'WNW': 292.5,
        'NW': 315.0,
        'NNW': 337.5
    }

    # Procesar los datos
    wind_speed = [int(row[1]) for row in filtered_data]
    wind_direction = [
        float(row[2]) if row[2].replace('.', '', 1).isdigit() else cardinal_to_degrees.get(row[2], None)
        for row in filtered_data
    ]

    # Filtrar valores inválidos (None)
    wind_direction = [deg for deg in wind_direction if deg is not None]

    temperatures = [row[3] for row in filtered_data]
    dew_point = [row[4] for row in filtered_data]
    humidity = [row[5] for row in filtered_data]
    bar_sea_level = [float(row[6]) * 33.8639 for row in filtered_data]
    rainfall = [row[7] for row in filtered_data]



    #===============================================================
    #===============================================================
    #GRAFICA DE ROSA DE LOS VIENTOS
    #===============================================================
    #===============================================================

    # Función para mapear grados a puntos cardinales
    def map_direction_to_cardinal(degrees):
        if 337.5 <= degrees or degrees < 22.5:
            return 'North'
        elif 22.5 <= degrees < 67.5:
            return 'N-E'
        elif 67.5 <= degrees < 112.5:
            return 'East'
        elif 112.5 <= degrees < 157.5:
            return 'S-E'
        elif 157.5 <= degrees < 202.5:
            return 'South'
        elif 202.5 <= degrees < 247.5:
            return 'S-W'
        elif 247.5 <= degrees < 292.5:
            return 'West'
        elif 292.5 <= degrees < 337.5:
            return 'N-W'

    # Convertir las direcciones numéricas a puntos cardinales
    wind_direction_cardinal = [map_direction_to_cardinal(deg) for deg in wind_direction]

    # Crear el DataFrame con las direcciones cardinales
    df = pd.DataFrame({
        'Nudos': wind_speed,
        'Direccion': wind_direction_cardinal,
    })

    # Definir el orden fijo de los puntos cardinales
    category_order = ['North', 'N-E', 'East', 'S-E', 'South', 'S-W', 'West', 'N-W']

    # Crear la gráfica polar con el orden fijo
    fig5 = px.bar_polar(
        df, r="Nudos", theta="Direccion",
        color="Nudos", template="plotly_dark",
        color_discrete_sequence=px.colors.sequential.Plasma_r,
        category_orders={"Direccion": category_order}  # Orden fijo
    )
    fig5.update_traces()

    


    # Crear la gráfica con Plotly
    fig = go.Figure()

    #===============================================================
    #===============================================================
    #GRAFICA DESCRIPTIVA SOBRE LA TEMPERATURA, PUNTO DE ROCIO Y HUMEDAD RELATIVA
    #===============================================================
    #===============================================================

    # Agregar trazas para temperatura, punto de rocío y humedad relativa 
    fig.add_trace(go.Scatter(x=timestamps, y=temperatures, mode='lines+markers', name='Temperatura (°C)', line=dict(color='blue', shape='spline')))
    fig.add_trace(go.Scatter(x=timestamps, y=dew_point, mode='lines+markers', name='Punto de Rocío (°C)', line=dict(color='red', shape='spline')))

    # Agregar traza para humedad
    fig.add_trace(go.Scatter(x=timestamps, y=humidity, mode='lines+markers', name='Humedad Relativa (%)', line=dict(color='green', shape='spline'), yaxis='y2'))

    # Configurar ejes
    fig.update_layout(
        xaxis=dict(
            title='Fecha y Hora',
            tickformat='%H:%M\n%d/%m',
            dtick=3600000  # Mostrar etiquetas cada hora
        ),
        yaxis=dict(
            title=dict(
                text='Temperatura y Punto de Rocío (°C)',
                font=dict(color='black')
            ),
            tickfont=dict(color='black')
        ),
        yaxis2=dict(
            title=dict(
                text='Humedad Relativa (%)',
                font=dict(color='green')
            ),
            tickfont=dict(color='green'),
            overlaying='y',
            side='right'
        ),
        title='Temperatura, Punto de Rocio y Humedad Relativa',
        legend=dict(
            x=0.5,
            y=1.15,
            xanchor='center',
            orientation='h'
        )
    )

   
    # Crear la gráfica con Plotly
    fig3 = go.Figure()

    #===============================================================
    #===============================================================
    #GRAFICA DESCRIPTIVA SOBRE LA TEMPERATURA, PUNTO DE ROCIO Y PRESION BAROMETRICA
    #===============================================================
    #===============================================================
    

    # Agregar trazas para temperatura, punto de rocío y presion barometrica
    fig3.add_trace(go.Scatter(x=timestamps, y=temperatures, mode='lines+markers', name='Temperatura (°C)', line=dict(color='blue', shape='spline')))
    fig3.add_trace(go.Scatter(x=timestamps, y=dew_point, mode='lines+markers', name='Punto de Rocío (°C)', line=dict(color='red', shape='spline')))

    # Agregar traza para presion barometrica
    fig3.add_trace(go.Scatter(x=timestamps, y=bar_sea_level, mode='lines+markers', name='Presión Barométrica (Hpa)', line=dict(color='green', shape='spline'), yaxis='y2'))

    # Configurar ejes
    fig3.update_layout(
        xaxis=dict(
            title='Fecha y Hora',
            tickformat='%H:%M\n%d/%m',
            dtick=3600000  # Mostrar etiquetas cada hora
        ),
        yaxis=dict(
            title=dict(
                text='Temperatura y Punto de Rocío (°C)',
                font=dict(color='black')
            ),
            tickfont=dict(color='black')
        ),
        yaxis2=dict(
            title=dict(
                text='Presión Barométrica (Hpa)',
                font=dict(color='green')
            ),
            tickfont=dict(color='green'),
            overlaying='y',
            side='right'
        ),
        title='Temperatura, Humedad y Presión Barométrica',
        legend=dict(
            x=0.5,
            y=1.15,
            xanchor='center',
            orientation='h'
        )
    )


    # Crear la gráfica con Plotly
    fig2 = go.Figure()

    #===============================================================
    #===============================================================
    #GRAFICA DESCRIPTIVA SOBRE LA TEMPERATURA, PUNTO DE ROCIO Y PRECIPITACION
    #===============================================================
    #===============================================================

    # Agregar trazas para temperatura, punto de rocío y humedad relativa 
    fig2.add_trace(go.Bar(x=timestamps, y=temperatures, name='Temperatura (°C)', marker_color='cornflowerblue'))
    fig2.add_trace(go.Bar(x=timestamps, y=dew_point, name='Punto de Rocío (°C)', marker_color='lightblue'))

    fig2.add_trace(go.Scatter(x=timestamps, y=rainfall, mode='lines+markers', name='Precipitación Diaria (mm)', line=dict(color='blue', shape='spline'), yaxis='y3'))


   
    fig2.update_layout(
    xaxis=dict(
        title='Fecha y Hora',
        tickformat='%H:%M\n%d/%m',
        dtick=3600000  # Mostrar etiquetas cada hora
    ),
    yaxis=dict(
        title=dict(
            text='Temperatura y Punto de Rocío (°C)',
            font=dict(color='black')
        ),
        tickfont=dict(color='black')
    ),
    yaxis3=dict(
        title=dict(
            text='Precipitación Diaria (mm)',
            font=dict(color='blue')
        ),
        tickfont=dict(color='blue'),
        anchor='free',
        overlaying='y',
        side='right',
        position=1
    ),
    title='Temperatura, Punto de Rocio y Precipitación Diaria',
    legend=dict(
        x=0.5,
        y=1.15,
        xanchor='center',
        orientation='h'
        )
    )

    return fig,fig2,fig3,fig5

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)

