import streamlit as st
import base64
from pathlib import Path


def apply_custom_theme() -> None:
    """Apply comprehensive professional design system with color palette, dark mode, and custom components."""
    bg_path = Path(__file__).resolve().parents[2] / "static" / "bg.webp"
    if not bg_path.exists():
        bg_path = Path(__file__).resolve().parents[2] / "static" / "bg.png"

    background_layer = "none"
    if bg_path.exists():
        mime_type = "image/webp" if bg_path.suffix.lower() == ".webp" else "image/png"
        encoded = base64.b64encode(bg_path.read_bytes()).decode("utf-8")
        background_layer = f"url('data:{mime_type};base64,{encoded}')"

    st.markdown(
        f"""
        <style>
          /* ===== DESIGN SYSTEM COLOR PALETTE ===== */
          :root {{
            --primary: #1f4e79;
            --primary-light: #2563eb;
            --secondary: #2bb3c0;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
            --text-dark: #0f172a;
            --text-light: #475569;
            --bg-light: #f5f7fa;
            --bg-white: #ffffff;
            --border: #cbd5e1;
          }}

          /* ===== SCROLLBAR STYLING ===== */
          ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
          }}
          ::-webkit-scrollbar-track {{
            background: #f1f5f9;
          }}
          ::-webkit-scrollbar-thumb {{
            background: #cbd5e1;
            border-radius: 4px;
          }}
          ::-webkit-scrollbar-thumb:hover {{
            background: #94a3b8;
          }}

          /* ===== GLOBAL APP STYLING ===== */
          .stApp > header {{
            background-color: transparent !important;
            padding: 0 !important;
          }}
          
          .stAppViewContainer {{
            padding-top: 1rem !important;
          }}

          .stApp {{
            background-image: {background_layer} !important;
            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
          }}
          
          /* ===== SIDEBAR ===== */
          [data-testid="stSidebar"] {{
            background-color: #f8fbff !important;
            background-image: linear-gradient(180deg, rgba(248, 251, 255, 0.88) 0%, rgba(248, 251, 255, 0.82) 100%), {background_layer} !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            border-right: 1px solid #dbe7f3 !important;
          }}
          
          [data-testid="stSidebar"] * {{
            color: #0f172a !important;
          }}

          html[data-theme="dark"] [data-testid="stSidebar"],
          body[data-theme="dark"] [data-testid="stSidebar"] {{
            background-color: #f8fbff !important;
            background-image: linear-gradient(180deg, rgba(248, 251, 255, 0.88) 0%, rgba(248, 251, 255, 0.82) 100%), {background_layer} !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            border-right: 1px solid #dbe7f3 !important;
          }}

          /* ===== TYPOGRAPHY ===== */
          .stApp h1 {{
            background: linear-gradient(90deg, #1f4e79 0%, #2bb3c0 100%);
            color: white !important;
            padding: 20px 24px;
            border-radius: 14px;
            box-shadow: 0 6px 20px rgba(31, 78, 121, 0.25);
            margin-bottom: 20px;
          }}

          .stApp h2 {{
            color: #1f4e79 !important;
            margin-bottom: 16px;
            font-weight: 700 !important;
          }}

          .stApp h3 {{
            color: #1f4e79 !important;
            font-weight: 600 !important;
          }}

          .stMarkdown, .stText, label {{
            color: #1f2937 !important;
          }}

          /* Hide default Streamlit divider */
          hr {{
            display: none !important;
          }}

          /* ===== BUTTONS ===== */
          /* Shared shape for all buttons */
          .stButton button,
          .stFormSubmitButton button,
          .stDownloadButton button {{
            border-radius: 8px !important;
            min-height: 46px !important;
            padding: 10px 22px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            transition: all 0.2s ease !important;
          }}

          /* Primary = Simpan style (red) */
          .stButton button[kind="primary"],
          .stButton button[data-testid="baseButton-primary"],
          .stFormSubmitButton button[kind="primary"],
          .stFormSubmitButton button[data-testid="baseButton-primary"] {{
            background: linear-gradient(180deg, #cf1649 0%, #b90f40 100%) !important;
            color: #ffffff !important;
            border: 1px solid #a80f3a !important;
            box-shadow: 0 3px 10px rgba(185, 15, 64, 0.28) !important;
          }}

          .stButton button[kind="primary"] span,
          .stButton button[kind="primary"] p,
          .stButton button[data-testid="baseButton-primary"] span,
          .stButton button[data-testid="baseButton-primary"] p,
          .stFormSubmitButton button[kind="primary"] span,
          .stFormSubmitButton button[kind="primary"] p {{
            color: #ffffff !important;
            fill: #ffffff !important;
          }}

          .stButton button[kind="primary"]:hover,
          .stButton button[data-testid="baseButton-primary"]:hover,
          .stFormSubmitButton button[kind="primary"]:hover,
          .stFormSubmitButton button[data-testid="baseButton-primary"]:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 14px rgba(185, 15, 64, 0.34) !important;
            filter: brightness(0.97) !important;
          }}

          /* Secondary = Reset style (blue filled, no white button) */
          .stButton button[kind="secondary"],
          .stButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]),
          .stFormSubmitButton button[kind="secondary"],
          .stFormSubmitButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {{
            background: linear-gradient(180deg, #2f5f90 0%, #214f7b 100%) !important;
            color: #ffffff !important;
            border: 1px solid #1b4368 !important;
            box-shadow: 0 3px 10px rgba(33, 79, 123, 0.24) !important;
          }}

          .stButton button[kind="secondary"]:hover,
          .stButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover,
          .stFormSubmitButton button[kind="secondary"]:hover,
          .stFormSubmitButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {{
            background: linear-gradient(180deg, #2a5685 0%, #1b4368 100%) !important;
            border-color: #173956 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 14px rgba(33, 79, 123, 0.32) !important;
            filter: brightness(0.98) !important;
          }}

          /* Sidebar Button */
          [data-testid="stSidebar"] .stButton button[kind="primary"],
          [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {{
            background: linear-gradient(180deg, #2f5f90 0%, #214f7b 100%) !important;
            color: #ffffff !important;
            border: 1px solid #1b4368 !important;
            box-shadow: 0 3px 10px rgba(33, 79, 123, 0.24) !important;
          }}

          [data-testid="stSidebar"] .stButton button[kind="primary"]:hover,
          [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"]:hover {{
            background: linear-gradient(180deg, #2a5685 0%, #1b4368 100%) !important;
            box-shadow: 0 6px 14px rgba(33, 79, 123, 0.32) !important;
          }}

          /* Download Button */
          .stDownloadButton button {{
            background: linear-gradient(180deg, #039b22 0%, #02851d 100%) !important;
            color: white !important;
            border: 1px solid #027519 !important;
            box-shadow: 0 3px 10px rgba(2, 133, 29, 0.28) !important;
          }}

          .stDownloadButton button:hover {{
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 14px rgba(2, 133, 29, 0.34) !important;
            filter: brightness(0.97) !important;
          }}

          /* Disabled Button */
          .stButton button:disabled,
          .stFormSubmitButton button:disabled,
          .stDownloadButton button:disabled {{
            background: #f3f4f6 !important;
            color: #9ca3af !important;
            border: 1px solid #e5e7eb !important;
            cursor: not-allowed !important;
            opacity: 0.6 !important;
          }}

          /* ===== INPUT FIELDS ===== */
          .stTextInput input,
          .stTextArea textarea,
          .stSelectbox select,
          .stNumberInput input,
          .stDateInput input,
          .stTimeInput input {{
            border-radius: 10px !important;
            border: 1.5px solid #cbd5e1 !important;
            background: white !important;
            transition: all 0.2s ease !important;
            font-size: 0.95rem !important;
          }}
          
          .stTextInput input:focus,
          .stTextArea textarea:focus,
          .stSelectbox select:focus,
          .stNumberInput input:focus,
          .stDateInput input:focus,
          .stTimeInput input:focus {{
            border-color: #2bb3c0 !important;
            box-shadow: 0 0 0 3px rgba(43, 179, 192, 0.08) !important;
          }}

          html[data-theme="dark"] .stTextInput input,
          body[data-theme="dark"] .stTextInput input,
          html[data-theme="dark"] .stTextArea textarea,
          body[data-theme="dark"] .stTextArea textarea,
          html[data-theme="dark"] .stSelectbox select,
          body[data-theme="dark"] .stSelectbox select {{
            background: #1e293b !important;
            border-color: #475569 !important;
            color: #e2e8f0 !important;
          }}

          /* ===== EXPANDERS ===== */
          .streamlit-expanderHeader {{
            background: linear-gradient(90deg, rgba(31, 78, 121, 0.08), rgba(43, 179, 192, 0.08)) !important;
            border-radius: 10px !important;
            border: 1.5px solid rgba(31, 78, 121, 0.2) !important;
            font-weight: 600 !important;
            color: #1f4e79 !important;
            padding: 12px !important;
            transition: all 0.2s ease !important;
          }}
          
          .streamlit-expanderHeader:hover {{
            background: linear-gradient(90deg, rgba(31, 78, 121, 0.12), rgba(43, 179, 192, 0.12)) !important;
            border-color: rgba(31, 78, 121, 0.4) !important;
          }}
          
          .streamlit-expanderContent {{
            background: white !important;
            border-radius: 0 0 10px 10px !important;
            border: 1.5px solid rgba(31, 78, 121, 0.15) !important;
            border-top: none !important;
            padding: 16px !important;
          }}

          html[data-theme="dark"] .streamlit-expanderHeader,
          body[data-theme="dark"] .streamlit-expanderHeader {{
            background: linear-gradient(90deg, rgba(30, 77, 122, 0.2), rgba(27, 109, 131, 0.2)) !important;
            border-color: rgba(148, 163, 184, 0.2) !important;
            color: #93c5fd !important;
          }}

          html[data-theme="dark"] .streamlit-expanderContent,
          body[data-theme="dark"] .streamlit-expanderContent {{
            background: #1e293b !important;
            border-color: rgba(148, 163, 184, 0.2) !important;
          }}

          /* ===== METRICS & TABLES ===== */
          [data-testid="stMetric"] {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 18px;
            border-radius: 12px;
            border: 1px solid rgba(31, 78, 121, 0.1);
            box-shadow: 0 4px 12px rgba(31, 78, 121, 0.08);
          }}
          
          [data-testid="stMetricLabel"] {{
            color: #1f4e79 !important;
            font-weight: 600 !important;
          }}
          
          [data-testid="stMetricValue"] {{
            color: #2bb3c0 !important;
            font-weight: 700 !important;
          }}

          .stDataFrame {{
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 4px 12px rgba(31, 78, 121, 0.08) !important;
          }}
          
          .stDataFrame table {{
            background: white !important;
          }}
          
          .stDataFrame thead tr th {{
            background: linear-gradient(90deg, #1f4e79, #2bb3c0) !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 12px !important;
          }}
          
          .stDataFrame tbody tr:nth-child(even) {{
            background: rgba(31, 78, 121, 0.03) !important;
          }}

          /* ===== ALERTS ===== */
          .stAlert {{
            border-radius: 10px !important;
            border: 1px solid;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
          }}
          
          div[data-baseweb="notification"][kind="info"] {{
            background: rgba(191, 219, 254, 0.95) !important;
            border-color: #3b82f6 !important;
            color: #1e40af !important;
          }}
          
          div[data-baseweb="notification"][kind="success"] {{
            background: rgba(209, 250, 229, 0.95) !important;
            border-color: #10b981 !important;
            color: #065f46 !important;
          }}
          
          div[data-baseweb="notification"][kind="warning"] {{
            background: rgba(254, 243, 199, 0.95) !important;
            border-color: #f59e0b !important;
            color: #78350f !important;
          }}
          
          div[data-baseweb="notification"][kind="error"] {{
            background: rgba(254, 226, 226, 0.95) !important;
            border-color: #ef4444 !important;
            color: #7f1d1d !important;
          }}

          /* ===== CARD COMPONENTS ===== */
          .td-form-card {{
            background: white;
            border-radius: 14px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 16px rgba(31, 78, 121, 0.08);
            padding: 28px;
            max-width: 520px;
            margin: 0 auto 20px auto;
          }}

          html[data-theme="dark"] .td-form-card,
          body[data-theme="dark"] .td-form-card {{
            background: #1e293b;
            border-color: #475569;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
          }}

          .td-page-intro-card,
          .td-feature-card,
          .td-section-card {{
            border: 1px solid rgba(31, 78, 121, 0.15);
            border-radius: 14px;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.94);
            box-shadow: 0 4px 12px rgba(31, 78, 121, 0.08);
            margin-bottom: 12px;
          }}

          .td-page-intro-card {{
            border-left: 4px solid #1f4e79;
          }}

          html[data-theme="dark"] .td-page-intro-card,
          body[data-theme="dark"] .td-page-intro-card {{
            background: #1e293b;
            border-color: rgba(148, 163, 184, 0.2);
            border-left-color: #2bb3c0;
          }}

          .td-feature-title {{
            font-size: 1.08rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 4px 0;
          }}

          .td-feature-desc {{
            font-size: 0.94rem;
            color: #334155;
            margin: 0;
            line-height: 1.5;
          }}

          html[data-theme="dark"] .td-feature-title,
          body[data-theme="dark"] .td-feature-title {{
            color: #e0f2fe;
          }}

          html[data-theme="dark"] .td-feature-desc,
          body[data-theme="dark"] .td-feature-desc {{
            color: #cbd5e1;
          }}

          /* ===== NAVIGATION CARDS (GRID) ===== */
          .td-nav-card {{
            min-height: 170px;
            border-radius: 18px;
            background: white;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 14px rgba(31, 78, 121, 0.09);
            text-align: center;
            padding: 16px 12px 12px 12px;
            margin-bottom: 8px;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
          }}

          .td-nav-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(31, 78, 121, 0.12);
            border-color: #2bb3c0;
          }}

          .td-nav-icon {{
            font-size: 2.4rem;
            line-height: 1;
            margin-bottom: 10px;
          }}

          .td-nav-title {{
            font-size: 1.02rem;
            font-weight: 700;
            color: #1f4e79;
            margin-bottom: 6px;
          }}

          .td-nav-desc {{
            font-size: 0.86rem;
            color: #64748b;
            line-height: 1.35;
            min-height: 34px;
          }}

          html[data-theme="dark"] .td-nav-card,
          body[data-theme="dark"] .td-nav-card {{
            background: #1e293b;
            border-color: #475569;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
          }}

          html[data-theme="dark"] .td-nav-card:hover,
          body[data-theme="dark"] .td-nav-card:hover {{
            border-color: #2bb3c0;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
          }}

          html[data-theme="dark"] .td-nav-title,
          body[data-theme="dark"] .td-nav-title {{
            color: #e0f2fe;
          }}

          html[data-theme="dark"] .td-nav-desc,
          body[data-theme="dark"] .td-nav-desc {{
            color: #cbd5e1;
          }}

          /* ===== CLICKABLE NAVIGATION CARDS (NEW) ===== */
          .td-nav-card-clickable {{
            min-height: 170px;
            border-radius: 18px;
            background: white;
            border: 2px solid #e2e8f0;
            box-shadow: 0 4px 14px rgba(31, 78, 121, 0.09);
            text-align: center;
            padding: 16px 12px 12px 12px;
            margin-bottom: 8px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            user-select: none;
          }}

          .td-nav-card-clickable:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(31, 78, 121, 0.18);
            border-color: #2bb3c0;
            background: #f0f9fc;
          }}

          .td-nav-card-clickable:active {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(31, 78, 121, 0.12);
          }}

          .td-nav-icon {{
            font-size: 2.4rem;
            line-height: 1;
            margin-bottom: 10px;
          }}

          .td-nav-title {{
            font-size: 1.02rem;
            font-weight: 700;
            color: #1f4e79;
            margin-bottom: 6px;
          }}

          .td-nav-desc {{
            font-size: 0.86rem;
            color: #64748b;
            line-height: 1.35;
            min-height: 34px;
          }}

          html[data-theme="dark"] .td-nav-card-clickable,
          body[data-theme="dark"] .td-nav-card-clickable {{
            background: #1e293b;
            border-color: #475569;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
          }}

          html[data-theme="dark"] .td-nav-card-clickable:hover,
          body[data-theme="dark"] .td-nav-card-clickable:hover {{
            background: #0f172a;
            border-color: #2bb3c0;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
          }}

          html[data-theme="dark"] .td-nav-card-clickable:active,
          body[data-theme="dark"] .td-nav-card-clickable:active {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2);
          }}

          /* ===== SPACING & LAYOUT ===== */
          [data-testid="column"] {{
            padding-top: 0 !important;
          }}

          .block-container {{
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )
