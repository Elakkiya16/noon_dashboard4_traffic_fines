import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO

st.set_page_config(page_title="Traffic Fines Dashboard", layout="wide", page_icon="🚦")

st.title("🚦 Dashboard 4 — Traffic Fines Analysis")
st.markdown("Deep analysis of traffic fines: trends, violation types, risk scores, and intervention priorities.")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheets = xl.sheet_names
    st.success(f"✅ File loaded. Sheets found: {', '.join(sheets)}")

    fines_sheet = st.selectbox("Select Traffic Fines sheet (Bike or equivalent):", sheets,
                                index=next((i for i, s in enumerate(sheets) if any(k in s.upper() for k in ["BIKE", "FINE", "TRAFFIC", "VEHICLE"])), 0))

    raw = xl.parse(fines_sheet, header=0)

    with st.expander("🔍 Preview raw data"):
        st.dataframe(raw.head(20), use_container_width=True)

    st.markdown("### ⚙️ Column Mapping")
    cols = list(raw.columns)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        name_col = st.selectbox("Rider Name:", cols,
                                 index=next((i for i, c in enumerate(cols) if any(k in str(c).upper() for k in ["NAME", "RIDER", "DRIVER"])), 0))
    with c2:
        date_col = st.selectbox("Date / Month:", ["None"] + cols,
                                 index=next((i+1 for i, c in enumerate(cols) if any(k in str(c).upper() for k in ["DATE", "MONTH", "PERIOD"])), 0))
    with c3:
        amount_col = st.selectbox("Fine Amount:", cols,
                                   index=next((i for i, c in enumerate(cols) if any(k in str(c).upper() for k in ["AMOUNT", "FINE", "VALUE", "AED"])), min(1, len(cols)-1)))
    with c4:
        reason_col = st.selectbox("Violation Type/Reason:", ["None"] + cols,
                                   index=next((i+1 for i, c in enumerate(cols) if any(k in str(c).upper() for k in ["REASON", "TYPE", "VIOLATION", "OFFENCE"])), 0))
    with c5:
        source_col = st.selectbox("Source (Camera/Police):", ["None"] + cols,
                                   index=next((i+1 for i, c in enumerate(cols) if any(k in str(c).upper() for k in ["SOURCE", "AUTHORITY", "ISSUED", "BY"])), 0))

    if st.button("🚀 Generate Dashboard"):

        use_cols = [name_col, amount_col]
        col_map = {"Rider": name_col, "Amount": amount_col}
        if date_col != "None":
            use_cols.append(date_col)
            col_map["Date"] = date_col
        if reason_col != "None":
            use_cols.append(reason_col)
            col_map["Reason"] = reason_col
        if source_col != "None":
            use_cols.append(source_col)
            col_map["Source"] = source_col

        df = raw[use_cols].copy()
        df = df.rename(columns={v: k for k, v in col_map.items()})
        df = df.dropna(subset=["Rider", "Amount"])
        df["Rider"] = df["Rider"].astype(str).str.strip()
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
        df = df.dropna(subset=["Amount"])

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df["Month"] = df["Date"].dt.strftime("%b %Y")
            df["MonthNum"] = df["Date"].dt.to_period("M")

        st.markdown("---")

        # ── KPI Cards ───────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Fines", len(df))
        c2.metric("Total Amount", f"AED {df['Amount'].sum():,.0f}")
        c3.metric("Riders with Fines", df["Rider"].nunique())
        c4.metric("Avg Fine per Rider", f"AED {df.groupby('Rider')['Amount'].sum().mean():,.0f}")

        st.markdown("---")

        # ── SECTION 1: Monthly Fines Trend ───────────────────────────────
        if "Month" in df.columns:
            st.subheader("📈 Monthly Fines Trend")
            monthly = df.groupby("Month").agg(
                TotalFines=("Amount", "sum"),
                FineCount=("Amount", "count")
            ).reset_index()

            fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
            fig_trend.add_trace(go.Bar(x=monthly["Month"], y=monthly["TotalFines"],
                                       name="Total Fine Amount (AED)", marker_color="#e74c3c"),
                                secondary_y=False)
            fig_trend.add_trace(go.Scatter(x=monthly["Month"], y=monthly["FineCount"],
                                           name="Number of Fines", mode="lines+markers",
                                           line=dict(color="#3498db", width=2), marker_size=8),
                                secondary_y=True)
            fig_trend.update_layout(title="Monthly Fine Amount & Frequency")
            fig_trend.update_yaxes(title_text="Total Amount (AED)", secondary_y=False)
            fig_trend.update_yaxes(title_text="Number of Fines", secondary_y=True)
            st.plotly_chart(fig_trend, use_container_width=True)

        # ── SECTION 2: Violation Type Analysis ───────────────────────────
        if "Reason" in df.columns:
            st.subheader("⚠️ Violation Type Analysis")
            col1, col2 = st.columns(2)

            reason_freq = df.groupby("Reason").agg(
                Count=("Amount", "count"),
                TotalCost=("Amount", "sum")
            ).reset_index().sort_values("Count", ascending=False)

            with col1:
                fig_freq = px.bar(reason_freq.head(10), x="Count", y="Reason",
                                  orientation="h", color="Count",
                                  color_continuous_scale="Reds",
                                  title="Most Frequent Violations (Count)",
                                  text="Count")
                fig_freq.update_traces(textposition="outside")
                fig_freq.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
                st.plotly_chart(fig_freq, use_container_width=True)

            with col2:
                reason_cost = reason_freq.sort_values("TotalCost", ascending=False)
                fig_cost = px.bar(reason_cost.head(10), x="TotalCost", y="Reason",
                                  orientation="h", color="TotalCost",
                                  color_continuous_scale="OrRd",
                                  title="Most Costly Violations (AED)",
                                  text="TotalCost")
                fig_cost.update_traces(texttemplate="AED %{text:,.0f}", textposition="outside")
                fig_cost.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
                st.plotly_chart(fig_cost, use_container_width=True)

        # ── SECTION 3: Camera vs Police Source ───────────────────────────
        if "Source" in df.columns:
            st.subheader("📷 Fine Source — Camera vs Police")
            source_data = df.groupby("Source").agg(
                Count=("Amount", "count"),
                TotalAmount=("Amount", "sum")
            ).reset_index()

            col1, col2 = st.columns(2)
            with col1:
                fig_src_count = px.pie(source_data, names="Source", values="Count",
                                       title="Fine Count by Source",
                                       color_discrete_sequence=["#e74c3c", "#3498db", "#2ecc71"])
                st.plotly_chart(fig_src_count, use_container_width=True)
            with col2:
                fig_src_amt = px.pie(source_data, names="Source", values="TotalAmount",
                                     title="Fine Amount by Source (AED)",
                                     color_discrete_sequence=["#e74c3c", "#3498db", "#2ecc71"])
                st.plotly_chart(fig_src_amt, use_container_width=True)

            st.info("""
            💡 **Insight Guide:**
            - **Camera fines** = Systematic speeding / signal jumping habits — training issue
            - **Police fines** = Serious violations or confrontational behavior — disciplinary issue
            """)

        # ── SECTION 4: Safety Risk Score per Rider ───────────────────────
        st.subheader("🛡️ Safety Risk Score per Rider")

        rider_risk = df.groupby("Rider").agg(
            FineCount=("Amount", "count"),
            TotalAmount=("Amount", "sum"),
            AvgFine=("Amount", "mean")
        ).reset_index()

        # Normalize scores 0–100
        def normalize(series):
            min_v, max_v = series.min(), series.max()
            if max_v == min_v:
                return pd.Series([50] * len(series), index=series.index)
            return ((series - min_v) / (max_v - min_v) * 100).round(1)

        rider_risk["FrequencyScore"] = normalize(rider_risk["FineCount"])
        rider_risk["AmountScore"] = normalize(rider_risk["TotalAmount"])
        rider_risk["RiskScore"] = (rider_risk["FrequencyScore"] * 0.6 + rider_risk["AmountScore"] * 0.4).round(1)

        def risk_label(score):
            if score >= 75: return "🔴 High Risk"
            elif score >= 50: return "🟠 Medium Risk"
            elif score >= 25: return "🟡 Low Risk"
            else: return "🟢 Minimal Risk"

        rider_risk["RiskLevel"] = rider_risk["RiskScore"].apply(risk_label)
        rider_risk = rider_risk.sort_values("RiskScore", ascending=False)

        fig_risk = px.bar(rider_risk.head(20), x="Rider", y="RiskScore",
                          color="RiskScore",
                          color_continuous_scale="RdYlGn_r",
                          title="Safety Risk Score — Top 20 Riders (Higher = More Risk)",
                          text="RiskScore",
                          hover_data=["FineCount", "TotalAmount", "RiskLevel"])
        fig_risk.update_traces(textposition="outside")
        fig_risk.update_layout(coloraxis_showscale=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_risk, use_container_width=True)

        # ── SECTION 5: Time to Re-offend ─────────────────────────────────
        if "Date" in df.columns:
            st.subheader("⏱️ Time to Re-offend Analysis")

            reoffend_data = []
            for rider, group in df.groupby("Rider"):
                dates = group["Date"].dropna().sort_values().tolist()
                if len(dates) >= 2:
                    gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                    avg_gap = np.mean(gaps)
                    min_gap = np.min(gaps)
                    reoffend_data.append({
                        "Rider": rider,
                        "TotalFines": len(dates),
                        "AvgDaysBetweenFines": round(avg_gap, 0),
                        "MinDaysBetweenFines": min_gap,
                        "FastestReoffend": f"{min_gap} days"
                    })

            if reoffend_data:
                reoffend_df = pd.DataFrame(reoffend_data).sort_values("AvgDaysBetweenFines")

                fig_reoffend = px.scatter(reoffend_df, x="AvgDaysBetweenFines", y="TotalFines",
                                          size="TotalFines", color="AvgDaysBetweenFines",
                                          color_continuous_scale="RdYlGn",
                                          hover_name="Rider",
                                          title="Re-offend Pattern: Avg Days Between Fines vs Total Fines",
                                          labels={"AvgDaysBetweenFines": "Avg Days Between Fines",
                                                  "TotalFines": "Total Fine Count"})
                st.plotly_chart(fig_reoffend, use_container_width=True)

                st.markdown("**⚡ Fastest Re-offenders (Fines not deterring behaviour):**")
                top_reoffend = reoffend_df.head(10)[["Rider", "TotalFines", "AvgDaysBetweenFines", "FastestReoffend"]]
                st.dataframe(top_reoffend.reset_index(drop=True), use_container_width=True)
            else:
                st.info("Need at least 2 fine records per rider to calculate re-offend time.")

        # ── SECTION 6: Intervention Priority List ────────────────────────
        st.subheader("🎯 Intervention Priority List")

        intervention = rider_risk[["Rider", "FineCount", "TotalAmount", "RiskScore", "RiskLevel"]].copy()
        intervention["TotalAmount"] = intervention["TotalAmount"].map(lambda x: f"AED {x:,.0f}")
        intervention["RecommendedAction"] = intervention["RiskScore"].apply(lambda s:
            "🚨 Immediate management review + suspension of fines liability" if s >= 75 else
            ("⚠️ Mandatory safety retraining + written warning" if s >= 50 else
             ("📋 Verbal warning + monitoring" if s >= 25 else
              "✅ No action required")))

        st.dataframe(intervention.reset_index(drop=True), use_container_width=True)

        # ── Export ───────────────────────────────────────────────────────
        st.subheader("⬇️ Export Report")
        out = BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            rider_risk.to_excel(writer, sheet_name="Rider Risk Scores", index=False)
            intervention.to_excel(writer, sheet_name="Intervention Plan", index=False)
            if "Reason" in df.columns:
                reason_freq.to_excel(writer, sheet_name="Violation Types", index=False)
        st.download_button("Download Excel Report", out.getvalue(),
                           file_name="traffic_fines_report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

else:
    st.info("👆 Please upload the noon operational Excel file to get started.")
    with st.expander("ℹ️ Expected Data Format"):
        st.markdown("""
        **Traffic Fines sheet (Bike / Vehicle):**
        - Rider Name
        - Fine Amount (AED, numeric)
        - Date or Month (optional, for trend analysis)
        - Violation Type / Reason (optional)
        - Source — Camera or Police (optional)
        """)
