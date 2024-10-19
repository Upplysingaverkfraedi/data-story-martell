import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

# Hlaða inn gögnunum úr báðum skrám
def load_data():
    # Breyta þessu í slóðirnar að þínum CSV skrám
    summary_data = pd.read_csv("CSV/siggi_hlaup_summary.csv")
    hlaup_data = pd.read_csv("CSV/siggi_hlaup.csv")
    return summary_data, hlaup_data

# Tengja gögnin á grundvelli 'IDs' og 'hlaupa_id'
def get_filtered_data_for_ids(merged_data, ids_str):
    # Skipta 'IDs' strengnum upp í lista af ID númerum
    ids_list = ids_str.split(", ")
    ids_list = [int(id_) for id_ in ids_list]  # Breyta í int ef ID-in eru heiltölur
    
    # Sía gögnin þannig að þau innihaldi aðeins valin 'hlaupa_id'
    filtered_data = merged_data[merged_data['hlaup_id'].isin(ids_list)]
    return filtered_data

# UI - Notendaviðmót
app_ui = ui.page_fluid(
    ui.h2("Sigurjón Ernir á Timataka.net"),
    
    # Dropdown fyrir að velja Length
    ui.input_select("length_select", "Veldu hlaup:", choices=[]),
    
    # Bæta við gagnvirku kökuriti
    output_widget("pie_chart"),
    
    # Layout með tveimur dálkum, þar sem línuritið tekur meira pláss en taflan
    ui.layout_columns(
        output_widget("line_chart"),    # Línurit sem sýnir tíma eða hringir
        ui.output_table("time_table"),  # Tafla sem sýnir tíma fyrir ID
        col_widths=[8, 4]  # Línuritið fær 8/12 hluta af plássinu, taflan 4/12
    )
)

# Server - Gagnavinnsla
def server(input, output, session):
    # Hlaða gögnunum
    summary_data, hlaup_data = load_data()
    
    # Gera lengdirnar úr 'Length' dálknum aðgengilegar fyrir dropdown
    @reactive.Effect
    def update_dropdown():
        ui.update_select("length_select", choices=list(summary_data['Length']))

    # Gagnavinnsla fyrir kökuritið
    @output
    @render_plotly
    def pie_chart():
        # Búa til kökurit með 'Length' og 'Counts' úr samantektargögnum
        fig = px.pie(summary_data, values='Count', names='Length', title="Hlutfall hlaupa eftir lengd")
        return fig

    # Línurit sem uppfærist þegar notandi velur lengd
    @output
    @render_plotly
    @reactive.event(input.length_select)
    def line_chart():
        # Fá lengdina sem notandinn valdi
        selected_length = input.length_select()
        
        # Sækja IDs fyrir valda lengd
        ids_str = summary_data[summary_data['Length'] == selected_length]["IDs"].values[0]
        filtered_data = get_filtered_data_for_ids(hlaup_data, ids_str)
        
        # Nota 'Time' ef hann er til staðar, annars 'Laps' (fyrir backyard hlaup)
        if 'Time' in filtered_data.columns and not filtered_data['Time'].isnull().all():
            y_axis = 'Time'
        else:
            y_axis = 'Laps'

        # Búa til línurit fyrir valda vegalengd (tími eða hringir vs hlaupa_id)
        fig = px.line(filtered_data, x='hlaup_id', y=y_axis, title=f"{y_axis} fyrir {selected_length}")
        
        # Virkja hover event á línuritið til að sýna samsvarandi gildi í töflunni
        fig.update_traces(hoverinfo='x+y', mode='lines+markers')
        return fig

    # Tafla sem sýnir tímatölur (Time) fyrir valin hlaupa_id
    @output
    @render.table
    def time_table():
        selected_length = input.length_select()
        ids_str = summary_data[summary_data['Length'] == selected_length]["IDs"].values[0]
        filtered_data = get_filtered_data_for_ids(hlaup_data, ids_str)
        return filtered_data[['hlaup_id', 'Time']].dropna()

# Keyra Shiny appið
app = App(app_ui, server)
