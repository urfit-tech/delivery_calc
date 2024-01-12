import streamlit as st
import datetime
import psycopg2
import pandas as pd

# establish postgres connection
pg_conn = psycopg2.connect(**st.secrets["postgres"])


@st.cache_data
def load_managers(app_id: str):
    df = pd.read_sql(
        """
        SELECT member_id, member.name, email
        FROM member
        JOIN member_property ON member.id = member_property.member_id AND member.app_id = %s
        JOIN property ON member_property.property_id = property.id AND property.name = '分機號碼'
        """,
        pg_conn,
        params=(app_id,),
        index_col="member_id",
    )
    return df


# @st.cache_data
def load_leads(app_id: str, started_at: str, ended_at: str):
    lead_category_df = pd.read_sql(
        """
        SELECT member_id, first_value(category_id) OVER (PARTITION BY member.id ORDER BY member.created_at DESC) AS last_category_id
        FROM member
        JOIN member_category ON member.id = member_category.member_id AND member.app_id = %s
        WHERE member.created_at BETWEEN %s AND %s
        """,
        pg_conn,
        params=(app_id, started_at, ended_at + datetime.timedelta(days=1)),
    )
    lead_level_df = pd.read_sql(
        """
        SELECT member_id, member_property.value AS level
        FROM member
        JOIN member_property ON member.id = member_property.member_id AND member.app_id = %s
        JOIN property ON member_property.property_id = property.id AND property.name = '名單分級'
        WHERE member.created_at BETWEEN %s AND %s
        """,
        pg_conn,
        params=(app_id, started_at, ended_at + datetime.timedelta(days=1)),
    )
    lead_level_df["level"] = lead_level_df["level"].apply(
        lambda x: x.replace(" ", "").split(",")[-1]
    )

    # outer join to get all leads
    lead_df = pd.merge(lead_category_df, lead_level_df, how="outer", on="member_id")
    lead_df["level"].fillna("N", inplace=True)
    return lead_df


@st.cache_data
def load_categories(app_id):
    """
    Load categories from database
    """
    return pd.read_sql(
        """
        SELECT id, name
        FROM category
        WHERE app_id = %s AND class = 'member'
        """,
        pg_conn,
        params=(app_id,),
        index_col="id",
    )
