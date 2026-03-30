import streamlit as st


def apply_custom_theme() -> None:
    st.markdown(
        """
        <style>
          /* Fix header spacing untuk menghindari toolbar */
          .stApp > header {
            background-color: transparent !important;
            padding: 0 !important;
          }
          
          .stAppViewContainer {
            padding-top: 1rem !important;
          }
          
          /* Main Background Gradient - Soft & Subtle */
          .stApp {
            background: linear-gradient(135deg, #e0e7ff 0%, #dbeafe 25%, #f0f9ff 50%, #ecfeff 75%, #f0fdfa 100%);
            background-size: 400% 400%;
            animation: gradientShift 20s ease infinite;
          }
          
          @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
          }
          
          /* Sidebar Gradient */
          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
          }
          
          [data-testid="stSidebar"] * {
            color: white !important;
          }
          
          /* Hero Banner Style for Main Header */
          .stApp h1 {
            background: linear-gradient(90deg, #1e40af 0%, #06b6d4 100%);
            color: white !important;
            padding: 20px 24px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            margin-bottom: 20px;
          }

          .stApp h2 {
            color: #0f172a !important;
            margin-bottom: 16px;
          }
          
          /* Horizontal Divider Styling */
          hr {
            border: none !important;
            height: 2px !important;
            background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.5), transparent) !important;
            margin: 24px 0 !important;
          }
          
          /* Main content panel */
          .main .block-container {
            background: rgba(255, 255, 255, 0.42);
            border: 1px solid rgba(255, 255, 255, 0.45);
            border-radius: 24px;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(10px);
            padding: 2rem 2rem 1.5rem 2rem !important;
          }

          /* Tool Title (h3) */
          h3 {
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            margin-bottom: 8px !important;
            margin-top: 0 !important;
            padding: 0 !important;
            color: #1d4ed8 !important;
            background: none !important;
            -webkit-text-fill-color: initial !important;
            box-shadow: none !important;
            border-radius: 0 !important;
          }
          
          /* Tool Description */
          p {
            color: #334155 !important;
            font-size: 0.98rem !important;
            line-height: 1.6 !important;
          }

          .stMarkdown, .stText, label {
            color: #1f2937 !important;
          }
          
          /* Column alignment */
          [data-testid="column"] {
            padding-top: 0 !important;
            display: flex !important;
            align-items: center !important;
          }
          
          /* Section Cards */
          .section-card {
            border: 2px solid rgba(59, 130, 246, 0.2);
            border-radius: 14px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
            margin-bottom: 16px;
          }
          
          /* Primary Buttons - Blue-Cyan Gradient */
          .stButton button[kind="primary"],
          .stButton button[data-testid="baseButton-primary"] {
            background: linear-gradient(90deg, #1e40af 0%, #06b6d4 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3) !important;
            transition: all 0.3s ease !important;
            min-height: 42px !important;
          }

          .stButton button[kind="primary"] span,
          .stButton button[kind="primary"] p,
          .stButton button[data-testid="baseButton-primary"] span,
          .stButton button[data-testid="baseButton-primary"] p {
            color: white !important;
            fill: white !important;
          }
          
          .stButton button[kind="primary"]:hover,
          .stButton button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(6, 182, 212, 0.4) !important;
          }

          /* Sidebar primary button (Logout) - Black */
          [data-testid="stSidebar"] .stButton button[kind="primary"],
          [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {
            background: #111827 !important;
            color: #ffffff !important;
            border: 1px solid #111827 !important;
            box-shadow: 0 4px 12px rgba(17, 24, 39, 0.35) !important;
          }

          [data-testid="stSidebar"] .stButton button[kind="primary"]:hover,
          [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"]:hover {
            background: #000000 !important;
            border-color: #000000 !important;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.45) !important;
          }
          
          /* Download Buttons - Green Gradient */
          .stDownloadButton button {
            background: linear-gradient(90deg, #059669 0%, #10b981 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
            transition: all 0.3s ease !important;
            min-height: 42px !important;
          }

          .stDownloadButton button span,
          .stDownloadButton button p {
            color: white !important;
          }
          
          .stDownloadButton button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4) !important;
          }
          
          /* Secondary/Regular Buttons */
          .stButton button[kind="secondary"],
          .stButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
            background: rgba(255, 255, 255, 0.98) !important;
            color: #1e40af !important;
            border: 2px solid #93c5fd !important;
            border-radius: 8px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            transition: all 0.3s ease !important;
            min-height: 42px !important;
          }
          
          .stButton button[kind="secondary"]:hover,
          .stButton button:not([kind="primary"]):not([data-testid="baseButton-primary"]):hover {
            background: #eff6ff !important;
            border-color: #3b82f6 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 10px rgba(59, 130, 246, 0.2) !important;
          }
          
          /* Disabled Buttons */
          .stButton button:disabled {
            background: #f3f4f6 !important;
            color: #9ca3af !important;
            border: 2px solid #e5e7eb !important;
            cursor: not-allowed !important;
            opacity: 0.6 !important;
          }
          
          .stButton button:disabled:hover {
            transform: none !important;
            box-shadow: none !important;
          }
          
          /* Metric Cards */
          [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 18px;
            border-radius: 12px;
            border: 2px solid rgba(59, 130, 246, 0.3);
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
          }
          
          [data-testid="stMetricLabel"] {
            color: #1e40af !important;
            font-weight: 600 !important;
          }
          
          [data-testid="stMetricValue"] {
            color: #06b6d4 !important;
            font-weight: 700 !important;
          }
          
          /* Alert Boxes */
          .stAlert {
            border-radius: 12px !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
            backdrop-filter: blur(10px) !important;
          }
          
          /* Info Alert */
          div[data-baseweb="notification"][kind="info"] {
            background: rgba(191, 219, 254, 0.95) !important;
            border-left: 4px solid #3b82f6 !important;
          }
          
          /* Success Alert */
          div[data-baseweb="notification"][kind="success"] {
            background: rgba(209, 250, 229, 0.95) !important;
            border-left: 4px solid #10b981 !important;
          }
          
          /* Warning Alert */
          div[data-baseweb="notification"][kind="warning"] {
            background: rgba(254, 243, 199, 0.95) !important;
            border-left: 4px solid #f59e0b !important;
          }
          
          /* Error Alert */
          div[data-baseweb="notification"][kind="error"] {
            background: rgba(254, 226, 226, 0.95) !important;
            border-left: 4px solid #ef4444 !important;
          }
          
          /* Text Area Styling - untuk Excel input */
          .stTextArea textarea {
            background: rgba(255, 255, 255, 0.98) !important;
            border: 2px solid rgba(59, 130, 246, 0.3) !important;
            border-radius: 8px !important;
            padding: 12px !important;
            font-family: 'Courier New', monospace !important;
            font-size: 0.9rem !important;
          }
          
          .stTextArea textarea:focus {
            border-color: #06b6d4 !important;
            box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1) !important;
          }
          
          /* Expander Styling */
          .streamlit-expanderHeader {
            background: linear-gradient(90deg, rgba(30, 64, 175, 0.1), rgba(6, 182, 212, 0.1)) !important;
            border-radius: 10px !important;
            border: 2px solid rgba(59, 130, 246, 0.3) !important;
            font-weight: 600 !important;
            color: #1e40af !important;
            padding: 12px !important;
            transition: all 0.3s ease !important;
          }
          
          .streamlit-expanderHeader:hover {
            background: linear-gradient(90deg, rgba(30, 64, 175, 0.15), rgba(6, 182, 212, 0.15)) !important;
            border-color: rgba(59, 130, 246, 0.5) !important;
          }
          
          .streamlit-expanderContent {
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 0 0 10px 10px !important;
            border: 2px solid rgba(59, 130, 246, 0.2) !important;
            border-top: none !important;
            padding: 16px !important;
          }
          
          /* Code block styling */
          .stCodeBlock {
            border-radius: 8px !important;
            border: 1px solid rgba(59, 130, 246, 0.2) !important;
            background: rgba(240, 249, 255, 0.8) !important;
          }
          
          /* Dataframe Styling */
          .stDataFrame {
            border-radius: 12px !important;
            overflow: hidden !important;
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1) !important;
          }
          
          .stDataFrame table {
            background: rgba(255, 255, 255, 0.98) !important;
          }
          
          .stDataFrame thead tr th {
            background: linear-gradient(90deg, #1e40af, #06b6d4) !important;
            color: white !important;
            font-weight: 600 !important;
            padding: 12px !important;
          }
          
          .stDataFrame tbody tr:nth-child(even) {
            background: rgba(239, 246, 255, 0.5) !important;
          }
          
          /* Input Fields */
          .stTextInput input, .stTextArea textarea, .stSelectbox select {
            border-radius: 8px !important;
            border: 2px solid rgba(59, 130, 246, 0.3) !important;
            background: rgba(255, 255, 255, 0.95) !important;
            transition: all 0.3s ease !important;
          }
          
          .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
            border-color: #06b6d4 !important;
            box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1) !important;
          }
          
          /* File Uploader */
          [data-testid="stFileUploader"] {
            background: rgba(255, 255, 255, 0.95) !important;
            border: 2px dashed rgba(59, 130, 246, 0.4) !important;
            border-radius: 12px !important;
            padding: 20px !important;
          }
          
          /* Radio Buttons */
          .stRadio > div {
            background: rgba(255, 255, 255, 0.95) !important;
            padding: 12px !important;
            border-radius: 10px !important;
            border: 2px solid rgba(59, 130, 246, 0.2) !important;
          }
          
          /* Caption Text */
          .stCaption {
            color: #475569 !important;
            font-size: 0.9rem !important;
          }
          
          /* Compact Spacing */
          .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
