import sqlite3
import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

# Function to load data from SQLite database
def load_data_from_db():
    # Connect to the SQLite database
    conn = sqlite3.connect('siggi_timataka.db')

    # Load data into DataFrames using SQL queries
    summary_data = pd.read_sql_query("SELECT * FROM siggi_hlaup_summary", conn)
    hlaup_data = pd.read_sql_query("SELECT * FROM timataka", conn)
    ar_data = pd.read_sql_query("SELECT * FROM ar_id_table", conn)

    # Close the database connection
    conn.close()
    
    return summary_data, hlaup_data, ar_data

# Function that filters data based on 'IDs' and 'hlaup_id'
def get_filtered_data_for_ids(hlaup_data, ids_str):
    ids_list = ids_str.split(", ")
    ids_list = [int(id_) for id_ in ids_list]
    filtered_data = hlaup_data[hlaup_data['hlaup_id'].isin(ids_list)]
    # Sort data by 'hlaup_id' in ascending order
    filtered_data = filtered_data.sort_values('hlaup_id')
    return filtered_data

# UI - Notendaviðmót
app_ui = ui.page_fluid(
    ui.tags.style("""
        table.dataframe {
            width: 100%;
            border-collapse: collapse;
        }
        table.dataframe th, table.dataframe td {
            border: 1px solid #ddd;
            padding: 8px;
        }
        table.dataframe tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        table.dataframe tr:hover {
            background-color: #ddd;
        }
        table.dataframe th {
            padding-top: 12px;
            padding-bottom: 12px;
            text-align: left;
            background-color: #4CAF50;
            color: white;
        }
    """),
    ui.navset_tab(
        ui.nav_panel(
            "Heim",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.h3("Valmöguleikar"),
                    ui.input_slider("num_races", "Fjöldi hlaupa í Rank línuriti:", min=5, max=100, value=10),
                    ui.input_radio_buttons("chart_type", "Veldu grafgerð:", choices=['Pie Chart', 'Bar Chart'], selected='Pie Chart'),
                ),
                ui.div(
                    output_widget("home_chart"),
                    output_widget("rank_plot"),
                )
            )
        ),
        ui.nav_panel(
            "Bætingar",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.input_select("length_select", "Veldu hlaup:", choices=[]),
                ),
                ui.div(
                    ui.h2("Bætingar yfir tíma"),
                    ui.row(
                        ui.column(6, output_widget("improvement_line_chart")),
                        ui.column(6, ui.output_table("improvement_time_table"))
                    )
                )
            )
        ),
        ui.nav_panel(
            "Gögn",
            ui.h2("Gögn um hlaup"),
            ui.input_select("table_select", "Veldu töflu:", choices=['hlaup_data', 'summary_data', 'ar_data']),
            ui.output_table("selected_data_table")
        ),
        ui.nav_panel(
            "Um",
            ui.h2("Um þetta forrit"),
            ui.p("Þetta er fágað Shiny forrit sem sýnir gögn um hlaup Sigurjóns Ernis frá Timataka.net.")
        ),
    ),
    title="Sigurjón Ernir á Timataka.net",
)

