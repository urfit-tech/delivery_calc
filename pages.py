import numpy as np
import plotly.express as px
import streamlit as st
import datetime
from utils import generate_sample_data
import pulp
import pandas as pd
from loaders import load_managers, load_categories, load_leads




def login_page():
    """
    Login page
    """
    st.title("Lead score calculator")
    st.subheader("Login")
    password = st.text_input(
        "Password",
        type="password",
    )
    if password:
        if password == st.secrets["password"]:
            st.session_state["authenticated"] = True
            st.experimental_rerun()
        else:
            st.error("The password you entered is incorrect.")


def main_page():
    col1, col2 = st.columns([4, 8])
    app_id = col1.selectbox("選擇 APP", ["xuemi", "sixdigital"])
    start_date, end_date = col2.date_input(
        "選擇日期範圍",
        [
            datetime.date(2023, 1, 1),
            datetime.date(2023, 1, 31),
            # datetime.datetime.now(), datetime.datetime.now()
        ],
    )
    if start_date is None or end_date is None:
        st.stop()

    col1, col2, col3 = st.columns(3)
    category_df = load_categories(app_id)
    manager_df = load_managers(app_id)
    lead_df = load_leads(app_id, start_date, end_date)

    col1.metric("領域數量", len(category_df))
    col2.metric("業務數量", len(manager_df))
    col3.metric("名單數量", len(lead_df))

    with st.expander("查看詳細數據"):
        st.subheader("領域")
        st.table(category_df)
        st.subheader("業務")
        st.table(manager_df)
        st.subheader("名單")
        st.table(lead_df)

    st.divider()
    conf_file = st.file_uploader("上傳設定檔案", type=["xlsx"])
    st.download_button(
        label="下載範例設定檔案",
        use_container_width=True,
        data=generate_sample_data(manager_df, category_df),
        file_name="config.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # read config file
    if conf_file is None:
        st.stop()
    try:
        manager_conf_df = pd.read_excel(
            conf_file, sheet_name="manager", index_col="member_id"
        )
        category_conf_df = pd.read_excel(
            conf_file, sheet_name="category", index_col="id"
        )
        level_conf_df = pd.read_excel(conf_file, sheet_name="level", index_col="level")

    except Exception as e:
        st.error(f"錯誤發生：{e}")

    N = len(lead_df)  # 名單資源數量
    M = len(manager_df)  # 業務數量
    F = len(category_df)  # 領域數量

    def get_level_value(level):
        try:
            return level_conf_df.loc[level, "value"]
        except KeyError:
            return level_conf_df.loc["N", "value"]

    def get_category_cost(category_id):
        # add 1 to avoid zero division
        try:
            return category_conf_df.loc[category_id, "cost"] + 1
        except KeyError:
            return 1

    def get_category_index(category_id):
        try:
            return "category." + category_df.loc[category_id, "name"]
        except KeyError:
            return "category.unknown"

    v = lead_df["level"].apply(get_level_value)  # 名單資源的分級價值
    c = lead_df["last_category_id"].apply(get_category_cost)  # 名單資源的領域成本
    f = lead_df["last_category_id"].apply(get_category_index)  # 名單資源對應的領域索引
    p = manager_conf_df.loc[:, "category.unknown":]  # 業務對領域的偏好
    s = manager_conf_df["score"]  # 業務的成交能力
    x_max = manager_conf_df["max_leads"]  # 業務最多能拿到的名單數量

    # 建立問題實例 - 最大化問題
    prob = pulp.LpProblem("Maximize_Satisfaction", pulp.LpMaximize)

    # 決策變數 x_ij
    x = pulp.LpVariable.dicts(
        "x", ((i, j) for i in range(M) for j in range(N)), cat="Binary"
    )

    # 目標函數
    prob += pulp.lpSum(
        x[(i, j)] * p.iloc[i, :][f[j]] * v[j] * s[i] ** 2 / c[j]
        for i in range(M)
        for j in range(N)
    )

    # 約束條件：每個名單資源只能被分配給一個業務
    for j in range(N):
        prob += pulp.lpSum(x[(i, j)] for i in range(M)) == 1

    # 新約束條件：業務分配的名單數量不超過其最大值 x_i
    for i in range(M):
        prob += pulp.lpSum(x[(i, j)] for j in range(N)) <= x_max[i]

    # 求解問題
    prob.solve()

    # 回傳結果
    result_df = pd.DataFrame(
        index=manager_conf_df.index,
        columns=[
            "category.unknown",
            *["category." + category_name for category_name in category_df["name"]],
        ],
        data=0,
    )

    total = 0
    for i in range(M):
        for j in range(N):
            if pulp.value(x[(i, j)]) == 1:
                total += 1
                result_df.loc[manager_conf_df.index[i], f[j]] += 1

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("狀態", pulp.LpStatus[prob.status])
    col2.metric("最大滿意度", np.round(pulp.value(prob.objective), 2))
    col3.metric("派發數量", total)

    # reset index, column name
    result_df.index = manager_df["name"] + "(" + manager_df["email"] + ")"
    result_df.columns = [
        category_name.replace("category.", "") for category_name in result_df.columns
    ]

    # remove rows and columns that are all zeros
    result_df = result_df.loc[
        (result_df != 0).any(axis=1), (result_df != 0).any(axis=0)
    ]

    data = result_df.values
    fig = px.imshow(
        data,
        labels=dict(x="領域", y="業務", color="名單數量"),
        x=result_df.columns,
        y=result_df.index,
        zmin=0,
        color_continuous_scale="Viridis",
    )
    # Add annotations (data labels)
    for y in range(data.shape[0]):
        for x in range(data.shape[1]):
            fig.add_annotation(
                dict(
                    font=dict(
                        color="white" if data[y, x] < data.max() / 2 else "black"
                    ),
                    x=x,
                    y=y,
                    text=str(data[y, x]),
                    showarrow=False,
                    xref="x",
                    yref="y",
                )
            )

    st.plotly_chart(fig, use_container_width=True)
    with st.expander("查看詳細數據"):
        st.table(result_df)
