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
    def format_seconds_to_hhmmss(seconds):
        # Breyta sekúndum í heiltölur
        seconds = int(seconds)
        # Reikna út klukkustundir, mínútur og sekúndur
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        # Skila streng í 'HH:MM:SS' sniði
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @output
    @render_plotly
    @reactive.event(input.length_select)
    def line_chart():
        # Fá lengdina sem notandinn valdi
        selected_length = input.length_select()
        
        # Sækja IDs fyrir valda lengd
        ids_str = summary_data[summary_data['Length'] == selected_length]["IDs"].values[0]
        filtered_data = get_filtered_data_for_ids(hlaup_data, ids_str)
        
        # Athuga hvort 'Time' dálkurinn sé til staðar og ekki tómur
        if 'Time' in filtered_data.columns and not filtered_data['Time'].isnull().all():
            # Breyta 'Time' úr streng í sekúndur
            if filtered_data['Time'].dtype == 'object':
                try:
                    # Reyna að umbreyta 'Time' í sekúndur með 'HH:MM:SS' sniði
                    filtered_data['Time_in_seconds'] = pd.to_timedelta(filtered_data['Time']).dt.total_seconds()
                except:
                    # Ef það virkar ekki, reyna með 'MM:SS' sniði
                    filtered_data['Time_in_seconds'] = pd.to_timedelta('00:' + filtered_data['Time']).dt.total_seconds()
            else:
                # Ef 'Time' er þegar tölulegt gildi í sekúndum
                filtered_data['Time_in_seconds'] = filtered_data['Time']
            
            y_axis = 'Time_in_seconds'
            y_label = 'Tími (HH:MM:SS)'
            
            # Búa til línurit með 'hlaup_id' á x-ás og 'Time_in_seconds' á y-ás
            fig = px.line(
                filtered_data,
                x='hlaup_id',
                y=y_axis,
                title=f"Tími fyrir {selected_length}",
                labels={'hlaup_id': 'Hlaup ID', y_axis: y_label}
            )
            
            # Búa til sérsniðna y-ás merkimiða án '0 days'
            y_ticks = sorted(filtered_data[y_axis].unique())
            y_ticktext = [format_seconds_to_hhmmss(seconds) for seconds in y_ticks]
            
            fig.update_yaxes(
                tickmode='array',
                tickvals=y_ticks,
                ticktext=y_ticktext
            )
            
            # Uppfæra hovertemplate til að sýna tímann í 'HH:MM:SS' sniði
            hover_text = [format_seconds_to_hhmmss(t) for t in filtered_data[y_axis]]
            fig.update_traces(
                hovertemplate='Hlaup ID: %{x}<br>Tími: %{text}',
                text=hover_text
            )
            
        else:
            y_axis = 'Laps'
            y_label = 'Fjöldi hringja'
            
            # Búa til línurit fyrir 'Laps'
            fig = px.line(
                filtered_data,
                x='hlaup_id',
                y=y_axis,
                title=f"Hringir fyrir {selected_length}",
                labels={'hlaup_id': 'Hlaup ID', y_axis: y_label}
            )
        
        # Virkja hover og sýna punktana
        fig.update_traces(mode='lines+markers')
        return fig

 
    # Tafla sem sýnir tímatölur (Time) fyrir valin hlaupa_id
    @output
    @render.table
    def time_table():
        selected_length = input.length_select()
        ids_str = summary_data[summary_data['Length'] == selected_length]["IDs"].values[0]
        filtered_data = get_filtered_data_for_ids(hlaup_data, ids_str)
        
        if 'Time' in filtered_data.columns and not filtered_data['Time'].isnull().all():
            # Breyta 'Time' í 'HH:MM:SS' snið ef það er ekki nú þegar þannig
            if filtered_data['Time'].dtype == 'object':
                try:
                    filtered_data['Time_delta'] = pd.to_timedelta(filtered_data['Time'])
                except:
                    filtered_data['Time_delta'] = pd.to_timedelta('00:' + filtered_data['Time'])
            else:
                filtered_data['Time_delta'] = pd.to_timedelta(filtered_data['Time'], unit='s')
            
            # Sýna 'hlaup_id' og 'Time_delta' í töflunni
            filtered_data['Time_formatted'] = filtered_data['Time_delta'].astype(str)
            return filtered_data[['hlaup_id', 'Time_formatted']]
        else:
            return filtered_data[['hlaup_id', 'Laps']].dropna()

# Keyra Shiny appið
app = App(app_ui, server)
