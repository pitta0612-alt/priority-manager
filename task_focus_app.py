import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="우선순위 관리기 v50", layout="wide")

# [보안] Secrets 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            raise ValueError
        if "상태" not in df.columns:
            df["상태"] = "진행"
        return df.dropna(subset=["작업명"])
    except:
        cols = ["작업명", "우선순위", "진행률", "중요도", "효율성", "저장시간", "상태"]
        if worksheet_name == "work":
            cols += ["긴급도", "의존성"]
        else:
            cols += ["난이도"]
        return pd.DataFrame(columns=cols)

# --- 메인 로직 ---
section = st.sidebar.selectbox("📂 섹션 선택", ["업무(Work)", "공부(Study)"])
ws_name = "work" if "업무" in section else "study"
st.title(f"🛡️ {section} 전략적 이력 관리 시스템")

df = load_data(ws_name)

# --- 사이드바 설정 ---
with st.sidebar:
    st.divider()
    mode = st.radio("모드 설정", ["새 항목 추가", "진행 상황 업데이트"])
    
    st.header("📝 데이터 입력")
    
    if mode == "새 항목 추가":
        t_name = st.text_input("명칭 (신규)")
        last_row = None
    else:
        active_tasks = sorted(df[df["상태"] == "진행"]["작업명"].unique())
        if active_tasks:
            t_name = st.selectbox("업데이트할 항목 선택", active_tasks)
            last_row = df[df["작업명"] == t_name].iloc[-1]
        else:
            t_name = ""
            st.info("진행 중인 항목이 없습니다.")
            last_row = None

    p = st.slider("진행률 (%)", 0, 100, int(last_row["진행률"]) if last_row is not None else 0, step=5)
    i = st.slider("중요도", 0, 10, int(last_row["중요도"]) if last_row is not None else 5)
    e = st.slider("효율성", 0, 10, int(last_row["효율성"]) if last_row is not None else 5)
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "공부" in section:
        level = st.slider("난이도", 0, 10, int(last_row.get("난이도", 5)) if last_row is not None else 5)
        p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
        new_row_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "중요도": i, "효율성": e, "난이도": level, "저장시간": current_time, "상태": "진행"}
    else:
        u = st.slider("긴급도", 0, 10, int(last_row.get("긴급도", 5)) if last_row is not None else 5)
        d = st.slider("의존성", 0, 10, int(last_row.get("의존성", 5)) if last_row is not None else 5)
        p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
        new_row_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "긴급도": u, "중요도": i, "의존성": d, "효율성": e, "저장시간": current_time, "상태": "진행"}

    if st.button("🚀 데이터 저장 및 이력 추가"):
        if t_name:
            try:
                new_row_df = pd.DataFrame([new_row_data])
                updated_df = pd.concat([df, new_row_df], ignore_index=True)
                conn.update(worksheet=ws_name, data=updated_df)
                st.balloons()
                st.success("✅ 새로운 이력이 기록되었습니다!")
                st.rerun()
            except Exception as err: st.error(f"저장 실패: {err}")

# --- 상단 레이아웃 ---
latest_each = df.sort_values("저장시간").groupby("작업명").tail(1)
active_df = latest_each[latest_each["상태"] == "진행"].copy()

col_chart, col_focus = st.columns([2, 1])

with col_chart:
    st.subheader("📊 현재 진행 중인 우선순위")
    if not active_df.empty:
        # 글자 크기 조절 로직 추가 (5글자 이상이면 작게)
        active_df['font_size'] = active_df['작업명'].apply(lambda x: 10 if len(str(x)) >= 5 else 14)
        
        fig = px.scatter(active_df, x="진행률", y="우선순위", size="우선순위", color="작업명", 
                         hover_data=active_df.columns, text="작업명", range_x=[-5, 105], range_y=[0, 120])
        
        # 텍스트 크기 개별 설정 적용
        fig.update_traces(textposition='top center', textfont_size=active_df['font_size'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("현재 진행 중인 작업이 없습니다.")

with col_focus:
    st.subheader("🎯 집중 타겟")
    pending = active_df.sort_values(by="우선순위", ascending=False)
    if not pending.empty:
        top = pending.iloc[0]
        st.warning(f"**집중: {top['작업명']}**")
        st.progress(int(top['진행률']))
        if st.button("✅ 완료 처리 (이력 보존)"):
            complete_row = top.copy()
            complete_row["상태"] = "완료"
            complete_row["진행률"] = 100
            complete_row["저장시간"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated_df = pd.concat([df, pd.DataFrame([complete_row])], ignore_index=True)
            conn.update(worksheet=ws_name, data=updated_df)
            st.balloons()
            st.rerun()

# --- 하단 이력 관리 ---
st.divider()
col_hist1, col_hist2 = st.columns(2)

with col_hist1:
    st.subheader("🔍 항목별 변화 이력")
    all_task_names = sorted(df["작업명"].unique())
    if all_task_names:
        selected_task = st.selectbox("이력을 확인할 항목 선택", all_task_names)
        task_history = df[df["작업명"] == selected_task].sort_values("저장시간", ascending=False)
        st.dataframe(task_history, use_container_width=True)

with col_hist2:
    st.subheader("📁 전체 데이터 관리")
    show_full = st.checkbox("전체 누적 로그 보기")
    if show_full:
        st.dataframe(df.sort_values("저장시간", ascending=False), use_container_width=True)