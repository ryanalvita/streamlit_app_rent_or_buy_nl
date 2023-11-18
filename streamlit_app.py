import streamlit as st
import numpy as np
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.colors as co


# Functions
def clean_df(series):
    # Resample
    s = 1000
    l = (series.index.size - 1) * s + 1
    new_index = np.interp(np.arange(l), np.arange(l, step=s), series.index)
    series = series.reindex(index=new_index)

    # Interpolate
    series = series.interpolate()

    # Change type to int
    series.index = series.index.astype(int)
    series = series.astype(int)

    # Remove negative
    series = series[series >= 0]

    return series


def calculate_payroll_taxes(year, brackets):
    results = {0: 0}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        last_key = list(results.keys())[-1]
        if bracket.get("max"):
            results[bracket["max"] + 1] = (
                (bracket["max"] - bracket["min"]) + 1
            ) * bracket["rate"] + results[last_key]
        else:
            results[max_income] = max_income * bracket["rate"] + results[last_key]
    return clean_df(pd.Series(results))


def calculate_social_security_taxes(year, brackets, retire):
    results = {0: 0}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        tax_type = "older" if retire else "social"
        results[bracket["max"] + 1] = ((bracket["max"] - bracket["min"]) + 1) * bracket[
            tax_type
        ]
        results[max_income] = results[bracket["max"] + 1]
    return clean_df(pd.Series(results))


def calculate_general_tax_credits(year, brackets):
    results = {}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        if bracket.get("max"):
            if bracket["rate"] > 1:
                results[0] = bracket["rate"]
                results[bracket["max"] + 1] = bracket["rate"]
            else:
                results[bracket["max"] + 1] = 0
        else:
            results[max_income] = 0
    return clean_df(pd.Series(results))


def calculate_labour_tax_credits(year, brackets):
    results = {0: 0}
    max_income = 120000
    year_brackets = brackets[year]
    for bracket in year_brackets:
        last_key = list(results.keys())[-1]
        if bracket.get("max"):
            if bracket["rate"] > 1:
                results[bracket["max"] + 1] = bracket["rate"]
            else:
                results[bracket["max"] + 1] = (
                    (bracket["max"] - bracket["min"]) + 1
                ) * bracket["rate"] + results[last_key]
        else:
            results[max_income] = max_income * bracket["rate"] + results[last_key]
    return clean_df(pd.Series(results))


st.header("🏠 Rent or Buy a House in NL")
st.write(
    "Run the numbers on deciding renting or buying a house in the Netherlands"
)

with open("data.json", "r") as f:
    data = json.load(f)

years = reversed(data["years"].copy())

# Input section
st.subheader("Input Parameter")
st.caption("**Buy**")
buy_price = st.number_input("Property price", min_value=0, value=200000, step=10000)
buy_price_growth = st.number_input("Property price growth (per year) [%]", min_value=0, max_value=100, value=2, step=1)
st.caption("Assumed stable throughout mortgage period")
down_payment = st.number_input("Down payment", min_value=0, value=20000, step=10000)
mortgage_period = st.number_input("Mortgage period", min_value=0, max_value=50, value=30, step=1)

buying_cost = st.number_input("Buying cost assumption [%]", min_value=0, max_value=100, value=5, step=1)
selling_cost = st.number_input("Selling cost assumption [%]", min_value=0, max_value=100, value=3, step=1)

woz = st.number_input("WOZ rate (per year) [%]", min_value=0, value=0.05, step=0.05)
mortgage_rate = st.number_input("Mortgage rate (per year) [%]", min_value=0, value=4, step=0.05)
st.caption("Assumed stable throughout mortgage period")

owners_association = st.number_input("Owner's association (per year)", min_value=0, value=3600, step=100)
gwe = st.number_input("Gas, Water, Electricity (per year)", min_value=0, value=2400, step=100)
internet = st.number_input("Internet (per year)", min_value=0, value=600, step=20)
insurance = st.number_input("Insurance (per year)", min_value=0, value=180, step=20)
gementee_tax = st.number_input("Gementee tax (per year)", min_value=0, value=480, step=20)

st.caption("**Rent**")
rent_price = st.number_input("Rent price (per year)", min_value=0, value=144000, step=1000)
rent_price_growth = st.number_input("Rent price growth (per year) [%]", min_value=0, value=144000, step=1000)

