import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# =================================================================
# [설정] 사용자 제공 구글 스프레드시트 주소 반영
# =================================================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1v4cSD3FMYfIWxMdkK9t6wD3MNcAt_h-knP4GH6EsgJ0/edit?gid=1234381228#gid=1234381228"

st.set_page_config(page_title="우선순위 관리기 v25", layout="wide")

# 구글 시트 연결 초기화
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    """구글 시트에서 섹션별 데이터를 실시간으로 가져옵니다."""
    try:
        # 캐시 없이 즉시 로드 (ttl=0)
        return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    except Exception:
        # 시트에 데이터가 없거나 탭이 없을 경우 기본 틀 생성
        if worksheet_name == "work":
            return pd.DataFrame(columns=["작업명", "우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"])
        else:
            return pd.DataFrame(columns=["작업명", "우선순위", "진행률", "중요도", "효율성", "난이도"])

# --- 사이드바 및 섹션 선택 ---
section = st.sidebar.selectbox("📂 섹션 선택", ["업무(Work)", "공부(Study)"])
ws_name = "work" if "업무" in section else "study"

st.title(f"🛡️ {section} 우선순위 시스템")
df = load_data(ws_name)

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
            # 공부 가중치: 난이도 50%, 중요도 20%, 효율성 20%, 진행률 10%
            p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
            new_row_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "중요도": i, "효율성": e, "난이도": level}
        else:
            u = st.slider("긴급도", 0, 10, 5)
            d = st.slider("의존성", 0, 10, 5)
            # 업무 가중치: 긴급 35%, 중요 35%, 의존 15%, 효율 14%, 진행 1%
            p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
            new_row_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "긴급도": u, "중요도": i, "의존성": d, "효율성": e}

        if st.button("구글 시트에 등록"):
            if t_name:
                new_row = pd.DataFrame([new_row_data])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=updated_df)
                st.success("데이터가 구글 시트에 안전하게 기록되었습니다.")
                st.rerun()
    
    else:
        st.header("🔄 수정")
        if not df.empty and "작업명" in df.columns:
            task_list = df["작업명"].dropna().unique().tolist()
            if task_list:
                target = st.selectbox("항목 선택", task_list)
                row = df[df["작업명"] == target].iloc[0]
                
                p = st.slider("진행률 (%)", 0, 100, int(row.get("진행률", 0)), step=5)
                i = st.slider("중요도", 0, 10, int(row.get("중요도", 5)))
                e = st.slider("효율성", 0, 10, int(row.get("효율성", 5)))

                if "공부" in section:
                    level = st.slider("난이도", 0, 10, int(row.get("난이도", 5)))
                    p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
                    update_cols = ["우선순위", "진행률", "중요도", "효율성", "난이도"]
                    update_vals = [p_score, p, i, e, level]
                else:
                    u = st.slider("긴급도", 0, 10, int(row.get("긴급도", 5)))
                    d = st.slider("의존성", 0, 10, int(row.get("의존성", 5)))
                    p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
                    update_cols = ["우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"]
                    update_vals = [p_score, p, u, i, d, e]

                if st.button("수정사항 반영"):
                    df.loc[df["작업명"] == target, update_cols] = update_vals
                    conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=df)
                    st.success("수정 사항이 구글 시트에 동기화되었습니다.")
                    st.rerun()

# --- 메인 화면: 그래프 및 집중 대상 ---
col_chart, col_focus = st.columns([2, 1])

with col_chart:
    st.subheader(f"📊 {section} 가시화")
    if not df.empty and "우선순위" in df.columns:
        hover_info = ["중요도", "난이도"] if "공부" in section else ["긴급도", "중요도"]
        # 실제 열 존재 여부 확인 후 표시
        actual_hover = [h for h in hover_info if h in df.columns]
        fig = px.scatter(df, x="진행률", y="우선순위", size="우선순위", color="작업명",
                         hover_data=actual_hover, text="작업명", 
                         range_x=[-5, 105], range_y=[0, 120])
        st.plotly_chart(fig, use_container_width=True)

with col_focus:
    st.subheader("🎯 핵심 타겟")
    if not df.empty and "진행률" in df.columns:
        pending = df[df["진행률"] < 100].sort_values(by="우선순위", ascending=False)
        if not pending.empty:
            top = pending.iloc[0]
            st.info(f"**현재 집중: {top['작업명']}**")
            st.progress(int(top['진행률']))
            if st.button("✅ 완료 및 시트에서 제거"):
                df = df[df["작업명"] != top["작업명"]]
                conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=df)
                st.balloons()
                st.rerun()
        else:
            st.success("모든 목표를 달성했습니다!")