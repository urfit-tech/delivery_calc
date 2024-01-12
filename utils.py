from io import BytesIO
import pandas as pd


def generate_sample_data(manager_df, category_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sample_manager_conf_df = pd.DataFrame(
            index=manager_df.index,
            columns=[
                "name",
                "email",
                "score",
                "max_leads",
                "category.unknown",
                *["category." + category_name for category_name in category_df["name"]],
            ],
        )
        sample_manager_conf_df["name"] = manager_df["name"]
        sample_manager_conf_df["email"] = manager_df["email"]
        sample_manager_conf_df["score"] = 0.5
        sample_manager_conf_df["max_leads"] = 0
        sample_manager_conf_df["category.unknown"] = 1
        sample_manager_conf_df.fillna(0, inplace=True)
        sample_manager_conf_df.to_excel(writer, sheet_name="manager")
        sample_category_conf_df = category_df.copy()
        sample_category_conf_df.loc[len(sample_category_conf_df)] = ["unknown"]
        sample_category_conf_df["cost"] = 0.5
        sample_category_conf_df.to_excel(writer, sheet_name="category")
        sample_level_conf_df = pd.DataFrame(
            index=["N", "R", "SR", "SSR"],
            data=[1, 2, 3, 5],
            columns=["value"],
        )
        sample_level_conf_df.index.name = "level"
        sample_level_conf_df.to_excel(writer, sheet_name="level")
    processed_data = output.getvalue()
    return processed_data
