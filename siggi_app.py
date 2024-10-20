import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
from shiny import App, render, ui

# Tengjast gagnagrunninum
conn = sqlite3.connect("siggi_timataka.db")

# Hlaða gögnin úr rank_table og siggi_hlaup_summary
rank_df = pd.read_sql_query("SELECT Rank FROM rank_table", conn)
summary_df = pd.read_sql_query("SELECT Length, Count, IDs FROM siggi_hlaup_summary", conn)

# Loka tengingunni
conn.close()

# Hreinsa tómar eða ógildar raðir úr 'Rank' dálknum
rank_df = rank_df[rank_df['Rank'].apply(pd.to_numeric, errors='coerce').notnull()]

# Breyta 'Rank' dálknum í tölur
rank_df['Rank'] = pd.to_numeric(rank_df['Rank'])

# Búa til tilbúna "Time" dálk með smá millibili fyrir Rank línuritið
rank_df['Time'] = range(1, len(rank_df) + 1)

# Helper function to convert time strings to seconds
def convert_to_seconds(time_str):
    try:
        if '.' in time_str:  # Handle times with fractional seconds like '00:36:16.10'
            h, m, s = map(float, time_str.split(':'))
        else:
            h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
    except Exception:
        return None

# Shiny app uppsetning
app_ui = ui.page_fluid(
    ui.h2("Mælaborð fyrir Sigurjón Erni"),

    # Fyrsta mælaborðið - línurit með sæti eftir tímaröð
    ui.panel_title("Sæti hlaupara með tímanum"),
    ui.output_plot("rank_plot"),

    # Annað mælaborðið - súlurit með lengdum hlaupa
    ui.panel_title("Lengdir hlaupa og fjöldi þátttaka"),
    ui.output_plot("summary_plot"),

    # Þriðja mælaborðið - Hlaupa tegund og tímarit
    ui.panel_title("Bæting eftir hlaupa tegund"),
    ui.input_select("length_choice", "Veldu hlaupa tegund", choices=list(summary_df['Length'].unique())),
    ui.output_plot("improvement_plot")
)

# Server hlutinn fyrir Shiny appið
def server(input, output, session):
    # Línurit - Sæti eftir tímaröð
    @output
    @render.plot
    def rank_plot():
        plt.figure(figsize=(10, 6))
        plt.plot(rank_df['Time'], rank_df['Rank'], marker='o')
        plt.xlabel('Tími (tilbúið)')
        plt.ylabel('Sæti')
        plt.title('Sæti hlaupara eftir tímaröð')
        plt.gca().invert_yaxis()  # Sætin verða betri ef við snúum þeim við
        plt.grid(True)
        return plt.gcf()

    # Súlurit - Lengdir hlaupa og fjöldi þátttaka
    @output
    @render.plot
    def summary_plot():
        plt.figure(figsize=(10, 6))
        plt.bar(summary_df['Length'], summary_df['Count'], color='skyblue')
        plt.xlabel('Lengdir hlaupa')
        plt.ylabel('Fjöldi þátttaka')
        plt.title('Lengdir hlaupa og fjöldi þátttaka')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        return plt.gcf()

    # Línurit - Bæting eftir hlaupa tegund
    @output
    @render.plot
    def improvement_plot():
        # Velja hlaupa tegund úr 'siggi_hlaup_summary'
        selected_length = input.length_choice()
        selected_ids = summary_df[summary_df['Length'] == selected_length]['IDs'].values[0]
        
        # Sækja 'Time' eða 'Laps' úr 'timataka' töflunni fyrir viðkomandi hlaupa IDs
        ids_list = selected_ids.split(", ")
        query = f"SELECT Time, Laps FROM timataka WHERE hlaup_id IN ({','.join(ids_list)})"
        
        conn = sqlite3.connect("siggi_timataka.db")
        timataka_df = pd.read_sql_query(query, conn)
        conn.close()

        # Umbreyta 'Time' gögnum í sekúndur og bæta við sem 'Time_in_seconds'
        timataka_df['Time_in_seconds'] = timataka_df['Time'].apply(convert_to_seconds)
        
        # Nota 'Time_in_seconds' ef það er til staðar annars 'Laps'
        timataka_df['Improvement'] = timataka_df['Time_in_seconds'].fillna(timataka_df['Laps'])
        
        # Búa til tímarað fyrir línuritið
        timataka_df = timataka_df.dropna(subset=['Improvement'])
        timataka_df['Time_series'] = range(1, len(timataka_df) + 1)
        
        # Teikna línuritið
        plt.figure(figsize=(10, 6))
        plt.plot(timataka_df['Time_series'], timataka_df['Improvement'], marker='o')
        plt.xlabel('Keppnir í tímaröð')
        plt.ylabel('Tími í sekúndum eða Laps')
        plt.title(f"Bæting í hlaupa tegund: {selected_length}")
        plt.grid(True)
        return plt.gcf()

# Setja upp app-ið
app = App(app_ui, server)
