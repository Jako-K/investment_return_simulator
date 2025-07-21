import FreeSimpleGUI as sg
import seaborn; seaborn.set_style("whitegrid")
from matplotlib.dates import DateFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

def get_plot_frame():
    layout =[
        [
            sg.Checkbox("Netto", default=True, key="-plot_netto-"),
            sg.Checkbox("Total skat", default=True, key="-plot_skat-"),
            sg.Checkbox("Fortjeneste", default=True, key="-plot_fortjeneste-"),
            sg.Checkbox("Indbetaling", default=True, key="-plot_indbetaling-"),
            sg.Checkbox("Kurtage", default=True, key="-plot_kurtage-"),
            sg.Checkbox("Admin. omkostninger", default=True, key="-plot_admin-"),
            sg.Checkbox("Log-y", default=True, key="-plot_logy-")
        ],
        [sg.HorizontalSeparator()],
        [sg.Canvas(key="-CANVAS-")]
    ]
    return sg.Frame(title=f"Plot", element_justification="center", font=(sg.DEFAULT_FONT, 15, "bold"), pad=(20, 20), size=(1100, 600), border_width=4, layout=layout)


def get_buttons(config):
    return[
      sg.Button("Plot", key="-PLOT-", button_color="green", size=config.button_size),
      sg.Button("Optimize", key="-OPTIMIZE-", button_color="orange", size=config.button_size)
    ]

def get_user_input(config):
    layout = [
        [sg.Text('Startkapital', size=config.TW),               sg.InputText(10_000, size=config.IW, key="-start-"), sg.Text("DKK")],
        [sg.Text('Investeringsperiode', size=config.TW),        sg.InputText(20, size=config.IW, key="-period-"), sg.Text("År")],
        [sg.Text('Investeringsinterval', size=config.TW),       sg.DropDown(default_value=2, readonly=True, size=config.IW, key="-interval-", values=config.investment_intervals), sg.Text("Måned")],
        [sg.Text('Investering pr. år', size=config.TW),         sg.InputText(2000 * 12, size=config.IW, key="-investment-"), sg.Text("DKK")],
        [sg.Text('Kurtage pr. investering', size=config.TW),    sg.InputText(7.43 * 10.0, size=config.IW, key="-commission-"), sg.Text("DKK")], # NOTE: Nordnet 2022 min. kurtage er 10 Euro
        [sg.Text('Kurtage pr. 1000 kr.', size=config.TW),       sg.InputText(round(1.345 * 7.43), size=config.IW, key="-commission_per_1000-"), sg.Text("DKK")],  # NOTE: Nordnet 2022 tager ca. 1 EU per 100 Euro
        [sg.Text('Estimeret årligt afkast', size=config.TW),    sg.InputText(7.0, size=config.IW, key="-return_rate-"), sg.Text("%")],
        [sg.Text('Estimeret årlig inflation', size=config.TW),  sg.InputText(2.0, size=config.IW, key="-inflation_rate-"), sg.Text("%")],
        [sg.Text('Admin. omkostninger', size=config.TW),        sg.InputText(0.1, size=config.IW, key="-expense_ratio-"), sg.Text("ÅOP")],
        [
            sg.Text('Beskatningstype', size=(config.IW[0]+1, config.IW[1])),
            sg.DropDown(size=config.IW, readonly=True, key="-tax_type-", default_value=config.tax_types[2], values=config.tax_types, enable_events=True),
            sg.Checkbox("Geninvester", tooltip="Den skat der ville have været betalt årligt ved brug af lagerbeskatning geninvesteres.", key="-reinvest-", default=True, visible=False)
        ],
        [
            sg.Button("Plot", key="-PLOT-", button_color="green", auto_size_button=True, size=config.button_size, pad=config.button_pad),
            sg.Button("Optimize", key="-OPTIMIZE-", button_color="#ED820E", size=config.button_size, pad=config.button_pad)
        ]
    ]

    return sg.Frame(title=f"Investering", font=(sg.DEFAULT_FONT, 15, "bold"), pad=(20, 20), size=(450, config.upper_frame_height), border_width=4, layout=layout)


def init_window_functionality(config, window):
    canvas = window[f"-CANVAS-"]

    # Create matplotlib stuff
    fig = plt.Figure(facecolor='#e3e3e3', figsize=(13, 12))
    fig.add_subplot(111)
    ax = fig.get_axes()[0]
    ax.xaxis.set_major_formatter(DateFormatter("%d-%m-%Y"))

    # Create a canvas to draw matplotlib plot on
    figure_canvas_agg = FigureCanvasTkAgg(fig, canvas.TKCanvas)
    fig.tight_layout()

    # Update config file with all objects necessary for updating the plot
    config.plot_info = {"fig": fig, "ax": ax, "canvas_fig": figure_canvas_agg}


def get_table(config):
    layout = [[
        sg.Table(
            [[]],
            key="-table-",
            headings=["Beskrivelse", "Værdi", "Værdi m. inflation"],
            justification="left",
            auto_size_columns=False,
            col_widths=[20,20,20],
            num_rows=25,
            alternating_row_color = "#D1D1D9"
        )
    ]]
    return sg.Frame(title=f"Statistik", element_justification="center", font=(sg.DEFAULT_FONT, 15, "bold"), pad=(20, 20), size=(600, config.upper_frame_height), border_width=4, layout=layout)


def get_application_layout(config):
    # User defined parameters
    s = sg.Column([
        [get_user_input(config), get_table(config)]
    ])
    layout = [[s], [get_plot_frame()]]
    return layout
