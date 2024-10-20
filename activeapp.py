import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

# Hlaða inn gögnunum úr báðum skrám
def load_data():
    summary_data = pd.read_csv("CSV/siggi_hlaup_summary.csv")
    hlaup_data = pd.read_csv("CSV/siggi_hlaup.csv")
    return summary_data, hlaup_data

# Fall sem tengir gögnin á grundvelli 'IDs' og 'hlaupa_id'
def get_filtered_data_for_ids(hlaup_data, ids_str):
    # Skipta 'IDs' strengnum upp í lista af ID númerum
    ids_list = ids_str.split(", ")
    ids_list = [int(id_) for id_ in ids_list]  # Breyta í int ef ID-in eru heiltölur
    
    # Sía gögnin þannig að þau innihaldi aðeins valin 'hlaupa_id'
    filtered_data = hlaup_data[hlaup_data['hlaup_id'].isin(ids_list)]
    return filtered_data

# UI - Notendaviðmót
app_ui = ui.page_fluid(
    ui.h2("Sigurjón Ernir á Timataka.net"),
    
    # Dropdown fyrir að velja Length
    ui.input_select("length_select", "Veldu hlaup:", choices=[]),
    
    # Bæta við gagnvirku kökuriti
    output_widget("pie_chart"),
    
    # Slider til að velja fjölda hlaupa í rank_plot línuritinu
    ui.input_slider("num_races", "Fjöldi hlaupa:", min=5, max=100, value=10),
    
    # Layout með tveimur dálkum, þar sem línuritið tekur meira pláss en taflan
    ui.layout_columns(
        output_widget("line_chart"),    # Línurit sem sýnir tíma eða hringir
        ui.output_table("time_table"),  # Tafla sem sýnir tíma fyrir ID
        col_widths=[8, 4]  # Línuritið fær 8/12 hluta af plássinu, taflan 4/12
    ),
    
    # Output fyrir rank_plot línuritið
    output_widget("rank_plot")  # Bætum við línuritinu fyrir Rank eftir hlaupa_id
)

# Server - Gagnavinnsla
def server(input, output, session):
    summary_data, hlaup_data = load_data()

    # Gera lengdirnar úr 'Length' dálknum aðgengilegar fyrir dropdown
    @reactive.Effect
    def update_dropdown():
        ui.update_select("length_select", choices=list(summary_data['Length']))

    # Gagnvirkt kökurit
    @output
    @render_plotly
    def pie_chart():
        fig = px.pie(summary_data, values='Count', names='Length', title="Hlutfall hlaupa eftir lengd")
        return fig

    # Línurit fyrir hlaupatíma eða hringi í lækkandi röð fyrir hlaup_id
    @output
    @render_plotly
    @reactive.event(input.length_select)
    def line_chart():
        selected_length = input.length_select()
        ids_str = summary_data[summary_data['Length'] == selected_length]["IDs"].values[0]
        filtered_data = get_filtered_data_for_ids(hlaup_data, ids_str)

        if 'Time' in filtered_data.columns and not filtered_data['Time'].isnull().all():
            if filtered_data['Time'].dtype == 'object':
                try:
                    filtered_data['Time_in_seconds'] = pd.to_timedelta(filtered_data['Time']).dt.total_seconds()
                except:
                    filtered_data['Time_in_seconds'] = pd.to_timedelta('00:' + filtered_data['Time']).dt.total_seconds()
            else:
                filtered_data['Time_in_seconds'] = filtered_data['Time']

            y_axis = 'Time_in_seconds'
            y_label = 'Tími (HH:MM:SS)'

            fig = px.line(
                filtered_data,
                x='hlaup_id',
                y=y_axis,
                title=f"Framvinda: Tími fyrir {selected_length}",
                labels={'hlaup_id': 'Hlaup ID', y_axis: y_label}
            )
            
            # Snúa x-ás í lækkandi röð
            fig.update_layout(xaxis=dict(autorange="reversed"))
            
            # Breyta y-ás merkimiðum til að sýna tíma í HH:MM:SS sniði
            hover_text = [pd.to_datetime(seconds, unit='s').strftime('%H:%M:%S') for seconds in filtered_data[y_axis]]
            fig.update_traces(hovertemplate='Hlaup ID: %{x}<br>Tími: %{text}', text=hover_text)
        else:
            y_axis = 'Laps'
            y_label = 'Fjöldi hringja'
            fig = px.line(filtered_data, x='hlaup_id', y=y_axis, title=f"Hringir fyrir {selected_length}",
                          labels={'hlaup_id': 'Hlaup ID', y_axis: y_label})

            # Snúa x-ás í lækkandi röð
            fig.update_layout(xaxis=dict(autorange="reversed"))

        fig.update_traces(mode='lines+markers')
        return fig

    # Tafla sem sýnir tíma fyrir valin hlaupa_id
    @output
    @render.table
    def time_table():
        selected_length = input.length_select()
        ids_str = summary_data[summary_data['Length'] == selected_length]["IDs"].values[0]
        filtered_data = get_filtered_data_for_ids(hlaup_data, ids_str)

        if 'Time' in filtered_data.columns and not filtered_data['Time'].isnull().all():
            if filtered_data['Time'].dtype == 'object':
                try:
                    filtered_data['Time_delta'] = pd.to_timedelta(filtered_data['Time'])
                except:
                    filtered_data['Time_delta'] = pd.to_timedelta('00:' + filtered_data['Time'])
            else:
                filtered_data['Time_delta'] = pd.to_timedelta(filtered_data['Time'], unit='s')

            filtered_data['Time_formatted'] = filtered_data['Time_delta'].astype(str)
            return filtered_data[['hlaup_id', 'Time_formatted']]
        else:
            return filtered_data[['hlaup_id', 'Laps']].dropna()

    # Gagnvirkt línurit sem teiknar 'Rank' eftir 'hlaupa_id'
    @output
    @render_plotly
    @reactive.event(input.num_races)
    def rank_plot():
        filtered_data = hlaup_data.nlargest(input.num_races(), 'hlaup_id')

        fig = px.line(filtered_data, x='hlaup_id', y='Rank', title="Race Rank by Hlaupa ID (Descending Order)",
                      labels={'hlaup_id': 'Race ID', 'Rank': 'Rank'})

        fig.update_layout(xaxis=dict(autorange="reversed"))
        return fig

# Keyra Shiny appið
app = App(app_ui, server)
