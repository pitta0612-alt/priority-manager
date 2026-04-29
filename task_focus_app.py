import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# [설정] 구글 스프레드시트 고유 ID (사용자님 시트 주소에서 추출)
SPREADSHEET_ID = "1v4cSD3FMYfIWxMdkK9t6wD3MNcAt_h-knP4GH6EsgJ0"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=0"

st.set_page_config(page_title="우선순위 관리기 v34", layout="wide")

# 연결 초기화
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(worksheet_name):
    try:
        # 데이터 읽기 시도 (ttl=0으로 실시간성 확보)
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        # 빈 데이터나 헤더만 있는 경우 처리
        if df is None or df.empty:
            raise ValueError
        # '작업명'이 비어있는 행(공백 행) 제거
        df = df.dropna(subset=["작업명"])
        return df
    except:
        # 오류 발생 시 섹션별 기본 틀 반환
        if worksheet_name == "work":
            return pd.DataFrame(columns=["작업명", "우선순위", "진행률", "긴급도", "중요도", "의존성", "효율성"])
        else:
            return pd.DataFrame(columns=["작업명", "우선순위", "진행률", "중요도", "효율성", "난이도"])

# --- 섹션 및 데이터 로드 ---
section = st.sidebar.selectbox("📂 섹션 선택", ["업무(Work)", "공부(Study)"])
ws_name = "work" if "업무" in section else "study"
st.title(f"🛡️ {section} 시스템 (Cloud Sync)")

df = load_data(ws_name)

# --- 사이드바 제어 ---
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
                    conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=updated_df)
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
                    conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=df)
                    st.success("✅ 동기화 완료!")
                    st.rerun()
                except Exception as err:
                    st.error(f"수정 실패: {err}")
        else:
            st.warning("수정할 데이터가 없습니다.")

# --- 메인 화면 레이아웃 ---
col_chart, col_focus = st.columns([2, 1])

with col_chart:
    st.subheader("📊 우선순위 맵")
    if not df.empty:
        fig = px.scatter(df, x="진행률", y="우선순위", size="우선순위", color="작업명", 
                         hover_data=df.columns, text="작업명", range_x=[-5, 105], range_y=[0, 120])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("시트에 데이터가 없습니다. 사이드바에서 추가해 주세요.")

with col_focus:
    st.subheader("🎯 최우선 타겟")
    pending = df[df["진행률"] < 100].sort_values(by="우선순위", ascending=False)
    if not pending.empty:
        top = pending.iloc[0]
        st.warning(f"**현재 집중: {top['작업명']}**")
        st.progress(int(top['진행률']))
        if st.button("✅ 완료 (시트에서 삭제)"):
            try:
                new_df = df[df["작업명"] != top["작업명"]]
                conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=new_df)
                st.balloons()
                st.rerun()
            except Exception as err:
                st.error(f"삭제 실패: {err}")
    else:
        st.success("모든 업무가 완료되었습니다!")