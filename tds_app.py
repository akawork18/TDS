import streamlit as st
import pandas as pd

st.set_page_config(page_title="TDS System FY 2026-27", layout="wide")

st.title("📊 TDS Computation System (Audit Ready)")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

# ================= HRA =================
def hra_exemption(basic, hra, rent, metro):
    perc = 0.5 if metro else 0.4
    return max(0, min(hra, rent - 0.1 * basic, perc * basic))

# ================= TAX =================
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

    return tax * 1.04  # cess

# ================= MAIN =================
if uploaded_file:

    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names

        # ===== Auto detect sheets =====
        payroll_sheet = None
        decl_sheet = None

        for s in sheet_names:
            if "pay" in s.lower():
                payroll_sheet = s
            if "decl" in s.lower():
                decl_sheet = s

        # fallback
        if not payroll_sheet:
            payroll_sheet = sheet_names[0]

        if not decl_sheet and len(sheet_names) > 1:
            decl_sheet = sheet_names[1]

        st.success(f"Using sheets → Payroll: {payroll_sheet} | Declarations: {decl_sheet}")

        # ===== Read Payroll =====
        payroll = pd.read_excel(xls, sheet_name=payroll_sheet)

        # ===== Read Declarations SAFELY =====
        if decl_sheet and decl_sheet in sheet_names:
            decl = pd.read_excel(xls, sheet_name=decl_sheet)

            if isinstance(decl, pd.DataFrame) and "EmpID" in decl.columns:
                df = payroll.merge(decl, on="EmpID", how="left")
            else:
                st.warning("Declarations sheet invalid. Proceeding without it.")
                df = payroll.copy()
        else:
            st.warning("Declarations sheet not found. Proceeding without it.")
            df = payroll.copy()

        results = []

        for _, e in df.iterrows():

            basic = float(e.get("BASIC", 0) or 0)
            hra = float(e.get("HRA", 0) or 0)
            rent = float(e.get("RENT", 0) or 0)
            metro = str(e.get("METRO", "No")).lower() == "yes"

            hra_ex = hra_exemption(basic, hra, rent, metro)

            # ===== Deductions =====
            d80c = min(float(e.get("CH80C", 0) or 0), 150000)
            d80d = min(float(e.get("CH80D", 0) or 0), 50000)
            nps = min(float(e.get("NPS", 0) or 0), 50000)

            statutory = (
                float(e.get("PROVIDENT_FUND", 0) or 0)
                + float(e.get("PROFESSIONAL_TAX", 0) or 0)
                + float(e.get("EMPLOYEE_ESI", 0) or 0)
            )

            gross = float(e.get("GROSS_EARN", 0) or 0)

            taxable = max(
                0,
                gross - hra_ex - 50000 - d80c - d80d - nps - statutory
            )

            tax = compute_tax(taxable, str(e.get("Regime", "New")))

            results.append({
                "EmpID": e.get("EmpID"),
                "Regime": e.get("Regime"),

                "Gross Salary": round(gross, 2),

                # ===== Exemptions =====
                "HRA Exemption": round(hra_ex, 2),

                # ===== Chapter VI-A =====
                "80C (Capped)": d80c,
                "80D": d80d,
                "NPS": nps,

                # ===== Statutory =====
                "Statutory (PF+PT+ESI)": statutory,

                # ===== Final =====
                "Taxable Income": round(taxable, 2),
                "Annual TDS": round(tax, 2),
                "Monthly TDS": round(tax / 12, 2),
            })

        result_df = pd.DataFrame(results)

        st.subheader("📋 TDS Working")
        st.dataframe(result_df, use_container_width=True)

        st.download_button(
            "⬇ Download Excel",
            result_df.to_csv(index=False),
            "TDS_Output.csv"
        )

    except Exception as e:
        st.error("Error processing file. Please check format.")
        st.exception(e)
