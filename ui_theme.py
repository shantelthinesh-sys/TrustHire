import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Manrope', 'Segoe UI', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 10% 20%, rgba(255, 186, 146, 0.28), transparent 30%),
                radial-gradient(circle at 90% 10%, rgba(77, 164, 255, 0.24), transparent 36%),
                linear-gradient(135deg, #f6fbff 0%, #eef4fb 45%, #f9f3ea 100%);
        }

        .th-hero {
            border-radius: 18px;
            padding: 18px 22px;
            background: linear-gradient(120deg, #0a2a43 0%, #114f73 55%, #1d7aa8 100%);
            color: #f5fbff;
            border: 1px solid rgba(255,255,255,0.18);
            box-shadow: 0 10px 30px rgba(12, 50, 84, 0.25);
            margin-bottom: 16px;
        }

        .th-hero h1 {
            margin: 0;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: 0.2px;
        }

        .th-hero p {
            margin: 6px 0 0;
            opacity: 0.93;
            font-size: 0.98rem;
        }

        .th-card {
            background: rgba(255, 255, 255, 0.72);
            backdrop-filter: blur(4px);
            border: 1px solid rgba(11, 52, 83, 0.12);
            border-radius: 16px;
            padding: 12px 14px;
            margin-bottom: 10px;
            box-shadow: 0 8px 24px rgba(18, 56, 92, 0.08);
        }

        .stButton>button {
            border-radius: 999px;
            border: 1px solid rgba(11, 52, 83, 0.18);
            font-weight: 700;
        }

        .stTextInput>div>div>input, .stTextArea textarea {
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="th-hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(text: str) -> None:
    st.markdown(f"<div class='th-card'>{text}</div>", unsafe_allow_html=True)
