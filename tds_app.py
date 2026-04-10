import streamlit as st
import pandas as pd

st.set_page_config(page_title="TDS System FY 2026-27", layout="wide")

st.title("📊 TDS Computation System (Audit Ready)")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

def hra_exemption(basic, hra, rent, metro):
    perc = 0.5 if metro else 0.4
    return max(0, min(hra, rent - 0.1 * basic, perc * basic))

def compute_tax(income, regime):
    tax = 0
    if regime == "New":
        if income <= 300000: tax = 0
        elif income <= 600000: tax = (income-300000)*0.05
        elif income <= 900000: tax = 15000+(income-600000)*0.1
        elif income <= 1200000: tax = 45000+(income-900000)*0.15
        elif income <= 1500000: tax = 90000+(income-1200000)*0.2
        else: tax = 150000+(income-1500000)*0.3
        if income <= 700000: tax = 0
    else:
        if income <= 250000: tax = 0
        elif income <= 500000: tax = (income-250000)*0.05
        elif income <= 1000000: tax = 12500+(income-500000)*0.2
        else: tax = 112500+(income-1000000)*0.3
        if income <= 500000: tax = 0
    return tax * 1.04

if uploaded_file:
    payroll = pd.read_excel(uploaded_file, sheet_name="Payroll")
    decl = pd.read_excel(uploaded_file, sheet_name="Declarations")

    df = payroll.merge(decl, on="EmpID", how="left")

    results = []

    for _, e in df.iterrows():
        basic = e.get("BASIC", 0)
        hra = e.get("HRA", 0)
        rent = e.get("RENT", 0)
        metro = str(e.get("METRO", "No")).lower() == "yes"

        hra_ex = hra_exemption(basic, hra, rent, metro)

        d80c = min(e.get("CH80C", 0), 150000)
        d80d = min(e.get("CH80D", 0), 50000)
        nps = min(e.get("NPS", 0), 50000)

        statutory = (
            e.get("PROVIDENT_FUND", 0)
            + e.get("PROFESSIONAL_TAX", 0)
            + e.get("EMPLOYEE_ESI", 0)
        )

        gross = e.get("GROSS_EARN", 0)

        taxable = max(
            0,
            gross - hra_ex - 50000 - d80c - d80d - nps - statutory
        )

        tax = compute_tax(taxable, e.get("Regime", "New"))

        results.append({
            "EmpID": e["EmpID"],
            "Gross": gross,
            "HRA Exemption": hra_ex,
            "80C": d80c,
            "80D": d80d,
            "NPS": nps,
            "Statutory": statutory,
            "Taxable Income": taxable,
            "Annual TDS": round(tax),
            "Monthly TDS": round(tax/12)
        })

    result_df = pd.DataFrame(results)

    st.subheader("📋 TDS Working")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        "⬇ Download Excel",
        result_df.to_csv(index=False),
        "TDS_Output.csv"
    )
