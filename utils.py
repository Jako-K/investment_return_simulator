from datetime import datetime
import pandas as pd
import numpy as np
import FreeSimpleGUI as sg

class GlobalConfig:
    # Layout
    TW = (16,1)
    IW = (15,1)
    button_size = (15,2)
    button_pad = ((10,10),(20, 20))
    upper_frame_height = 375

    # Random
    investment_intervals = [1,2,3,4,6,12]

    # Tax info
    tax_types = ["Aktiesparekonto", "Realiseringsbeskatning", "Lagerbeskatning"]
    progression_limit = 57_200
    aktiesparekonto_tax = 0.17
    aktiesparekonto_max = 103_500
    low_tax = 0.27
    high_tax = 0.42

    # Variables
    plot_info = None


def is_enter_key(event):
    # SOURCE: https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Keyboard_ENTER_Presses_Button.py
    return event in ('\r', "special 16777220", "special 16777221")

def do_warning_popup(window, message:str, ding_sound:bool=True) -> None:
    if ding_sound: window.ding()
    sg.popup(message)


def calculate_return(config:GlobalConfig, values, tax_type:str):
    # Setup - Simple definitions
    start_capital = float(values["-start-"])
    total_investment_period_in_years = int(values["-period-"])
    time_between_investment_in_months = float(values["-interval-"])
    reoccurring_investment_amount_yearly = float(values["-investment-"])
    commission_fee_start = float(values["-commission-"])
    commission_fee_per_1000_dkk = float(values["-commission_per_1000-"])
    expense_ratio_yearly = float(values["-expense_ratio-"]) / 100
    expected_yearly_return_rate = float(values["-return_rate-"]) / 100


    # Handle reinvesting in case of "Realiseringsbeskatning" taxation
    df_lagerbeskatning = None
    if (tax_type == "Realiseringsbeskatning") and (values["-reinvest-"]):
        df_lagerbeskatning = calculate_return(config, values, tax_type="Lagerbeskatning")

    # Checks
    assert expected_yearly_return_rate > expense_ratio_yearly, "Stupid..."

    # Setup - stuff for calculations
    reoccurring_investment_amount_adjusted = reoccurring_investment_amount_yearly * (time_between_investment_in_months / 12)
    return_rate_monthly = expected_yearly_return_rate * (1/12)
    expense_ratio_monthly = expense_ratio_yearly * (1 / 12)
    commission_fee_per_transaction = commission_fee_start + (reoccurring_investment_amount_adjusted / 1000) * commission_fee_per_1000_dkk

    # Simulate investment period
    this_year = datetime.today().year
    dates = [datetime(this_year-1, 12, 12)]
    balances = [start_capital - commission_fee_per_transaction]
    earnings = [0]
    commission_fees = [commission_fee_per_transaction]
    expense_ratios = [0]
    investments = [start_capital - commission_fee_per_transaction]

    # TODO: Debug
    print(tax_type, reoccurring_investment_amount_adjusted, return_rate_monthly, expense_ratio_monthly, commission_fee_per_transaction)

    last_year = this_year + total_investment_period_in_years
    years = range(this_year, last_year + 1)
    for i, year in enumerate(years):
        extra_investment = 0
        if (df_lagerbeskatning is not None) and (i != 0) and (i != last_year):
            december_last_year = df_lagerbeskatning["date"] == f"{year-1}-12-01"
            taxes_paid_last_december = df_lagerbeskatning[december_last_year]["tax_paid"].item()
            extra_investment = taxes_paid_last_december * (time_between_investment_in_months / 12)

        for month in range(1, 13):
            # First investment
            # if (this_year == year) and (month == 1):
            #     continue

            # Interest
            account_balance = balances[-1] * (1 + return_rate_monthly - expense_ratio_monthly)
            earnings.append(account_balance - balances[-1])
            expense_ratios.append(balances[-1] * (1 + return_rate_monthly) - account_balance) # Difference between return with and without the expense ratio

            # invest this this month?
            investment, commission_paid = 0, 0
            is_investment_month = ((i*12 + month) % time_between_investment_in_months) == 0
            aktiesparekonto_max_reached = (account_balance > config.aktiesparekonto_max) and (tax_type == "Aktiesparekonto")
            if is_investment_month and (not aktiesparekonto_max_reached):
                investment = reoccurring_investment_amount_adjusted + extra_investment - commission_fee_per_transaction # Commission fees are not tax exempt and are just treated as any other purchase: https://www.berlingske.dk/privatoekonomi/kan-aktiegebyr-traekkes-fra-i-skat

                # If the maximum allowed investment is reached for the aktiesparekonto
                if (tax_type == "Aktiesparekonto") and ((account_balance + investment) > config.aktiesparekonto_max):
                    investment = config.aktiesparekonto_max - account_balance

                account_balance += investment
                commission_paid = commission_fee_per_transaction

            # Book keeping
            investments.append(investment)
            balances.append(account_balance)
            dates.append(datetime(year, month, 1))
            commission_fees.append(commission_paid)

    assert len(dates) == len(balances), f"{len(dates), len(balances)}"

    # Format in dataframe
    df = pd.DataFrame(data={
        "date": dates,
        "balance": balances,
        "earnings": earnings,
        "investment":investments,
        "commission_fee_per_transaction":commission_fees,
        "expense_ratio": expense_ratios
    })
    df["year"] = df.apply(lambda x: int(x["date"].year), 1)
    df["is_december"] = df["date"].apply(lambda x: x.month) == 12
    df["tax_paid"] = 0

    df.to_csv("./tester.csv", index=False)
    # Handle taxes and return
    df = _calculate_taxes_on_return(df, config, tax_type)
    return df


