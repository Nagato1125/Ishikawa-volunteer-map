import streamlit as st
from streamlit_folium import st_folium
import folium
import pandas as pd
import geopandas as gpd
import gspread
from google.oauth2 import service_account
import pytz
from datetime import datetime

acceptable_color = "#059669"
limit_acceptable_color = "#D97706"
not_acceptable_color = "1F2937"

def color_func(feature):
    is_acceptable = feature['properties']['募集状況']
    if is_acceptable == "募集している":
        return acceptable_color
    elif is_acceptable == "制限付きで募集している":
        return limit_acceptable_color
    else:
        return not_acceptable_color
    
def highlight_function(feature):
    return {
        'fillColor': color_func(feature),
        'color': 'black',
        'weight': 2,
        'fillOpacity': 0.7
    }

def load_geo_json():
    return gpd.read_file('N03-21_17_210101.json')

def load_accept_vo_data():
    return pd.read_excel("Ishikawa_town_accept_volunteer.xlsx")

def load_gspread():
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)

    gc = gspread.authorize(credentials)
    sheet_url = st.secrets["SP_SHEET_URL"]["url"]
    sp = gc.open_by_url(sheet_url)

    return sp

def conv_sp_to_df(sp):
    sheet = sp.worksheet("シート1").get_all_values()
    return pd.DataFrame(sheet[1:], columns=sheet[0])
    
def create_map(geojson_data):

    m = folium.Map(
        location=(36.80, 136.80),
        zoom_start=9,
    )   
    folium.GeoJson(
        geojson_data,
        style_function=lambda feature: {
            'fillColor': color_func(feature),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.5
        },
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(fields=['N03_004', "募集状況"], labels=False),
        popup=folium.GeoJsonPopup(fields=['N03_004'], labels=False),
        popup_keep_highlighted=True
    ).add_to(m)

    return m

def get_last_update_time_in_jst(sp):
    dt = datetime.strptime(sp.lastUpdateTime, '%Y-%m-%dT%H:%M:%S.%fZ')

    # UTCを表すタイムゾーンを設定
    dt_utc = dt.replace(tzinfo=pytz.UTC)

    # 日本時間（JST）に変換
    dt_jst = dt_utc.astimezone(pytz.timezone('Asia/Tokyo'))

    return dt_jst.strftime('%Y年%m月%d日 %H時%M分 JST')
    

def main():
    # Load GeoJSON data
    gpd_df = load_geo_json()
    sp = load_gspread()
    last_update_time = get_last_update_time_in_jst(sp)
    df_acceptable_vo = conv_sp_to_df(sp)
    df_concat = pd.merge(left=gpd_df, right=df_acceptable_vo, left_on="N03_004", right_on="市区町村名")

    st.set_page_config(
        page_title="石川県ボランティア受け入れ情報マップ",
        page_icon=":world_map:",
        layout="centered"
    )

    st.header(":world_map:石川県ボランティア受け入れ情報マップ")
    st.write(f"{last_update_time}時点")

    st.subheader("地図の見方")
    st.markdown("""
        - :green[**緑**]・・・現在ボランティアを募集している自治体です。  
        - :orange[**オレンジ**]・・・現在ボランティアを条件付きで募集している自治体です。  
        - :gray[**グレー**]・・・現在ボランティアを募集していない自治体です。

    """)

    st.warning("""
               手動更新のため、情報に抜け、漏れがある可能性があります。
               必ず自治体からの最新の情報を確認してください。
               ボランティアを募集していないと表記している自治体には募集状況が不明な自治体も含まれます。""")
    # Create the map
    folium_map = create_map(df_concat)

    # Display the map in the Streamlit app
    st_folium(folium_map, width=700)


if __name__ == "__main__":
    main()
