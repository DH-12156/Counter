import streamlit as st
import google.generativeai as genai
import random
import time

# ==========================================
# 1. 基本設定
# ==========================================
st.set_page_config(page_title="NEXUS", page_icon="🧬", layout="wide")

# CSS: シンプル・頑丈・見やすい
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; color: #333; }
    .header-box {
        padding: 20px; border-radius: 10px; background: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; border-left: 10px solid #333;
    }
    .info-card {
        background: white; padding: 15px; border-radius: 8px; border: 1px solid #ddd;
        height: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .info-title {
        font-size: 0.85em; color: #666; font-weight: bold; 
        border-bottom: 2px solid #f0f0f0; margin-bottom: 10px; padding-bottom: 5px;
    }
    .info-val { font-weight: bold; color: #333; font-size: 1.1em; }
    .mission-bar {
        background-color: #333; color: white; padding: 15px; text-align: center; 
        font-weight: bold; border-radius: 8px; margin-bottom: 25px; font-size: 1.2em;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 商材データ
# ==========================================
THEMES = {
    "① PI（乗り換え）": {"color": "#E60012", "icon": "🔥"},
    "② プラン変更": {"color": "#E91E63", "icon": "📱"},
    "③ S4（オプション満載）": {"color": "#673AB7", "icon": "🛡️"},
    "④ イエナカ（光・HOME 5G）": {"color": "#0091EA", "icon": "📶"},
    "⑤ Pixelスイッチ": {"color": "#2E7D32", "icon": "🎨"},
    "⑥ dカード（GOLD）": {"color": "#F9A825", "icon": "💳"},
    "⑦ 電気・ガス": {"color": "#EF6C00", "icon": "💡"}
}

TARGET_COURSES = {
    "① PI（乗り換え）": {"goal": "MNP成約", "prompt": "現在au/SB利用。メリットを感じていない。"},
    "② プラン変更": {"goal": "ポイ活/eximo成約", "prompt": "制限中、またはポイ活興味あり。"},
    "③ S4（オプション満載）": {"goal": "6点フル成約", "prompt": "セキュリティ意識低い。リスク訴求必要。"},
    "④ イエナカ（光・HOME 5G）": {"goal": "解約新規・成約", "prompt": "他社光/遅い回線利用中。速度不満。"},
    "⑤ Pixelスイッチ": {"goal": "Pixel成約", "prompt": "iPhone(古)などを利用中。"},
    "⑥ dカード（GOLD）": {"goal": "GOLD/PLATINUM成約", "prompt": "現金派。年会費懸念。"},
    "⑦ 電気・ガス": {"goal": "", "prompt": "地域電力利用中。まとめるメリット提示。"}
}

# ==========================================
# 3. サイドバー（モデル自動取得・エラー回避ロジック）
# ==========================================
with st.sidebar:
    st.title("🧬 NEXUS System")
    api_key = st.text_input("🔑 API Key", type="password")
    
    # デフォルトのモデル（万が一リスト取得に失敗した場合用）
    model_options = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    
    # APIキーがある場合、実際に使えるモデルリストを取りに行く
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Googleに問い合わせる
            fetched_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    # モデル名（models/gemini-1.5-flash 等）をそのままリストへ
                    fetched_models.append(m.name.replace("models/", ""))
            
            if fetched_models:
                model_options = fetched_models
                st.success(f"✅ 接続成功（{len(fetched_models)}個のモデルを確認）")
            
        except Exception as e:
            st.warning("⚠️ モデルリストの取得に失敗しました（標準リストを使います）")
    
    # ユーザーが選択（ここで選ばれたモデル名は確実に存在するはず）
    selected_model = st.selectbox("使用モデル:", model_options)

    st.markdown("---")
    mission_key = st.selectbox("強化商材:", list(TARGET_COURSES.keys()))
    mood_selector = st.selectbox("お客様タイプ:", ["ランダム", "じっくり聞く(普通)", "怒っている(難)", "教えて(易)", "急いでいる(短)"])
    
    if st.button("🔄 リセット"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# 4. メイン処理
# ==========================================
if api_key:
    # 選択されたモデルで設定
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(selected_model)
    except:
        st.error("モデル設定エラー。別のモデルを選んでください。")

    theme = THEMES[mission_key]
    course = TARGET_COURSES[mission_key]
    
    # 色適用
    st.markdown(f"""
    <style>
        .header-box {{ border-left-color: {theme['color']}; }}
        .mission-bar {{ background-color: {theme['color']}; }}
    </style>
    """, unsafe_allow_html=True)

    # ミッションバー
    mission_text = f"{theme['icon']} MISSION: {mission_key} 成約を目指せ！"
    if course['goal']:
        mission_text += f" ({course['goal']})"
    st.markdown(f"<div class='mission-bar'>{mission_text}</div>", unsafe_allow_html=True)

    # セッション管理
    if "stage" not in st.session_state:
        st.session_state.stage = 0
        st.session_state.customer_data = {}
        st.session_state.emotion = "neutral"
        st.session_state.messages = []

    # --- 待機画面 ---
    if st.session_state.stage == 0:
        st.markdown(f"<h2 style='text-align:center; color:{theme['color']};'>🧬 NEXUS TRAINING</h2>", unsafe_allow_html=True)
        st.caption(f"使用中モデル: {selected_model}")
        
        # ボタンを押した時だけ通信
        if st.button("👥 お客様を呼び出す", type="primary", use_container_width=True):
            with st.spinner("お客様来店中..."):
                try:
                    # プロンプト
                    prompt = f"""
                    ドコモショップに来店する日本人顧客プロフィールを作成せよ。
                    商材：{mission_key}
                    設定：{course['prompt']}
                    性格指定：{mood_selector}
                    
                    【出力項目】
                    名前：(日本人名)
                    性別：(男性/女性)
                    年代：(例:20代)
                    性格：(一言で)
                    現機種：(機種名 + 利用年数。例:iPhone12(3年))
                    現プラン：(eximo/irumo/ギガホなど)
                    dカードランク：(REGULAR/GOLD/GOLD U/PLATINUM/なし)
                    dカード利用額：(例:月5万 / なし)
                    Wi-Fi：(例:ドコモ光(1Gbps/5720円) / HOME 5G / なし)
                    TV契約：(あり/なし)
                    電話契約：(あり/なし)
                    電気ガス：(例:東京電力/東京ガス)
                    来店目的：(料金支払い/充電器購入/パスワード忘れ/操作説明/迷惑メール相談/フィルム貼替え からランダム1つ)
                    """
                    
                    response = model.generate_content(prompt)
                    text = response.text
                    
                    # データ抽出
                    data = {}
                    for line in text.split('\n'):
                        if "：" in line:
                            p = line.split("：", 1)
                            data[p[0].strip()] = p[1].strip()
                        elif ":" in line:
                            p = line.split(":", 1)
                            data[p[0].strip()] = p[1].strip()
                    
                    st.session_state.customer_data = data
                    
                    # イラストURL
                    seed = random.randint(1000, 9999)
                    st.session_state.avatar_url = f"https://api.dicebear.com/7.x/personas/png?seed={seed}"
                    
                    st.session_state.stage = 1
                    st.rerun()

                except Exception as e:
                    st.error(f"通信エラー: {e}")
                    st.warning("⚠️ エラーが出た場合、サイドバーの「使用モデル」を別のもの（例: gemini-1.5-flash）に変更してみてください。")

    # --- 接客画面 ---
    elif st.session_state.stage >= 1:
        data = st.session_state.customer_data
        
        st.markdown(f"""
        <div class="header-box">
            <h3>👤 {data.get('名前','お客様')} <small>({data.get('年代','')} {data.get('性別','')})</small></h3>
            <div style="color:{theme['color']}; font-weight:bold;">🚩 来店目的：{data.get('来店目的','')}</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="info-card"><div class="info-title">📱 端末/プラン</div><div class="info-val">{data.get('現機種','-')}<br>{data.get('現プラン','-')}</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="info-card"><div class="info-title">💳 dカード</div><div class="info-val">{data.get('dカードランク','-')}<br>{data.get('dカード利用額','-')}</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="info-card"><div class="info-title">🏠 ネット/TV</div><div class="info-val">{data.get('Wi-Fi','-')}<br>TV:{data.get('TV契約','-')} TEL:{data.get('電話契約','-')}</div></div>""", unsafe_allow_html=True)
        with c4:
            eg_val = data.get('電気ガス','-')
            if mission_key == "⑦ 電気・ガス":
                eg_val = f"<span style='color:{theme['color']}'>{eg_val}</span>"
            st.markdown(f"""<div class="info-card"><div class="info-title">⚡ 電気・ガス</div><div class="info-val">{eg_val}</div></div>""", unsafe_allow_html=True)

        st.write("") 

        col_img, col_chat = st.columns([1, 2])
        
        with col_img:
            st.image(st.session_state.avatar_url, width=200)
            st.info(f"**性格**: {data.get('性格','普通')}")
            
            emo = st.session_state.emotion
            emo_icon = "😐 普通"
            if emo == "angry": emo_icon = "💢 不機嫌"
            elif emo == "happy": emo_icon = "🥰 満足"
            st.write(f"### 感情: {emo_icon}")

            if st.session_state.stage == 1:
                if st.button("🔥 接客スタート", type="primary"):
                    st.session_state.stage = 2
                    try:
                        first_prompt = f"設定：{str(data)}。来店目的について店員に話しかけられた。用件を済ませたい。性格に合わせて第一声を返して。"
                        res = model.generate_content(first_prompt)
                        st.session_state.messages.append({"role": "model", "parts": [res.text]})
                        st.rerun()
                    except Exception as e:
                        st.error(f"通信エラー: {e}")

        with col_chat:
            if st.session_state.stage == 2:
                # チャット履歴
                chat_box = st.container(height=400)
                with chat_box:
                    for msg in st.session_state.messages:
                        role = "あなた" if msg["role"] == "user" else "お客様"
                        icon = "🧑‍💼" if role == "あなた" else "👤"
                        st.chat_message(msg["role"], avatar=icon).write(msg["parts"][0])
                
                # 入力欄
                user_input = st.chat_input("提案トークを入力...")
                if user_input:
                    st.session_state.messages.append({"role": "user", "parts": [user_input]})
                    
                    logic_prompt = f"""
                    客として振る舞え。設定：{str(data)}。目標：{course['goal']}。
                    直前の店員の言葉：{user_input}
                    1. 「来店目的」が未解決なら営業に怒る。
                    2. 解決済みでメリットがあれば興味を持つ。
                    3. 最後に感情タグ <emo>angry/neutral/happy</emo> をつける。
                    """
                    
                    try:
                        history = [{"role": m["role"], "parts": m["parts"]} for m in st.session_state.messages]
                        chat = model.start_chat(history=history[:-1])
                        response = chat.send_message(logic_prompt)
                        
                        text = response.text
                        new_emo = "neutral"
                        if "<emo>angry</emo>" in text: new_emo = "angry"
                        elif "<emo>happy</emo>" in text: new_emo = "happy"
                        
                        clean_text = text.replace("<emo>angry</emo>", "").replace("<emo>happy</emo>", "").replace("<emo>neutral</emo>", "")
                        
                        st.session_state.emotion = new_emo
                        st.session_state.messages.append({"role": "model", "parts": [clean_text]})
                        st.rerun()
                    except Exception as e:
                        st.error(f"通信エラー: {e}")
                        st.warning("サイドバーでモデルを変更して再試行してください。")

else:
    st.info("👈 左のサイドバーにAPIキーを入れてください")