def _calculate_taxes_on_return(df, config:GlobalConfig, tax_type:str):
    def high_low_tax(amount, is_aktiesparekonto=False):
        progression_limit, aktiesparekonto_tax, low_tax, high_tax = config.progression_limit, config.aktiesparekonto_tax, config.low_tax, config.high_tax
        if is_aktiesparekonto:
            taxes = amount * aktiesparekonto_tax
        elif amount > progression_limit:
            taxes = progression_limit * low_tax + (amount - progression_limit) * high_tax
        else:
            taxes = amount * low_tax
        return taxes

    if tax_type == "Aktiesparekonto":
        yearly_taxes_paid = dict(df[["year", "earnings"]].groupby("year").sum()["earnings"].apply(high_low_tax, is_aktiesparekonto=True))
        df["tax_paid"] = df.apply(lambda x: yearly_taxes_paid[x["date"].year] if x["is_december"] else 0, 1)

    elif tax_type == "Realiseringsbeskatning":
        earnings_total = df["earnings"].sum().item()
        df.loc[len(df) - 1, "tax_paid"] = high_low_tax(earnings_total)

    elif tax_type == "Lagerbeskatning":
        yearly_taxes_paid = dict(df[["year", "earnings"]].groupby("year").sum()["earnings"].apply(high_low_tax))
        df["tax_paid"] = df.apply(lambda x: yearly_taxes_paid[x["date"].year] if x["is_december"] else 0, 1)

    df["netto_income"] = df["balance"] - df["tax_paid"]

    return df


def format_df(df, values):
    # Naming
    name_changes = {
        "date": "Dato",
        "netto_income": "Netto",
        "tax_paid": "Skat",
        "earnings": "Fortjeneste",
        "investment": "Investering",
        "commission_fee_per_transaction": "Kurtage",
        "expense_ratio": "Admin. omkostninger"
    }
    df = df.rename(columns=name_changes)

    # Accumulate the value of certain columns over time
    cumsum_cols = ["Fortjeneste", "Investering", "Kurtage", "Admin. omkostninger", "Skat"]
    df[cumsum_cols] = df[cumsum_cols].cumsum()

    # TODO: Debug
    df.to_csv("./tester_after.csv", index=False)

    return df


