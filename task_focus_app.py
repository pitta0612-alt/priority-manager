import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# 데이터 저장 경로 설정
def get_file_paths(section):
    clean_name = "work" if "업무" in section else "study"
    return f"task_{clean_name}.csv", f"history_{clean_name}.csv"

def load_data(file_path, columns):
    if os.path.exists(file_path):
        data = pd.read_csv(file_path)
        # 기존 파일에 없는 컬럼이 있을 경우 보정
        for col in columns:
            if col not in data.columns:
                data[col] = 0
        return data
    return pd.DataFrame(columns=columns)

def save_with_history(file_path, history_path, df, old_row=None):
    if old_row is not None:
        h_df = load_data(history_path, ["수정시간", "작업명", "우선순위", "진행률"])
        old_dict = old_row.to_dict('records')[0]
        old_dict["수정시간"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        h_df = pd.concat([h_df, pd.DataFrame([old_dict])], ignore_index=True)
        h_df.to_csv(history_path, index=False)
    df.to_csv(file_path, index=False)

st.set_page_config(page_title="우선순위 관리기", layout="wide")

# 상단 페이지 분리 메뉴
section = st.sidebar.selectbox("📂 섹션 선택", ["업무(Work)", "공부(Study)"])
DATA_FILE, HISTORY_FILE = get_file_paths(section)

st.title(f"🛡️ {section} 우선순위 시스템")

# 섹션별 컬럼 정의
if "공부" in section:
    cols = ["작업명", "우선순위", "진행률", "중요도", "효율성", "난이도"]
else:
    cols = ["작업명", "우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"]

df = load_data(DATA_FILE, cols)

# 1. 사이드바: 입력 및 수정
with st.sidebar:
    st.divider()
    mode = st.radio("모드 설정", ["새 항목 추가", "기존 항목 수정"])
    
    if mode == "새 항목 추가":
        st.header("➕ 추가")
        t_name = st.text_input("명칭")
        p = st.slider("진행률 (%)", 0, 100, 0, step=5)
        i = st.slider("중요도", 0, 10, 5)
        e = st.slider("효율성", 0, 10, 5)
        
        if "공부" in section:
            level = st.slider("난이도 (어려울수록 높게)", 0, 10, 5)
            # 공부 우선순위: 난이도 50%, 중요도 20%, 효율성 20%, 진행률 10%
            p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
            new_row_data = {"작업명": [t_name], "우선순위": [p_score], "진행률": [p], "중요도": [i], "효율성": [e], "난이도": [level]}
        else:
            u = st.slider("긴급도", 0, 10, 5)
            d = st.slider("의존성", 0, 10, 5)
            p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
            new_row_data = {"작업명": [t_name], "우선순위": [p_score], "진행률": [p], "긴급도": [u], "중요도": [i], "의존성": [d], "효율성": [e]}

        if st.button("리스트 등록"):
            if t_name:
                new_row = pd.DataFrame(new_row_data)
                df = pd.concat([df, new_row], ignore_index=True)
                save_with_history(DATA_FILE, HISTORY_FILE, df)
                st.rerun()
    
    else:
        st.header("🔄 수정")
        if not df.empty:
            target = st.selectbox("항목 선택", df["작업명"].tolist())
            row = df[df["작업명"] == target].iloc[0]
            
            p = st.slider("진행률 (%)", 0, 100, int(row["진행률"]), step=5)
            i = st.slider("중요도", 0, 10, int(row["중요도"]))
            e = st.slider("효율성", 0, 10, int(row["효율성"]))

            if "공부" in section:
                level = st.slider("난이도", 0, 10, int(row.get("난이도", 5)))
                p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
                update_vals = [p_score, p, i, e, level]
                update_cols = ["우선순위", "진행률", "중요도", "효율성", "난이도"]
            else:
                u = st.slider("긴급도", 0, 10, int(row["긴급도"]))
                d = st.slider("의존성", 0, 10, int(row["의존성"]))
                p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
                update_vals = [p_score, p, u, i, d, e]
                update_cols = ["우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"]

            if st.button("변경사항 저장"):
                old_row = df[df["작업명"] == target].copy()
                df.loc[df["작업명"] == target, update_cols] = update_vals
                save_with_history(DATA_FILE, HISTORY_FILE, df, old_row)
                st.rerun()

# 2. 메인 대시보드
col_chart, col_focus = st.columns([2, 1])

with col_chart:
    st.subheader(f"📊 {section} 우선순위 맵")
    if not df.empty:
        hover = ["중요도", "난이도"] if "공부" in section else ["긴급도", "중요도"]
        fig = px.scatter(df, x="진행률", y="우선순위", size="우선순위", color="작업명",
                         hover_data=hover, text="작업명", 
                         range_x=[-5, 105], range_y=[0, 120])
        st.plotly_chart(fig, use_container_width=True)

with col_focus:
    st.subheader("🎯 최우선 집중")
    pending = df[df["진행률"] < 100].sort_values(by="우선순위", ascending=False)
    if not pending.empty:
        top = pending.iloc[0]
        st.info(f"**{top['작업명']}**")
        st.progress(int(top['진행률']))
        if st.button("✅ 완료 (리스트 제거)"):
            df = df[df["작업명"] != top["작업명"]]
            save_with_history(DATA_FILE, HISTORY_FILE, df)
            st.rerun()
    else:
        st.success("완료!")

if st.checkbox("과거 수정 기록(History) 보기"):
    st.dataframe(load_data(HISTORY_FILE, []))