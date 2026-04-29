import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 페이지 기본 설정
st.set_page_config(page_title="우선순위 관리기 v45", layout="wide")

# [보안] Secrets에 설정된 정보를 사용하여 자동으로 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    """구글 시트에서 데이터를 실시간으로 로드"""
    try:
        # Secrets에 설정된 정보를 바탕으로 데이터 로드
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            raise ValueError
        # 작업명이 있는 유효한 행만 필터링
        return df.dropna(subset=["작업명"])
    except:
        # 데이터가 없을 경우 기본 컬럼 구조 생성
        if worksheet_name == "work":
            return pd.DataFrame(columns=["작업명", "우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"])
        else:
            return pd.DataFrame(columns=["작업명", "우선순위", "진행률", "중요도", "효율성", "난이도"])

# --- 메인 로직 시작 ---
section = st.sidebar.selectbox("📂 섹션 선택", ["업무(Work)", "공부(Study)"])
ws_name = "work" if "업무" in section else "study"
st.title(f"🛡️ {section} 우선순위 시스템")

# 데이터 불러오기
df = load_data(ws_name)

# --- 사이드바: 추가 및 수정 ---
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
            level = st.slider("난이도", 0, 10, 5)
            p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
            new_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "중요도": i, "효율성": e, "난이도": level}
        else:
            u = st.slider("긴급도", 0, 10, 5)
            d = st.slider("의존성", 0, 10, 5)
            p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
            new_data = {"작업명": t_name, "우선순위": p_score, "진행률": p, "긴급도": u, "중요도": i, "의존성": d, "효율성": e}

        if st.button("🚀 시트에 즉시 저장"):
            if t_name:
                try:
                    new_row = pd.DataFrame([new_data])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet=ws_name, data=updated_df)
                    st.success("✅ 저장 성공!")
                    st.rerun()
                except Exception as err:
                    st.error(f"저장 실패: {err}")

    else:
        st.header("🔄 수정")
        if not df.empty:
            target = st.selectbox("수정할 항목 선택", df["작업명"].tolist())
            row = df[df["작업명"] == target].iloc[0]
            
            p = st.slider("진행률 (%)", 0, 100, int(row["진행률"]), step=5)
            i = st.slider("중요도", 0, 10, int(row["중요도"]))
            e = st.slider("효율성", 0, 10, int(row["효율성"]))

            if "공부" in section:
                level = st.slider("난이도", 0, 10, int(row.get("난이도", 5)))
                p_score = (level * 5.0) + (i * 2.0) + (e * 2.0) + (p * 0.1)
                up_cols = ["우선순위", "진행률", "중요도", "효율성", "난이도"]
                up_vals = [p_score, p, i, e, level]
            else:
                u = st.slider("긴급도", 0, 10, int(row.get("긴급도", 5)))
                d = st.slider("의존성", 0, 10, int(row.get("의존성", 5)))
                p_score = (u*3.5) + (i*3.5) + (p*0.1) + (d*1.5) + (e*1.4)
                up_cols = ["우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"]
                up_vals = [p_score, p, u, i, d, e]

            if st.button("💾 변경사항 반영"):
                try:
                    df.loc[df["작업명"] == target, up_cols] = up_vals
                    conn.update(worksheet=ws_name, data=df)
                    st.success("✅ 동기화 완료!")
                    st.rerun()
                except Exception as err:
                    st.error(f"수정 실패: {err}")

# --- 상단 영역: 차트 및 최우선 타겟 ---
col_chart, col_focus = st.columns([2, 1])

with col_chart:
    st.subheader("📊 우선순위 맵 (Scatter Plot)")
    if not df.empty:
        fig = px.scatter(df, x="진행률", y="우선순위", size="우선순위", color="작업명", 
                         hover_data=df.columns, text="작업명", range_x=[-5, 105], range_y=[0, 120])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("표시할 데이터가 없습니다.")

with col_focus:
    st.subheader("🎯 최우선 집중 타겟")
    pending = df[df["진행률"] < 100].sort_values(by="우선순위", ascending=False)
    if not pending.empty:
        top = pending.iloc[0]
        st.warning(f"**현재 집중: {top['작업명']}**")
        st.progress(int(top['진행률']))
        if st.button("✅ 완료 (시트에서 삭제)"):
            new_df = df[df["작업명"] != top["작업명"]]
            conn.update(worksheet=ws_name, data=new_df)
            st.balloons()
            st.rerun()
    else:
        st.success("모든 목표를 달성했습니다!")

# --- 하단 영역: 지난 이력 (데이터 리스트) ---
st.divider()
st.subheader("📋 지난 이력 (전체 데이터 리스트)")
if not df.empty:
    # 점수가 높은 순(우선순위 순)으로 정렬하여 표로 표시
    history_df = df.sort_values(by="우선순위", ascending=False)
    st.dataframe(history_df, use_container_width=True)
else:
    st.info("데이터 리스트가 비어 있습니다.")