# Calculation
buy_df = pd.DataFrame()
buy_df.loc[0, "capital_cost"] = buying_cost + selling_cost + down_payment
buy_df.loc[0, "owners_association"] = owners_association
buy_df.loc[0, "gwe"] = gwe
buy_df.loc[0, "internet"] = internet
buy_df.loc[0, "insurance"] = insurance
buy_df.loc[0, "gementee_tax"] = gementee_tax
buy_df["yearly_cost"] = buy_df["capital_cost"] + buy_df["owners_association"] + buy_df["gwe"] + buy_df["internet"] + buy_df["insurance"] + buy_df["gementee_tax"]
buy_df.loc[0, "debt"] = buy_price - down_payment
buy_df["debt_interest"] = buy_df["debt"] * mortgage_rate
buy_df["debt_repaid"] = np.pmt(mortgage_rate, mortgage_period, buy_df.loc[0, "debt"]) - buy_df["debt_interest"]
buy_df.loc[0, "house_price"] = buy_price * (1 + buy_price_growth)
buy_df.loc[0, "capital_gain"] = buy_df.loc[0, "house_price"] - buy_price
buy_df.loc["deductable_income"] = max()

0df_payroll_taxes = calculate_payroll_taxes(year, data["payrollTax"])
df_social_security_taxes = calculate_social_security_taxes(
    year, data["socialTax"], retire
)
df_general_tax_credits = calculate_general_tax_credits(year, data["generalCredit"])
df_labour_tax_credits = calculate_labour_tax_credits(year, data["labourCredit"])

df_dict = {
    "Payroll Tax (Inkomstenbelasting)": df_payroll_taxes,
    "Social Security Tax (Volksverzekeringen)": df_social_security_taxes,
    "General Tax Credit (Algemene heffingskorting)": df_general_tax_credits,
    "Labour Tax Credit (Arbeidskorting)": df_labour_tax_credits,
}
payroll_tax = int(
    np.interp([income], df_payroll_taxes.index, df_payroll_taxes.values)[0]
)
social_security_tax = int(
    np.interp(
        [income], df_social_security_taxes.index, df_social_security_taxes.values
    )[0]
)
general_tax_credit = int(
    np.interp([income], df_general_tax_credits.index, df_general_tax_credits.values)[0]
)
labour_tax_credit = int(
    np.interp([income], df_labour_tax_credits.index, df_labour_tax_credits.values)[0]
)

# Table section
st.subheader("Table")
results = {
    "Income Before Tax": income,
    "Payroll Tax (Inkomstenbelasting)": payroll_tax,
    "Social Security Tax (Volksverzekeringen)": social_security_tax,
    "General Tax Credit (Algemene heffingskorting)": general_tax_credit,
    "Labour Tax Credit (Arbeidskorting)": labour_tax_credit,
}

results["Income After Tax"] = (
    income
    - results["Payroll Tax (Inkomstenbelasting)"]
    - results["Social Security Tax (Volksverzekeringen)"]
    + results["General Tax Credit (Algemene heffingskorting)"]
    + results["Labour Tax Credit (Arbeidskorting)"]
)

cols = st.columns([0.1, 0.8, 0.1])
series = pd.Series(results, name="Values")
cols[1].dataframe(series, use_container_width=True)
cols[1].markdown(
    """<div style="text-align: right; font-size: 0.75em">*values are per year</div>""",
    unsafe_allow_html=True,
)

# Graph section
st.subheader("Graph")
for key, values in df_dict.items():
    if not "Credit" in key:
        color = co.qualitative.Plotly[0]
    else:
        color = co.qualitative.Plotly[2]

    df = values
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df.values,
            mode="lines",
            name=f"{key}",
            line=dict(
                color=color,
                width=4,
            ),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[income],
            y=[results[key]],
            mode="markers",
            name=f"Your {key}",
            marker=dict(color=co.qualitative.Plotly[1], size=12),
        ),
    )
    fig.update_layout(
        title=f"{key}",
        legend={"orientation": "h", "y": -0.2},
        xaxis_title="Yearly Income",
        yaxis_title=f"{key}",
    )
    fig.update_xaxes(tickformat="~")
    fig.update_yaxes(tickformat="~")
    st.plotly_chart(fig, use_container_width=True)

st.caption("**Disclamier:**")
st.caption(
    "This calculator provides an estimated income tax calculation based on the information provided. It is only for basic tax calculation and illustrative purposes and does not guarantee accuracy. Consult a tax professional for precise calculations."
)
st.caption("Source: https://www.belastingdienst.nl/")
