import sqlite3
import pandas as pd
import plotly.express as px
import re
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

# Function to convert time string to seconds
def time_to_seconds(time_str):
    try:
        return pd.to_timedelta(time_str).total_seconds()
    except:
        try:
            return pd.to_timedelta('00:' + time_str).total_seconds()
        except:
            return None

# Function to format seconds into 'HH:MM:SS' format
def format_seconds_to_hhmmss(seconds):
    if pd.isnull(seconds):
        return None
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:02d}"

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
            "Hraði",
            ui.layout_sidebar(
                ui.sidebar(
                    ui.h3("Veldu vegalengd"),
                    ui.input_radio_buttons(
                        "distance_range",
                        "Veldu bil:",
                        choices={
                            "1": "1KM - 9.9KM",
                            "2": "10KM - 19.9KM",
                            "3": "20KM - 39.9KM",
                            "4": "40KM - 100KM",
                            "5": "Allar vegalengdir"
                        },
                        selected="1"
                    )
                ),
                ui.div(
                    output_widget("speed_line_chart")
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

    # --- Nýr kóði til að nota lengdartöfluna ---

    # Búa til streng með töflunni
    length_table_str = """
Length	Count	IDs
10KM	8	1002, 1145, 1170, 1223, 1229, 1260, 74, 808
12KM	1	175
14KM	1	1214
17.5KM	3	1072, 1219, 566
17.6KM	1	196
19KM	1	711
21KM	4	1076, 66, 69, 96
22KM	0	1003
23KM	1	828
24KM	2	1005, 554
27KM	1	1167
28KM	1	748
30.6KM	1	557
32.7KM	2	738, 924
32KM	1	13
37KM	1	36
42KM	6	222, 227, 655, 837, 963, 974
50KM	3	210, 61, 679
53KM	1	237
55KM	1	487
5KM	4	1110, 1156, 185, 261
63KM	1	3
8.3KM	1	573
Backyard	3	317, 360, 469
Puffin	4	110, 375, 585, 617
Unknown	4	127, 437, 525, 548
"""

    # Lesa strenginn inn í DataFrame
    from io import StringIO
    length_df = pd.read_csv(StringIO(length_table_str), sep='\t')

    # Útvíkka 'IDs' dálkinn til að fá einn 'hlaup_id' á hverja línu
    length_df_expanded = length_df.drop('Count', axis=1).copy()
    length_df_expanded = length_df_expanded.assign(
        hlaup_id=length_df_expanded['IDs'].str.split(', ')
    ).explode('hlaup_id')
    length_df_expanded = length_df_expanded.drop('IDs', axis=1)
    length_df_expanded['hlaup_id'] = length_df_expanded['hlaup_id'].astype(int)

    # Búa til 'Distance_m' dálk úr 'Length'
    def length_to_meters(length_str):
        try:
            match = re.search(r'(\d+(?:\.\d+)?)', length_str)
            if match:
                distance_km = float(match.group(1))
                distance_m = distance_km * 1000
                return distance_m
            else:
                return None
        except:
            return None

    length_df_expanded['Distance_m'] = length_df_expanded['Length'].apply(length_to_meters)

    # Sameina við hlaup_data á 'hlaup_id'
    hlaup_data = hlaup_data.merge(length_df_expanded[['hlaup_id', 'Distance_m']], on='hlaup_id', how='left')

    # --- Lok nýs kóða ---

    # Umbreyta 'Time' í sekúndur
    hlaup_data['Time_in_seconds'] = hlaup_data['Time'].apply(time_to_seconds)

    # Reikna hraða (m/s)
    hlaup_data['Speed_m_s'] = hlaup_data.apply(
        lambda row: row['Distance_m'] / row['Time_in_seconds'] if pd.notnull(row['Distance_m']) and pd.notnull(row['Time_in_seconds']) and row['Time_in_seconds'] > 0 else None,
        axis=1
    )

    # Fall til að formatta sekúndur í 'HH:MM:SS' snið
    def format_seconds(total_seconds):
        if pd.isnull(total_seconds):
            return None
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
            data['Time_in_seconds'] = data['Time'].apply(time_to_seconds)

            # Umbreyta 'ar' og 'hlaup_id' í Int64 til að leyfa NaN gildi
            data['ar'] = data['ar'].astype('Int64')
            data['hlaup_id'] = data['hlaup_id'].astype('Int64')
            data = data.dropna(subset=['hlaup_id', 'Time_in_seconds'])
            data = data.sort_values('hlaup_id')

            # Bæta við dálki með tíma í 'HH:MM:SS' sniði
            data['Time_formatted'] = data['Time_in_seconds'].apply(format_seconds_to_hhmmss)

            # Línurit með 'hlaup_id' á x-ásnum og 'Time_in_seconds' á y-ásnum
            fig = px.line(
                data,
                x='hlaup_id',
                y='Time_in_seconds',
                title=f"Framvinda: Tími fyrir {input.length_select()}",
                labels={'hlaup_id': 'Hlaup ID', 'Time_in_seconds': 'Tími (HH:MM:SS)'}
            )
            fig.update_traces(mode='lines+markers')

            # Bæta við formattaðri tímalengd í sveimaupplýsingum
            fig.update_traces(
                hovertemplate='Hlaup ID: %{x}<br>Tími: %{text}',
                text=data['Time_formatted']
            )

            # Sérsníða y-ásinn til að sýna tímann í 'HH:MM:SS' sniði
            y_ticks = sorted(data['Time_in_seconds'].unique())
            y_ticktext = [format_seconds_to_hhmmss(t) for t in y_ticks]

            fig.update_yaxes(
                tickmode='array',
                tickvals=y_ticks,
                ticktext=y_ticktext
            )

            # Snúa x-ásnum til að hafa hlaup_id í lækkandi röð
            fig.update_layout(xaxis=dict(autorange='reversed'))

            return fig
        else:
            # Reyna að finna 'Laps' dálkinn
            laps_col = None
            for col in data.columns:
                if col.lower() == 'laps':
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
            data['Time_in_seconds'] = data['Time'].apply(time_to_seconds)

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
                if col.lower() == 'laps':
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

    # Reactive filter fyrir vegalengd fyrir 'Hraði' flipann
    @reactive.Calc
    def speed_filtered_data():
        distance_range = input.distance_range()
        if distance_range == "1":
            min_dist, max_dist = 1 * 1000, 9.9 * 1000
        elif distance_range == "2":
            min_dist, max_dist = 10 * 1000, 19.9 * 1000
        elif distance_range == "3":
            min_dist, max_dist = 20 * 1000, 39.9 * 1000
        elif distance_range == "4":
            min_dist, max_dist = 40 * 1000, 100 * 1000
        elif distance_range == "5":
            min_dist, max_dist = None, None  # Engin síun
        else:
            min_dist, max_dist = 0, float('inf')

        data = hlaup_data.dropna(subset=['Distance_m', 'Time_in_seconds', 'Speed_m_s'])

        if min_dist is not None and max_dist is not None:
            data = data[(data['Distance_m'] >= min_dist) & (data['Distance_m'] <= max_dist)]
        # Ef min_dist og max_dist eru None, síum við ekki eftir vegalengd

        data = data.sort_values('hlaup_id')
        return data

    # Línurit fyrir hraða í 'Hraði' flipanum
    @output
    @render_plotly
    def speed_line_chart():
        data = speed_filtered_data()
        if data.empty:
            return px.scatter(title="Engin gögn til að sýna.")
        
        # Bæta við formattaðri vegalengd og tíma
        data['Distance_km'] = data['Distance_m'] / 1000
        data['Time_formatted'] = data['Time_in_seconds'].apply(format_seconds_to_hhmmss)
        
        distance_range = input.distance_range()

        if distance_range == "5":
            # Fyrir allar vegalengdir, búa til punktarit með hallalínu
            fig = px.scatter(
                data,
                x='hlaup_id',
                y='Speed_m_s',
                trendline='ols',
                title="Hraði (m/s) fyrir öll hlaup",
                labels={'hlaup_id': 'Hlaup ID', 'Speed_m_s': 'Hraði (m/s)'},
                hover_data={'Name': True, 'Distance_km': True, 'Time_formatted': True},
            )
            fig.update_traces(
                hovertemplate='Hlaup ID: %{x}<br>Nafn: %{customdata[0]}<br>Vegalengd: %{customdata[1]:.2f} km<br>Tími: %{customdata[2]}<br>Hraði: %{y:.2f} m/s'
            )
        else:
            # Fyrir ákveðin vegalengdarbil, halda áfram með línurit
            fig = px.line(
                data,
                x='hlaup_id',
                y='Speed_m_s',
                title="Hraði (m/s) eftir hlaup ID",
                labels={'hlaup_id': 'Hlaup ID', 'Speed_m_s': 'Hraði (m/s)'},
                hover_data={'Name': True, 'Distance_km': True, 'Time_formatted': True},
                markers=True
            )
            fig.update_traces(
                hovertemplate='Hlaup ID: %{x}<br>Nafn: %{customdata[0]}<br>Vegalengd: %{customdata[1]:.2f} km<br>Tími: %{customdata[2]}<br>Hraði: %{y:.2f} m/s'
            )

        # Snúa x-ásnum til að hafa hlaup_id í lækkandi röð
        fig.update_layout(xaxis=dict(autorange='reversed'))
        return fig

# Keyra Shiny appið
app = App(app_ui, server)