def update_plot(df, config, values):
    # Adjust columns to plot settings
    check_box_names = ["-plot_netto-", "-plot_skat-", "-plot_fortjeneste-", "-plot_indbetaling-", "-plot_kurtage-", "-plot_admin-"]
    col_names = ["Netto", "Skat", "Fortjeneste", "Investering", "Kurtage", "Admin. omkostninger"]
    columns_to_plot = ["Dato"] + [name for (name, is_checked) in zip(col_names, check_box_names) if values[is_checked]]
    df = df[columns_to_plot]

    # Setup plot
    fig = config.plot_info["fig"]
    ax = config.plot_info["ax"]; ax.cla()
    figure_canvas_agg = config.plot_info["canvas_fig"]

    # Plot
    color_map = {'Netto': '#1f77b4', 'Skat': '#ff7f0e', 'Fortjeneste': '#2ca02c', 'Investering': '#d62728', 'Kurtage': '#9467bd', 'Admin. omkostninger': '#8c564b'}
    colors = [color_map[name] for name in df.columns if name != "Dato"]
    df.plot(x="Dato", ax=ax, ylabel="DKK", logy=values["-plot_logy-"], color=colors)
    ax.set_xlabel("")

    # Adjust range x/y-axis (just giving it some breathing room, for some reason it is cropped exactly)
    min_, max_ = ax.get_xlim()
    padding = abs(np.mean(ax.get_xlim()) * 0.025)
    ax.set_xlim((min_ - padding, max_ + padding))
    ax.set_ylim(100, ax.get_ylim()[1])

    fig.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.95, wspace=0, hspace=0)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack()


def update_table(df, window, values):
    # Setup
    df["Fortjeneste_no_accum"] = df["Fortjeneste"].diff()
    df["Investering_no_accum"] = df["Investering"].diff()

    last_row = df.iloc[-1:, 1:]
    format_number = lambda x: "{:0,.0f}".format(x).replace(",", ".")
    last_row["Brutto"] = last_row["balance"]
    inflation = 1 + float(values["-inflation_rate-"]) / 100

    # Calculate inflation
    years_invested = max(df["Dato"]).year - min(df["Dato"]).year
    inflation_factor = 1 / (inflation ** years_invested)
    inflation_adjusted = last_row * inflation_factor

    # Percentages
    taxes_paid_percent = round(last_row["Skat"] / last_row["Brutto"] * 100, 2).item()
    commisions_percent = round((last_row["Admin. omkostninger"] + last_row["Kurtage"]) / last_row["Netto"] * 100, 3).item()
    gain_brutto_in_percent = round(last_row["Brutto"] / last_row["Investering"] * 100 - 100, 2).item()
    gain_netto_in_percent = round(last_row["Netto"] / last_row["Investering"] * 100  - 100, 2).item()
    gain_netto_infl_in_percent = round(inflation_adjusted["Netto"] / last_row["Investering"] * 100  - 100, 2).item()
    lost_to_inflation = round((last_row["Netto"] - inflation_adjusted["Netto"])/last_row["Netto"] * 100, 2).item()

    monthly_amount_10_years = round(last_row["Netto"] / 12 / 10).item()
    monthly_amount_10_years_infl = round(inflation_adjusted["Netto"] / 12 / 10).item()
    monthly_amount_20_years = round(last_row["Netto"] / 12 / 20).item()
    monthly_amount_20_years_infl = round(inflation_adjusted["Netto"] / 12 / 20).item()

    print(df.columns)
    # Update table
    names = ["Brutto", "Netto", "Skat", "Fortjeneste", "Investering", "Kurtage", "Admin. omkostninger"]
    table_data = [[name, format_number(last_row[name].item()), format_number(inflation_adjusted[name].item())] for name in names]
    table_data += [["", "", ""]]
    table_data += [["Månedlig beløb i 10 år", int(monthly_amount_10_years), int(monthly_amount_10_years_infl)]]
    table_data += [["Månedlig beløb i 20 år", int(monthly_amount_20_years), int(monthly_amount_20_years_infl)]]
    table_data += [["Månedlig profit (20 år)", int(last_row["Fortjeneste_no_accum"]), int(inflation_adjusted["Fortjeneste_no_accum"])]]
    table_data += [["", "", ""]]
    table_data += [
        ["Udvikling (Brutto)",          f"{gain_brutto_in_percent} %", "-"],
        ["Udvikling (Netto)",           f"{gain_netto_in_percent} %", "-"],
        ["Udvikling (Netto + infl.)",   f"{gain_netto_infl_in_percent} %", "-"],
        ["Skattetab (Brutto)",          f"{taxes_paid_percent} %", "-"],
        ["Inflationstab (Netto)",       f"{lost_to_inflation} %", "-"],
        ["Omkostningstab (Netto)",      f"{commisions_percent} %", "-"]
    ]

    window["-table-"].update(table_data)