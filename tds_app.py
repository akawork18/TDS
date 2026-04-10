import streamlit as st
import pandas as pd

st.set_page_config(page_title="TDS System FY 2026-27", layout="wide")

st.title("📊 TDS Computation System (Full Professional Version)")

# ================= FILE UPLOAD =================
payroll_file = st.file_uploader("Upload Payroll File", type=["xlsx"])
decl_file = st.file_uploader("Upload Declarations File", type=["xlsx"])

# ================= FUNCTIONS =================

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

# ================= MAIN =================

if payroll_file:

    payroll = pd.read_excel(payroll_file)

    if decl_file:
        decl = pd.read_excel(decl_file)
        df = payroll.merge(decl, on="EmpID", how="left")
    else:
        st.warning("Declarations file not uploaded. Proceeding without it.")
        df = payroll.copy()

    results = []

    for _, e in df.iterrows():

        # ===== CORE SALARY =====
        basic = float(e.get("BASIC", 0) or 0)
        hra = float(e.get("HRA", 0) or 0)
        special = float(e.get("SPECIAL_ALLOWANCE", 0) or 0)

        # ===== OTHER TAXABLE EARNINGS =====
        bonus = float(e.get("BONUS", 0) or 0)
        incentive = float(e.get("INCENTIVE", 0) or 0)
        overtime = float(e.get("OVER_TIME", 0) or 0)
        other1 = float(e.get("OTHER_EARNING", 0) or 0)
        other2 = float(e.get("OTHER_EARNING_2", 0) or 0)
        notice_pay = float(e.get("NOTICE_PAY_PAYMENT", 0) or 0)
        driver = float(e.get("DRIVER_ALLOWANCE", 0) or 0)

        taxable_earnings = (
            basic + hra + special + bonus + incentive +
            overtime + other1 + other2 + notice_pay + driver
        )

        # ===== REIMBURSEMENTS (EXEMPT) =====
        telephone = float(e.get("TELEPHONE_REIMBURSEMENT", 0) or 0)
        petrol = float(e.get("PETROL_REIMBURSEMENT", 0) or 0)
        books = float(e.get("BOOKS_&_PERIODICALS_REIMB", 0) or 0)
        washing = float(e.get("WASHING_REIMBURSEMENT", 0) or 0)
        uniform = float(e.get("UNIFORM_ALL", 0) or 0)
        travel = float(e.get("TRAVEL_REIMBURSEMENT", 0) or 0)

        reimbursements_exempt = (
            telephone + petrol + books + washing + uniform + travel
        )

        # ===== CHILD EDUCATION (PARTIAL EXEMPT) =====
        children_allow = float(e.get("CHILDREN_EDUCATION_ALLOWA", 0) or 0)
        children_exempt = min(children_allow, 2400)  # simplified annual cap
        children_taxable = children_allow - children_exempt

        # ===== HRA =====
        rent = float(e.get("RENT", 0) or 0)
        metro = str(e.get("METRO", "No")).lower() == "yes"
        hra_ex = hra_exemption(basic, hra, rent, metro)

        # ===== DEDUCTIONS =====
        d80c = min(float(e.get("CH80C", 0) or 0), 150000)
        d80d = min(float(e.get("CH80D", 0) or 0), 50000)
        nps = min(float(e.get("NPS", 0) or 0), 50000)

        statutory = (
            float(e.get("PROVIDENT_FUND", 0) or 0)
            + float(e.get("PROFESSIONAL_TAX", 0) or 0)
            + float(e.get("EMPLOYEE_ESI", 0) or 0)
        )

        # ===== GROSS =====
        gross = float(e.get("GROSS_EARN", taxable_earnings) or 0)

        # ===== TAXABLE INCOME =====
        taxable = max(
            0,
            gross
            - reimbursements_exempt
            - hra_ex
            - children_exempt
            - 50000
            - d80c
            - d80d
            - nps
            - statutory
        )

        tax = compute_tax(taxable, str(e.get("Regime", "New")))

        results.append({
            "EmpID": e.get("EmpID"),
            "Regime": e.get("Regime"),

            # ===== Salary =====
            "Gross Salary": gross,
            "Taxable Earnings": taxable_earnings,

            # ===== Exemptions =====
            "HRA Exemption": hra_ex,
            "Reimbursements Exempt": reimbursements_exempt,
            "Children Education Exempt": children_exempt,

            # ===== Deductions =====
            "80C (Capped)": d80c,
            "80D": d80d,
            "NPS": nps,
            "Statutory (PF/PT/ESI)": statutory,

            # ===== Final =====
            "Taxable Income": taxable,
            "Annual TDS": round(tax),
            "Monthly TDS": round(tax / 12),
        })

    result_df = pd.DataFrame(results)

    st.subheader("📋 TDS Working (Full Version)")
    st.dataframe(result_df, use_container_width=True)

    st.download_button(
        "⬇ Download Excel",
        result_df.to_csv(index=False),
        "TDS_Full_Output.csv"
    )