# Server - Bakendinn
def server(input, output, session):
    # Hlaða gögnum úr SQLite gagnagrunninum
    summary_data, hlaup_data, ar_data = load_data_from_db()

    # Endurnefna 'id' í 'hlaup_id' ef nauðsyn krefur
    if 'id' in ar_data.columns:
        ar_data = ar_data.rename(columns={'id': 'hlaup_id'})
    elif 'hlaupID' in ar_data.columns:
        ar_data = ar_data.rename(columns={'hlaupID': 'hlaup_id'})
    else:
        # Ef 'hlaup_id' dálkurinn finnst ekki
        raise KeyError("'hlaup_id' column not found in ar_data")

    # Gakktu úr skugga um að 'hlaup_id' sé til staðar í hlaup_data
    if 'hlaup_id' not in hlaup_data.columns:
        raise KeyError("'hlaup_id' column not found in hlaup_data")

    # Gera 'hlaup_id' dálkinn að sama gagnagerð
    hlaup_data['hlaup_id'] = hlaup_data['hlaup_id'].astype(int)
    ar_data['hlaup_id'] = ar_data['hlaup_id'].astype(int)

    # Sameina hlaup_data og ar_data til að fá 'ar' fyrir hvert 'hlaup_id'
    hlaup_data = hlaup_data.merge(ar_data[['hlaup_id', 'ar']], on='hlaup_id', how='left')

    # Fall til að formatta sekúndur í hh:mm:ss
    def format_seconds(total_seconds):
        total_seconds = int(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    # Uppfæra valmöguleika í dropdown þegar forritið byrjar
    @reactive.Effect
    def update_dropdown():
        ui.update_select("length_select", choices=list(summary_data['Length']))

    # Sía gögnin eftir völdu hlaupi
    @reactive.Calc
    def filtered_data():
        selected_length = input.length_select()
        ids_str_series = summary_data[summary_data['Length'] == selected_length]["IDs"]
        if ids_str_series.empty:
            return pd.DataFrame()
        ids_str = ids_str_series.values[0]
        data = get_filtered_data_for_ids(hlaup_data, ids_str)
        return data

    # Línurit fyrir 'Heim' flipann
    @output
    @render_plotly
    def home_chart():
        chart_type = input.chart_type()
        if chart_type == 'Pie Chart':
            fig = px.pie(summary_data, values='Count', names='Length', title="Hlutfall hlaupa eftir lengd")
        else:
            fig = px.bar(summary_data, x='Length', y='Count', title="Fjöldi hlaupa eftir lengd")
        return fig

    # Línurit fyrir bætingar yfir tíma
    @output
    @render_plotly
    def improvement_line_chart():
        data = filtered_data()
        if data.empty:
            return px.line(title="Engin gögn til að sýna.")

        # Athuga hvort 'Time' gögn séu til staðar
        if 'Time' in data.columns and not data['Time'].isnull().all():
            # Umbreyta 'Time' í sekúndur
            if data['Time'].dtype == 'object':
                try:
                    data['Time_in_seconds'] = pd.to_timedelta(data['Time']).dt.total_seconds()
                except:
                    data['Time_in_seconds'] = pd.to_timedelta('00:' + data['Time']).dt.total_seconds()
            else:
                data['Time_in_seconds'] = data['Time'].astype(float)

            # Umbreyta 'ar' og 'hlaup_id' í Int64 til að leyfa NaN gildi
            data['ar'] = data['ar'].astype('Int64')
            data['hlaup_id'] = data['hlaup_id'].astype('Int64')
            data = data.dropna(subset=['hlaup_id', 'Time_in_seconds'])
            data = data.sort_values('hlaup_id')

            # Línurit með 'hlaup_id' á x-ásnum og 'Time_in_seconds' á y-ásnum
            fig = px.line(
                data,
                x='hlaup_id',
                y='Time_in_seconds',
                title=f"Framvinda: Tími fyrir {input.length_select()}",
                labels={'hlaup_id': 'Hlaup ID', 'Time_in_seconds': 'Tími (sekúndur)'}
            )
            fig.update_traces(mode='lines+markers')

            # Bæta við formattaðri tímalengd í sveima upplýsingum
            hover_text = data['Time_in_seconds'].apply(format_seconds)
            fig.update_traces(hovertemplate='Hlaup ID: %{x}<br>Tími: %{text}', text=hover_text)

            # Snúa x-ásnum til að hafa hlaup_id í lækkandi röð
            fig.update_layout(xaxis=dict(autorange='reversed'))

            return fig
        else:
            # Reyna að finna 'Laps' dálkinn
            laps_col = None
            for col in data.columns:
                if col.lower() == 'Laps':
                    laps_col = col
                    break
            if laps_col and not data[laps_col].isnull().all():
                # Fyrir 'Laps' gögn
                data['ar'] = data['ar'].astype('Int64')
                data['hlaup_id'] = data['hlaup_id'].astype('Int64')
                data = data.dropna(subset=['hlaup_id', laps_col])
                data = data.sort_values('hlaup_id')

                fig = px.line(
                    data,
                    x='hlaup_id',
                    y=laps_col,
                    title=f"Hringir fyrir {input.length_select()}",
                    labels={'hlaup_id': 'Hlaup ID', laps_col: 'Fjöldi hringja'}
                )
                fig.update_traces(mode='lines+markers')

                # Snúa x-ásnum til að hafa hlaup_id í lækkandi röð
                fig.update_layout(xaxis=dict(autorange='reversed'))

                return fig
            else:
                return px.line(title="Engin gögn til að sýna.")

    # Tafla sem sýnir tíma eða hringi með 'ar' og 'hlaup_id'
    @output
    @render.table
    def improvement_time_table():
        data = filtered_data()
        if data.empty:
            return pd.DataFrame({"Skilaboð": ["Engin gögn til að sýna."]})

        if 'Time' in data.columns and not data['Time'].isnull().all():
            # Umbreyta 'Time' í sekúndur
            if data['Time'].dtype == 'object':
                try:
                    data['Time_in_seconds'] = pd.to_timedelta(data['Time']).dt.total_seconds()
                except:
                    data['Time_in_seconds'] = pd.to_timedelta('00:' + data['Time']).dt.total_seconds()
            else:
                data['Time_in_seconds'] = data['Time'].astype(float)

            # Umbreyta 'ar' og 'hlaup_id' í Int64 til að leyfa NaN gildi
            data['ar'] = data['ar'].astype('Int64')
            data['hlaup_id'] = data['hlaup_id'].astype('Int64')
            data = data.dropna(subset=['ar', 'hlaup_id', 'Time_in_seconds'])

            # Nota formattaða tímalengd
            data['Time_formatted'] = data['Time_in_seconds'].apply(format_seconds)

            return data[['ar', 'hlaup_id', 'Time_formatted']].reset_index(drop=True)
        else:
            # Reyna að finna 'Laps' dálkinn
            laps_col = None
            for col in data.columns:
                if col.lower() == 'Laps':
                    laps_col = col
                    break
            if laps_col and not data[laps_col].isnull().all():
                # Fyrir 'Laps' gögn
                data['ar'] = data['ar'].astype('Int64')
                data['hlaup_id'] = data['hlaup_id'].astype('Int64')
                data = data.dropna(subset=['ar', 'hlaup_id', laps_col])
                return data[['ar', 'hlaup_id', laps_col]].reset_index(drop=True)
            else:
                return pd.DataFrame({"Skilaboð": ["Engin gögn til að sýna."]})

    # Línurit fyrir Rank eftir hlaup_id
    @output
    @render_plotly
    def rank_plot():
        filtered_rank_data = hlaup_data.nlargest(input.num_races(), 'hlaup_id')
        filtered_rank_data = filtered_rank_data.sort_values('hlaup_id')

        fig = px.line(
            filtered_rank_data,
            x='hlaup_id',
            y='Rank',
            title="Röðun í hlaupum eftir hlaup ID",
            labels={'hlaup_id': 'Hlaup ID', 'Rank': 'Röðun'}
        )
        fig.update_traces(mode='lines+markers')

        # Snúa x-ásnum til að hafa hlaup_id í lækkandi röð
        fig.update_layout(xaxis=dict(autorange='reversed'))

        return fig

    # Úttak fyrir valda töflu í 'Gögn' flipanum
    @output
    @render.table
    def selected_data_table():
        selected_table = input.table_select()
        if selected_table == 'hlaup_data':
            return hlaup_data.sort_values('hlaup_id', ascending=True)
        elif selected_table == 'summary_data':
            return summary_data
        elif selected_table == 'ar_data':
            return ar_data
        else:
            return pd.DataFrame()

# Keyra Shiny appið
app = App(app_ui, server)
