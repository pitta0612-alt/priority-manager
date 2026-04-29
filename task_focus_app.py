import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 페이지 기본 설정
st.set_page_config(page_title="우선순위 관리기 v48", layout="wide")

# [보안] Secrets 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            raise ValueError
        return df.dropna(subset=["작업명"])
    except:
        # '저장시간' 컬럼 기본 포함
        cols = ["작업명", "우선순위", "진행률", "중요도", "효율성", "저장시간"]
        if worksheet_name == "work":
            cols += ["긴급도", "의존성"]
        else:
            cols += ["난이도"]
        return pd.DataFrame(columns=cols)

# --- 메인 로직 ---
section = st.sidebar.selectbox("📂 섹션 선택", ["업무(Work)", "공부(Study)"])
ws_name = "work" if "업무" in section else "study"
st.title(f"🛡️ {section} 우선순위 및 이력 시스템")

df = load_data(ws_name)

# --- 사이드바 설정 ---
with st.sidebar:
    st.divider()
    mode = st.radio("모드 설정", ["새 항목 추가", "진행 상황 업데이트"])
    
    # 공통 입력 UI (추가/수정 모두 동일하게 사용)
    st.header("📝 데이터 입력")
    
    if mode == "새 항목 추가":
        t_name = st.text_input("명칭 (신규)")
    else:
        if not df.empty:
            # 중복 제거된 유니크한 작업명 리스트 추출
            unique_tasks = sorted(df["작업명"].unique())
            t_name = st.selectbox("업데이트할 항목 선택", unique_tasks)
            # 가장 최근 데이터의 값을 초기값으로 세팅
            last_row = df[df["작업명"] == t_name].iloc[-1]
        else:
            t_name = ""
            st.info("데이터가 없습니다.")

    p = st.slider("진행률 (%)", 0, 100, 0 if mode=="새 항목 추가" else int(last_row["진행률"]), step=5)
    i = st.slider("중요도", 0, 10, 5 if mode=="새 항목 추가" else int(last_row["중요도"]))
    e = st.slider("효율성", 0, 10, 5 if mode=="새 항목 추가" else int(last_row["효율성"]))
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "공부" in section:
        level = st.slider("난이도", 0, 10, 5 if mode=="새 항목 추가" else int(last_row.get("난이도", 5)))
        p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
        new_row_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "중요도": i, "효율성": e, "난이도": level, "저장시간": current_time}
    else:
        u = st.slider("긴급도", 0, 10, 5 if mode=="새 항목 추가" else int(last_row.get("긴급도", 5)))
        d = st.slider("의존성", 0, 10, 5 if mode=="새 항목 추가" else int(last_row.get("의존성", 5)))
        p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
        new_row_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "긴급도": u, "중요도": i, "의존성": d, "효율성": e, "저장시간": current_time}

    if st.button("🚀 데이터 저장 및 이력 추가"):
        if t_name:
            try:
                # 수정 모드에서도 덮어쓰지 않고 새로운 행을 생성하여 이어 붙임
                new_row_df = pd.DataFrame([new_row_data])
                updated_df = pd.concat([df, new_row_df], ignore_index=True)
                conn.update(worksheet=ws_name, data=updated_df)
                st.balloons()
                st.success(f"✅ {current_time}에 이력이 추가되었습니다!")
                st.rerun()
            except Exception as err:
                st.error(f"저장 실패: {err}")

# --- 상단 레이아웃 (시각화는 가장 최근 시점의 데이터만 표시) ---
col_chart, col_focus = st.columns([2, 1])

# 시각화용 데이터: 각 작업명별로 가장 최신(마지막) 행만 추출
latest_df = df.sort_values("저장시간").groupby("작업명").tail(1) if not df.empty else df

with col_chart:
    st.subheader("📊 현재 진행 현황 (최신 시점)")
    if not latest_df.empty:
        fig = px.scatter(latest_df, x="진행률", y="우선순위", size="우선순위", color="작업명", 
                         hover_data=latest_df.columns, text="작업명", range_x=[-5, 105], range_y=[0, 120])
        st.plotly_chart(fig, use_container_width=True)

with col_focus:
    st.subheader("🎯 최우선 타겟")
    pending = latest_df[latest_df["진행률"] < 100].sort_values(by="우선순위", ascending=False)
    if not pending.empty:
        top = pending.iloc[0]
        st.warning(f"**집중: {top['작업명']}**")
        st.progress(int(top['진행률']))
        if st.button("✅ 전체 이력에서 삭제"):
            # 해당 작업명의 모든 과거 기록 삭제
            conn.update(worksheet=ws_name, data=df[df["작업명"] != top["작업명"]])
            st.balloons()
            st.rerun()

# --- 하단 체크박스 (전체 이력 조회) ---
st.divider()
show_history = st.checkbox("📋 전체 변경 이력 보기 (타임스탬프 포함)")

if show_history:
    st.subheader("📜 누적 데이터 로그")
    if not df.empty:
        # 최근 저장된 시간이 위로 오도록 정렬
        log_df = df.sort_values(by="저장시간", ascending=False)
        st.dataframe(log_df, use_container_width=True)