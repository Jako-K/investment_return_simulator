from gui_layout import get_application_layout, init_window_functionality
from utils import GlobalConfig, update_plot, calculate_return, format_df, is_enter_key, update_table, do_warning_popup
import FreeSimpleGUI as sg


if __name__ == "__main__":
    sg.theme('LightGray6')
    config = GlobalConfig()
    layout = get_application_layout(config)
    window = sg.Window('Simple data entry window', layout, return_keyboard_events=True).finalize()
    init_window_functionality(config, window)

    while True:
        event, values = window.read()

        ########
        # Checks
        ########

        if values is None:
            break
        elif values["-tax_type-"] == "Realiseringsbeskatning":
            window["-reinvest-"].update(visible=True)
        else:
            window["-reinvest-"].update(visible=False)

        ########
        # Events
        ########
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        # Handle the plot button on each page
        elif (event == "-PLOT-") or is_enter_key(event) or (event == "-OPTIMIZE-"):
            if (values["-tax_type-"] == "Aktiesparekonto") and (float(values["-start-"]) > config.aktiesparekonto_max):
                do_warning_popup(window, f"Startkapitalen for en aktiesparekonto kan ikke overgå max-grænsen på {config.aktiesparekonto_max} DKK")
                continue

            # Optimize
            if event == "-OPTIMIZE-":
                best_netto_income = 0
                for i, interval in enumerate(config.investment_intervals):
                    values["-interval-"] = str(interval)
                    df = calculate_return(config, values, values["-tax_type-"])
                    netto_income = df["netto_income"].iloc[-1].item()
                    if netto_income <= best_netto_income:
                        values["-interval-"] = str(config.investment_intervals[i - 1])
                        window["-interval-"].update(str(config.investment_intervals[i - 1]))
                        break
                    best_netto_income = netto_income


            df = calculate_return(config, values, values["-tax_type-"])
            df = format_df(df, values)

            update_plot(df.copy(), config, values)
            update_table(df, window, values)
            window["-table-"].update(select_rows=[1, 10, 13])

    window.close()

# The input data looks like a simple list
# when automatic numbered
