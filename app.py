import datetime
import base64
import html
import importlib
import time
import uuid
from pathlib import Path

import streamlit as st
import pandas as pd
from config import setting

from db import query, execute
from auth import login, seed_admin, is_admin, hash_password
import reports as report_module
report_module = importlib.reload(report_module)
members_report = report_module.members_report
payments_report = report_module.payments_report
excel_report = report_module.excel_report
member_payments_report = report_module.member_payments_report
printable_pdf = report_module.printable_pdf
from services.receipt import make_receipt
from services.upi import create_upi_qr
from services.whatsapp import configuration as whatsapp_configuration
from services.whatsapp import missing_configuration, normalize_indian_mobile
from services.whatsapp import send_template_message

BASE = Path(__file__).resolve().parent
LOGO = BASE / "assets" / "baliraja-logo.jpg"
UPLOADS = BASE / "uploads"
RECEIPTS = BASE / "receipts"
BACKUPS = BASE / "backups"
EXPORTS = BASE / "exports"

for folder in [UPLOADS, RECEIPTS, BACKUPS, EXPORTS]:
    folder.mkdir(exist_ok=True)
PUBLIC_GALLERY = BASE / "assets" / "public_gallery"
PUBLIC_GALLERY.mkdir(exist_ok=True)
PUBLIC_VIDEOS = BASE / "assets" / "public_videos"
PUBLIC_VIDEOS.mkdir(exist_ok=True)
MAX_PUBLIC_VIDEO_BYTES = 150 * 1024 * 1024


def show_table(frame, **kwargs):
    if not isinstance(frame, pd.DataFrame):
        st.dataframe(frame, **kwargs)
        return

    html_table = frame.to_html(index=not kwargs.get("hide_index", False), escape=True,
                               border=0, classes="app-data-table")
    st.markdown(f"<div class='app-table-wrap'>{html_table}</div>", unsafe_allow_html=True)


EXECUTIVE_BODY = [
    ("१", "अध्यक्ष (President)", "पंकज अरुणराव घोंगे", "वार्ड न. ३, बोरगाव (खु) पो. धापेवाडा, ता. कळमेश्वर, जी. नागपूर-४४१५०१", "७७७४९१२२३२"),
    ("२", "उपाध्यक्ष - १ (Vice-President 1)", "श्री. नरेशजी गुंडेरावजी राऊत", "c/o गुडेराव राऊत, वार्ड न.०३, मु-वरोडा, पो-ब्राम्हणी, त-कळमेश्वर-४४१५०१", "९८२२९४०४९३"),
    ("३", "उपाध्यक्ष - २ (Vice-President 2)", "अनिल किसनाजी बंड", "घर न. १०८, वार्ड न. ०३, कनियाडोल, कळमेश्वर, पिपला किनखेडा-४४१५०२", "९७६४९१७३६०"),
    ("४", "सचिव (General Secretary)", "प्रविण अनिल गोतमारे", "१९९, वार्ड न. ०३, हनुमान मंदिराजवळ, खैरी (हर्जी), पो-उपरवाही, त-कळमेश्वर-४४१५०१", "९०९६३४६४९२"),
    ("५", "सहसचिव (Joint Secretary)", "निरंजन वामनराव शास्त्री", "वार्ड न. ३, बोरगाव (खु) पो. धापेवाडा, ता. कळमेश्वर, जी. नागपूर-४४१५०१", "९१११५५४३८८"),
    ("६", "कोषाध्यक्ष (Treasurer)", "साहेबराव मुरलीधर करडभाजणे", "टाईप-एफ/३६/१२, छिंदवाडा रोड, के.टी.पी.एस. कोराडी कॉलोनी, नागपूर-४४११११", "९७३०७७९१४०"),
    ("७", "कार्यकारी सदस्य (Executive Member)", "चिंतामण अंकुशराव पारसकर", "वार्ड न.१, वरोडा रोड, वेलजवळ, सावळी(बु), सहुळी, नागपूर-४४१५०१", "९२७१८२२१८६"),
    ("८", "कार्यकारी सदस्य (Executive Member)", "विनोद मधुकरराव मते", "३८, नव जीवन कॉलोनी, ब्राम्हणी, कळमेश्वर-४४१५०१", "९५९५७४२९९९"),
    ("९", "कार्यकारी सदस्य (Executive Member)", "आशिष भुजंगराव डेहणकर", "वार्ड न. ०२, लोणारा, पो-उपरवाही, त-कळमेश्वर-४४१५०१", "९८२३३५५०६९"),
    ("१०", "कार्यकारी सदस्य (Executive Member)", "चिंतामण विठ्ठलराव रोहणकर", "वार्ड न.०१, धापेवाडा बक, त-कळमेश्वर-४४१५०१", "९७६५७७१९६५"),
    ("११", "कार्यकारी सदस्य (Executive Member)", "अभिजित प्रकाश गजभिये", "प्लॉट न. ७८, जय दुर्गा सोसायटी, गायत्री नगर, बाबा फरीद नगरजवळ, जिंगाबाई टाकळी मानकापूर-४४००३०", "८६००९७३३३३"),
    ("१२", "कार्यकारी सदस्य (Executive Member)", "नरेश सुरेशराव तायवाडे", "वार्ड न. ०३, खैरी (हर्जी), पो-उपरवाही, त-कळमेश्वर-४४१५०१", "८६००३७५४३२"),
    ("१३", "कार्यकारी सदस्य (Executive Member)", "संदीप मुरलीधर देशमुख", "वार्ड न. ०२, तेलकामठी, नागपूर-४४११०७", "७७७५८०२५८८"),
    ("१४", "कार्यकारी सदस्य (Executive Member)", "सुरेश श्रीक्रीष्णाजी बोधाने", "वार्ड न.०१, वाढोणा बक, धापेवाडा, त-कळमेश्वर-४४१५०१", "९७६३३९०६६९"),
    ("१५", "कार्यकारी सदस्य (Executive Member)", "सुभाष अजाबराव ठाकरे", "मु- बोरगाव(धुरखेडा), पोस्ट-धापेवाडा, बोरगाव(बु), त-कळमेश्वर-४४१५०१", "८००७७२७३१२"),
    ("१६", "कार्यकारी सदस्य (Executive Member)", "राजेश माधवराव पायतोडे", "प्लॉट. न. १३, मेन रोड, ओम साई इंटरप्राईजेसजवळ, गीता नगर, जिंगाबाई टाकळी मानकापूर-४४००३०", "९८२३६१८३७९"),
    ("१७", "कार्यकारी सदस्य (Executive Member)", "रुपेश लक्ष्मन निवल", "वार्ड न. ०३, भडागी, धापेवाडा-४४१५०१", "८८३०३५९१०२"),
]

st.set_page_config(
    page_title="बळीराजा शेतकरी संघटना",
    page_icon=str(LOGO),
    layout="wide"
)

st.markdown(
    '''
    <style>
    .stButton>button {
        min-height:44px;
        font-weight:600;
        width:100%;
    }
    .block-container {
        padding-top:1rem;
    }
    .app-table-wrap {width:100%;max-height:650px;overflow:auto;border:1px solid #cbd8cc;border-radius:8px;background:#fff}
    .app-data-table {width:100%;min-width:760px;border-collapse:separate;border-spacing:0;table-layout:auto;color:#243329;font-size:14px}
    .app-data-table th,.app-data-table td {padding:9px 12px;border-bottom:1px solid #d9e3da;text-align:left;vertical-align:top;white-space:normal;overflow-wrap:anywhere}
    .app-data-table thead th {position:sticky;top:0;z-index:2;background:#194d33;color:#fff;font-weight:700;border-bottom:2px solid #bd9637}
    .app-data-table tbody tr:nth-child(odd) {background:#fff}
    .app-data-table tbody tr:nth-child(even) {background:#eaf3e7}
    .app-data-table tbody tr:hover {background:#fff1c9}
    .app-data-table tbody td {color:#243329}
    @media(max-width:700px) {
        .block-container {
            padding-left:.7rem;
            padding-right:.7rem;
        }
    }
    </style>
    ''',
    unsafe_allow_html=True
)

seed_admin()

# Public information pages are available without an employee account. Keep
# this gallery separate from member portraits and other private uploads.
public_view = st.radio(
    "संकेतस्थळ / कर्मचारी विभाग",
    ["🌐 सार्वजनिक संकेतस्थळ", "🔐 Admin Login"],
    horizontal=True,
    key="portal_mode",
)
if public_view == "🌐 सार्वजनिक संकेतस्थळ":
    st.markdown("""<style>
    [data-testid="stAppViewContainer"] {background:linear-gradient(180deg,#edf7ec 0%,#fbfcf7 48%,#f3f8ed 100%)}
    [data-testid="stSidebar"] {display:none}
    [data-testid="stMain"] .block-container {max-width:none;padding:1rem 2.5rem 3rem}
    [data-testid="stHeader"] {background:transparent}
    [data-testid="stMain"], [data-testid="stMain"] * {color:#243329}
    [data-testid="stMain"] h1, [data-testid="stMain"] h2,
    [data-testid="stMain"] h3, [data-testid="stMain"] p,
    [data-testid="stMain"] label, [data-testid="stMain"] [data-testid="stMarkdownContainer"] {color:#243329}
    [data-testid="stMain"] [role="radiogroup"] label {color:#243329 !important}
    [data-testid="stMain"] [role="radio"] {color:#243329 !important}
    [data-testid="stMain"] .stMarkdown, [data-testid="stMain"] .stMarkdown p,
    [data-testid="stMain"] label, [data-testid="stMain"] [data-testid="stAlert"] {font-weight:600}
    [data-testid="stMain"] h1, [data-testid="stMain"] h2,
    [data-testid="stMain"] h3 {font-weight:750}
    [data-testid="stMain"] h2, [data-testid="stMain"] h3 {color:#1b6338 !important}
    [data-testid="stMain"] [role="radiogroup"] label,
    [data-testid="stTabs"] button,
    [data-testid="stTabs"] [role="tab"],
    [data-baseweb="tab"] {font-weight:800 !important}
    [data-testid="stTabs"] button *,
    [data-testid="stTabs"] [role="tab"] *,
    [data-baseweb="tab"] * {font-weight:900 !important}
    [data-testid="stTabs"] [role="tab"],
    [data-baseweb="tab"] {font-size:16px !important}
    [data-testid="stTabs"] button,
    [data-testid="stTabs"] [role="tab"],
    [data-baseweb="tab"] {color:#405449 !important}
    .site-hero {position:relative;isolation:isolate;box-sizing:border-box;min-height:315px;width:100%;display:flex;align-items:center;padding:38px 48px;margin-bottom:16px;background-size:cover;background-position:center 46%;overflow:hidden}
    .site-hero::before {content:"";position:absolute;inset:0;z-index:-1;background:rgba(12,35,21,.56)}
    .site-hero-brand {display:flex;align-items:center;gap:20px;max-width:860px}
    .site-logo {width:82px;height:82px;object-fit:contain;background:#fff;border-radius:50%;padding:7px;flex:0 0 auto}
    .site-hero-copy {max-width:760px;color:#fff}
    .site-hero-copy .site-location {margin:0 0 12px;color:#f0d17a;font-size:14px;font-weight:700}
    .site-hero-copy h1 {margin:0;color:#fff !important;font-size:36px;line-height:1.35;font-weight:900 !important;text-shadow:0 2px 9px rgba(0,0,0,.82);-webkit-text-stroke:.25px #fff}
    .site-hero-copy p {margin:10px 0 0;color:#fff !important;font-size:17px;line-height:1.6;text-shadow:0 1px 5px rgba(0,0,0,.8)}
    .home-intro {padding:22px 0 20px;border-bottom:1px solid #d7e2d7}
    .home-intro .home-kicker {margin:0 0 6px;color:#87641a;font-size:14px;font-weight:700}
    .home-intro h2 {margin:0 0 8px;color:#174d32;font-size:25px;line-height:1.4}
    .home-intro p {max-width:850px;margin:0;color:#3d5144;font-size:16px;line-height:1.8}
    .home-focus {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px;padding:24px 0 28px}
    .home-focus-item {padding-top:12px;border-top:3px solid #bd9637}
    .home-focus-item h3 {margin:0 0 7px;color:#214b31;font-size:18px}
    .home-focus-item p {margin:0;color:#526258;font-size:14px;line-height:1.7}
    .home-office {padding:17px 0 4px;border-top:1px solid #d7e2d7;color:#42564a;font-size:14px;line-height:1.7}
    .home-office strong {color:#174d32}
    .home-office a {color:#1d633b;font-weight:700;text-decoration:underline;text-underline-offset:3px}
    .home-office a:hover {color:#a24631}
    .news-strip {display:flex;align-items:center;overflow:hidden;margin:0 0 8px;background:#174d32;color:#fff;border-left:5px solid #bd9637}
    .news-label {z-index:1;flex:0 0 auto;padding:10px 15px;background:#174d32;color:#f0d17a!important;font-size:14px;font-weight:800;white-space:nowrap}
    .news-window {min-width:0;overflow:hidden}
    .news-track {display:flex;width:max-content;animation:news-scroll 36s linear infinite;white-space:nowrap}
    .news-strip:hover .news-track {animation-play-state:paused}
    .news-item {padding:10px 30px;color:#fff!important;font-size:14px}
    .news-item::before {content:"•";padding-right:12px;color:#f0d17a}
    @keyframes news-scroll {from{transform:translateX(0)}to{transform:translateX(-50%)}}
    [data-testid="stTabs"] button[aria-selected="true"] {color:#176b39 !important;border-bottom-color:#23944e}
    [data-testid="stTabs"] [role="tab"] {padding:.7rem 1rem;border-radius:10px 10px 0 0}
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {background:#e2f2df !important}
    [data-testid="stVerticalBlockBorderWrapper"] {background:linear-gradient(135deg,#ffffff,#f3faf0);border:1px solid #d4e8d2;border-left:6px solid #33834d;border-radius:16px;box-shadow:0 5px 18px rgba(32,89,48,.09);padding:.5rem}
    [data-testid="stAlert"] {border-radius:12px}
    [data-testid="stMain"] .stButton button {background:#287a42;color:white;border:0;border-radius:10px}
    [data-testid="stMain"] .stButton button:hover {background:#195d32;color:white}
    [data-testid="stMain"] [role="radiogroup"] label {background:#e4f1e1;border-radius:10px;padding:.35rem .65rem}
    @media(max-width:700px) {[data-testid="stMain"] .block-container{padding:.7rem}.site-hero{min-height:270px;padding:24px 20px;background-position:67% center}.site-hero-brand{align-items:flex-start;gap:12px}.site-logo{width:58px;height:58px;padding:5px}.site-hero-copy h1{font-size:29px}.site-hero-copy p{font-size:15px}.home-intro h2{font-size:21px}.home-focus{grid-template-columns:1fr;gap:18px;padding:20px 0}.home-focus-item{padding-top:9px}}
    @media(prefers-reduced-motion:reduce){.news-track{animation:none;width:auto;white-space:normal;flex-wrap:wrap}.news-item{white-space:normal}}
    </style>""", unsafe_allow_html=True)
    banner_data = base64.b64encode((BASE / "assets" / "maharashtra-farming-banner.png").read_bytes()).decode("ascii")
    logo_data = base64.b64encode(LOGO.read_bytes()).decode("ascii")
    st.markdown(
        f"<section class='site-hero' style='background-image:url(data:image/png;base64,{banner_data})'>"
        f"<div class='site-hero-brand'><img class='site-logo' src='data:image/jpeg;base64,{logo_data}' alt='बळीराजा शेतकरी संघटनेचा लोगो'>"
        "<div class='site-hero-copy'><p class='site-location'>नागपूर जिल्हा · महाराष्ट्र</p>"
        "<h1 style='color:#fff!important;font-weight:900!important;text-shadow:0 2px 9px rgba(0,0,0,.9)'>बळीराजा शेतकरी संघटना</h1>"
        "<p>शेतकऱ्यांच्या हक्कांसाठी संघटित व्यासपीठ</p></div></div></section>",
        unsafe_allow_html=True,
    )
    tabs = st.tabs(
        ["मुखपृष्ठ", "आमच्याबद्दल", "कार्यकारी मंडळ", "कार्यक्रम", "छायाचित्र दालन", "व्हिडिओ दालन", "संपर्क", "संस्थेचे नियम"],
        on_change="rerun",
        key="public_website_tabs",
    )
    with tabs[0]:
        st.markdown("""
        <section class="news-strip" aria-label="नवीन घडामोडी">
          <div class="news-label">नवीन घडामोडी</div>
          <div class="news-window"><div class="news-track">
            <span class="news-item">०५ ऑक्टोबर २०२६, सकाळी ११:३० वाजता — सावनेर येथे मा. उपविभागीय अधिकारी तथा भूसंपादन अधिकारी यांना बाह्य रिंग रोड भूसंपादन व न्याय्य मोबदल्याबाबत निवेदन.</span>
            <span class="news-item">नागपूर बाह्य रिंग रोड भूसंपादनासाठी योग्य मोबदला, पुनर्वसन आणि पारदर्शक मोजणीची संघटनेची मागणी.</span>
            <span class="news-item" aria-hidden="true">०५ ऑक्टोबर २०२६, सकाळी ११:३० वाजता — सावनेर येथे मा. उपविभागीय अधिकारी तथा भूसंपादन अधिकारी यांना बाह्य रिंग रोड भूसंपादन व न्याय्य मोबदल्याबाबत निवेदन.</span>
            <span class="news-item" aria-hidden="true">नागपूर बाह्य रिंग रोड भूसंपादनासाठी योग्य मोबदला, पुनर्वसन आणि पारदर्शक मोजणीची संघटनेची मागणी.</span>
          </div></div>
        </section>
        """, unsafe_allow_html=True)
        st.markdown("""
        <section class="home-intro">
          <p class="home-kicker">शेतकऱ्यांसोबत, शेतकऱ्यांसाठी</p>
          <h2>शेतकरी हितासाठी एकत्रित प्रयत्न</h2>
          <p>बळीराजा शेतकरी संघटना शेतकऱ्यांच्या प्रश्नांवर संवाद, मार्गदर्शन आणि सामूहिक पाठपुरावा करण्यासाठी कार्यरत आहे. संघटनेची माहिती, कार्यकारी मंडळ आणि उपक्रम येथे पाहा.</p>
        </section>
        <section class="home-focus">
          <div class="home-focus-item"><h3>शेतकरी हक्क</h3><p>भूसंपादन, योग्य मोबदला आणि शेतकऱ्यांच्या हक्कांबाबत एकत्रित आवाज.</p></div>
          <div class="home-focus-item"><h3>मार्गदर्शन</h3><p>अर्ज, कागदपत्रे आणि प्रशासकीय प्रक्रियांसाठी माहिती व सहकार्य.</p></div>
          <div class="home-focus-item"><h3>संघटन</h3><p>स्थानिक प्रश्नांवर शेतकरी बांधवांशी संवाद आणि सामूहिक प्रयत्न.</p></div>
        </section>
        <section class="home-office"><strong>मुख्य कार्यालय</strong><br>शॉप न.२१, कृषी उत्पन्न बाजार समिती संकुल, कळमेश्वर, जी. नागपूर-५५१५०१<br><a href="tel:77749122320">संपर्क: ७७७४९१२२३२०</a> &nbsp; · &nbsp; <a href="https://www.youtube.com/@BalirajaShetkariSanghatana" target="_blank" rel="noopener noreferrer">YouTube चॅनेल पहा</a></section>
        """, unsafe_allow_html=True)
        st.info("कार्यक्रमांच्या तारखा आणि तपशील आयोजकांकडून निश्चित झाल्यानंतर येथे प्रसिद्ध केले जातील.")
    with tabs[1]:
        st.subheader("संघटनेबद्दल")
        st.write("बळीराजा शेतकरी संघटना ही शेतकरी बांधवांच्या प्रश्नांवर संवाद साधण्यासाठी आणि त्यांच्या हितासाठी एकत्र काम करण्यासाठीचे व्यासपीठ आहे.")
        st.write("संघटनेच्या उद्दिष्टांबद्दल, सदस्यत्वाबद्दल किंवा स्थानिक उपक्रमांबद्दल अधिक माहितीसाठी मुख्य कार्यालयाशी संपर्क साधा.")
    with tabs[2]:
        st.subheader("कार्यकारी मंडळ")
        president = EXECUTIVE_BODY[0]
        vice_presidents = EXECUTIVE_BODY[1:3]
        office_bearers = EXECUTIVE_BODY[3:6]
        executive_members = EXECUTIVE_BODY[6:]

        def org_node(person, extra_class="", portrait=None):
            _, designation, member_name, _, _ = person
            photo_html = "<span aria-hidden='true'>📷</span>"
            if portrait and portrait.exists():
                photo_data = base64.b64encode(portrait.read_bytes()).decode("ascii")
                photo_html = f"<img src='data:image/jpeg;base64,{photo_data}' alt='{html.escape(member_name)}'>"
            return (
                f"<div class='org-node {extra_class}'><div class='org-photo'>{photo_html}</div>"
                f"<div class='org-card'><strong>{html.escape(designation)}</strong><b>{html.escape(member_name)}</b></div></div>"
            )

        org_html = """<style>
        .org-chart{padding:26px 16px 38px;overflow-x:auto;background:linear-gradient(180deg,#f4fbf1,#fff);border-radius:20px}
        .org-tier{position:relative;display:flex;justify-content:center;align-items:flex-start;gap:32px;margin:0 auto 52px;width:max-content;min-width:100%}
        .org-tier:not(.tier-top)::before{content:'';position:absolute;top:-27px;left:8%;right:8%;border-top:3px solid #6aa878}
        .org-tier:not(.tier-top) .org-node::before{content:'';position:absolute;left:50%;top:-27px;height:27px;border-left:3px solid #6aa878}
        .org-node{position:relative;width:230px;display:flex;flex-direction:column;align-items:center}
        .org-photo{z-index:1;width:128px;height:128px;border-radius:50%;display:flex;justify-content:center;align-items:center;background:#e4f2df;border:4px solid #fff;box-shadow:0 2px 10px #194a3033;color:#27683b;font-size:28px;margin-bottom:-10px;overflow:hidden}
        .org-photo img{width:100%;height:100%;object-fit:cover;object-position:center 28%;border-radius:50%}
        .org-card{box-sizing:border-box;width:100%;height:132px;padding:14px 12px;border-radius:8px;background:#267343;color:#fff;text-align:center;box-shadow:0 5px 14px #16452c2b;display:flex;flex-direction:column;justify-content:center;gap:6px;overflow-wrap:anywhere}
        .org-card strong{font-size:16px;color:#fff}.org-card b{font-size:19px;color:#fff}
        .tier-top .org-photo{width:148px;height:148px}.tier-top .org-card{background:#155c35}
        .tier-vice .org-card{background:#d7a62d;color:#263820}.tier-vice .org-card strong,.tier-vice .org-card b{color:#263820}
        .tier-officers .org-card{background:#419357}.tier-members{display:grid;grid-template-columns:repeat(4,230px);width:max-content}
        .tier-members .org-card{background:#244c3b}.tier-members .org-photo{width:106px;height:106px}
        @media(max-width:700px){.org-tier{gap:18px}.org-node{width:210px}.org-card{height:132px}.org-photo{width:112px;height:112px}.tier-members{grid-template-columns:repeat(2,210px)}.tier-members .org-photo{width:96px;height:96px}.tier-top .org-photo{width:132px;height:132px}}
        </style><div class='org-chart'>"""
        org_html += f"<div class='org-tier tier-top'>{org_node(president, portrait=BASE / 'assets' / 'pankaj-ghonge.jpg')}</div>"
        vice_president_portraits = {"२": BASE / "assets" / "naresh-raut.jpg"}
        org_html += "<div class='org-tier tier-vice'>" + "".join(
            org_node(p, "vice", vice_president_portraits.get(p[0]))
            for p in vice_presidents
        ) + "</div>"
        officer_portraits = {
            "४": BASE / "assets" / "pravin-gotamare.jpg",
            "६": BASE / "assets" / "sahebrao-karadbhajne.jpg",
        }
        org_html += "<div class='org-tier tier-officers'>" + "".join(
            org_node(p, "officer", officer_portraits.get(p[0]))
            for p in office_bearers
        ) + "</div>"
        org_html += "<div class='org-tier tier-members'>" + "".join(org_node(p, "member") for p in executive_members) + "</div></div>"
        st.markdown(org_html, unsafe_allow_html=True)
        st.subheader("कार्यकारी मंडळाची संपर्क यादी")
        executive_contacts = pd.DataFrame(
            [[designation, member_name, address, mobile]
             for _, designation, member_name, address, mobile in EXECUTIVE_BODY],
            columns=["पद", "नाव", "पत्ता", "मोबाईल"]
        )
        show_table(executive_contacts, use_container_width=True, hide_index=True)
    with tabs[3]:
        st.subheader("सभा व संघटनेचे ठराव")
        st.markdown("### सभा क्रमांक ०४ — ०८ जुलै २०२६")
        st.markdown("**बळीराजा शेतकरी संघटना, कळमेश्वर तालुका**  \n**आवाहन:** तालुक्यातील नवीन आउटर रिंग रोड बाधित सर्व शेतकऱ्यांसाठी  \n**ठिकाण:** स्व. बाबासाहेब केदार हॉल, संत्रा मंडी, कळमेश्वर  \n**वेळ:** दुपारी १.०० वाजता (१ pm)")
        st.info("नवीन आउटर रिंग रोड-३ बाधित सर्व शेतकऱ्यांनी सभेला आवर्जून उपस्थित राहावे. सभा वेळेवर सुरू होईल.")
        with st.expander("सभेतील विषय", expanded=True):
            st.markdown("""
            1. सरकारविरोधात लढा देण्यासाठी सर्व शेतकरी तयार आहेत का, यावर चर्चा.
            2. जमीन शेतकऱ्यांची असल्याने जमिनीचा दर शेतकऱ्यांनी ठरवलेल्या भावानेच सरकारने द्यावा, या मागणीवर सर्वांची मते जाणून घेणे.
            3. याआधी झालेल्या तीन सभांची माहिती देणे.
            4. पुढील कृतीची रूपरेषा ठरवणे.
            5. सरकारला योग्य किंमत देण्यासाठी भाग पाडण्याबाबत चर्चा.
            6. तहसीलदारांना निवेदन देणे.
            7. मागणी मान्य न झाल्यास आंदोलन उभारण्याबाबत शेतकऱ्यांची मते जाणून घेणे.
            8. वेळेवर येणारे इतर विषय.
            """)
        st.markdown("**विशेष विनंती:** सभेला न चुकता उपस्थित राहून आपले म्हणणे सर्वांसमोर मांडा.")
        st.markdown("### गावदौरा कार्यक्रम — २६ ऑगस्ट २०२६")
        st.markdown("**वेळ:** सायंकाळी ४.०० वाजता  \n**गावे:** कन्याडोल, पिंपळा, तेलकामठी आणि मडासावंगी  \n**एकत्र येण्याचे ठिकाण:** बळीराजा शेतकरी संघटनेचे कार्यालय")
        st.info("सर्व पदाधिकाऱ्यांनी वेळेवर संघटनेच्या कार्यालयात उपस्थित राहावे. गावदौऱ्यात सहभागी होऊ इच्छिणाऱ्यांनीही यावे.")
        st.markdown("### निवेदन सादर — ०५ ऑक्टोबर २०२६")
        st.markdown("**वेळ:** सकाळी ११:३० वाजता  \n**ठिकाण:** सावनेर, जि. नागपूर  \n**प्रति:** मा. उपविभागीय अधिकारी तथा भूसंपादन अधिकारी, सावनेर उपविभाग, जि. नागपूर  \n**विषय:** Outer Ring Road / NMRDA प्रकल्पामुळे बाधित सावनेर व कळमेश्वर तालुक्यातील शेतकऱ्यांना न्याय्य मोबदला मिळण्यासाठी निवेदन.")
        st.write("निवेदनात प्रत्यक्ष व नोंदणीकृत बाजारभावाच्या आधारे पारदर्शक मोबदला निश्चित करणे, मोजणीपूर्वी बाधित शेतकऱ्यांशी चर्चा करणे, तसेच शेती, विहीर, बोअरवेल, झाडे, पिके व उर्वरित जमिनीच्या नुकसानीचे योग्य मूल्यांकन करण्याची मागणी आहे.")
        st.markdown("### सभा क्रमांक ०७ — २५ जुलै २०२६")
        st.markdown("**संघटना:** बळीराजा शेतकरी संघटना, कळमेश्वर तालुका  \n**वार:** शनिवार  \n**ठिकाण:** रेणुका माता मंदिर, सावळी, ता. कळमेश्वर")
        st.success("संघटनेची सातवी सभा यशस्वीरित्या संपन्न झाली.")
        with st.expander("सभेतील सारांश व ठराव", expanded=True):
            st.markdown("""
            1. NMRD संदर्भातील लढ्यासाठी संघटना तयार करून तिची नोंदणी करणे.
            2. संघटनेच्या माध्यमातून शेतकऱ्यांचा आवाज सरकारपर्यंत पोहोचवणे.
            3. कळमेश्वर तालुक्यातील रस्त्यामुळे बाधित प्रत्येक शेतकऱ्यासाठी प्रत्येकी एक कोटी रुपयांच्या पाचपट मोबदल्याची मागणी करणे.
            4. प्रत्येक गावातून दोन ते तीन सक्रिय सदस्यांची गाव प्रतिनिधी म्हणून नियुक्ती करणे.
            5. शेतकऱ्यांना योग्य मोबदला देण्यासाठी सरकारकडे पाठपुरावा करणे.
            6. तहसीलदारांना निवेदन देणे.
            """)
        st.caption("सभा आयोजित करण्यासाठी हॉल उपलब्ध करून दिल्याबद्दल अनिरुद्धजी जोशी यांचे विशेष आभार. 🙏")
    with tabs[4]:
        st.subheader("छायाचित्र दालन")
        gallery_images = sorted(p for p in PUBLIC_GALLERY.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
        gallery_captions = {
            "IMG_20260909_204629.jpg.jpeg": "उबाळी येथे शेतकऱ्यांशी चर्चा सत्र",
            "ChatGPT Image Sep 10, 2026, 08_58_53 AM.png": "बळीराजा शेतकरी संघटनेचे YouTube चॅनेल — नवीन व्हिडिओंसाठी सदस्यता घ्या",
            "07-kalameshwar-meeting-2026-07-25.jpeg": "सभा क्रमांक ०७ — २५ जुलै २०२६, रेणुका माता मंदिर, सावळी, कळमेश्वर",
            "01-lonara-panchayat-submission.jpg": "लोणारा ग्रामपंचायतीसमोर निवेदन सादर",
            "02-farmer-delegation-meeting.jpg": "शेतकरी संघटनेची सभा",
            "03-farmer-public-meeting.jpg": "शेतकरी बांधवांची बैठक",
            "04-lonara-farmer-meeting.jpg": "शेतकरी प्रतिनिधींची बैठक, लोणारा",
            "05-organization-gathering.jpg": "संघटनेचे सामूहिक छायाचित्र",
            "06-farmer-address.jpg": "शेतकऱ्यांशी संवाद",
        }
        if gallery_images:
            gallery_cols = st.columns(3)
            for i, image in enumerate(gallery_images):
                gallery_cols[i % 3].image(
                    str(image), caption=gallery_captions.get(image.name, image.stem),
                    use_container_width=True
                )
        else:
            st.caption("कार्यक्रमांची छायाचित्रे लवकरच येथे जोडली जातील.")
    with tabs[5]:
        st.subheader("व्हिडिओ दालन")
        video_files = sorted(
            p for p in PUBLIC_VIDEOS.iterdir()
            if p.suffix.lower() in {".mp4", ".webm", ".mov", ".m4v"}
        )
        if video_files and tabs[5].open:
            for video in video_files:
                st.markdown(f"#### {html.escape(video.stem.replace('-', ' ').replace('_', ' '))}")
                if video.stat().st_size > MAX_PUBLIC_VIDEO_BYTES:
                    st.warning("हा व्हिडिओ फाइल आकाराने मोठा असल्यामुळे येथे प्ले करता येत नाही. कृपया लहान किंवा कमी आकाराची आवृत्ती अपलोड करा.")
                else:
                    st.video(str(video))
        elif not video_files:
            st.info("व्हिडिओ लवकरच येथे जोडले जातील.")
        st.markdown("[संघटनेचे YouTube चॅनेल पहा](https://www.youtube.com/@BalirajaShetkariSanghatana)")
    with tabs[6]:
        st.subheader("मुख्य कार्यालय")
        st.write("शॉप न.२१, कृषी उत्पन्न बाजार समिती संकुल, कळमेश्वर,जी. नागपूर-५५१५०१")
        st.markdown("फोन / WhatsApp: [७७७४९१२२३२०](tel:77749122320)")
        st.write("कार्यालयीन वेळ व ईमेलसाठी कृपया प्रत्यक्ष कार्यालयाशी संपर्क साधा.")
    with tabs[7]:
        st.subheader("संस्थेचे नियम व नियमपुस्तिका")
        st.markdown("**Memorandum of Association — संस्थेचे ज्ञापन पत्र**")
        st.markdown("**१. संस्थेचे नाव:** बळीराजा शेतकरी संघटना")
        st.markdown("**२. मध्यवर्ती कार्यालय:** शॉप न. २१, कृषी उत्पन्न बाजार समिती कॉम्प्लेक्स, ता. कळमेश्वर, जी. नागपूर, महाराष्ट्र-४४१५०१")
        st.markdown("**३. संस्थेचे कार्यक्षेत्र:** संपूर्ण नागपूर जिल्हा आणि परिसर.")
        with st.expander("४. संस्थेचे मुख्य उद्देश (Aims and Objects)", expanded=True):
            st.markdown("""
            - **न्याय्य भूसंपादन मोबदला:** नागपूर ३ऱ्या बाह्य रिंग रोड (3rd Outer Ring Road) प्रकल्प तसेच विविध शासकीय भूसंपादन प्रकल्पांमधील बाधित शेतकऱ्यांना संघटित करून त्यांच्या जमिनींना योग्य, न्याय्य व कमाल बाजारभाव मिळवून देण्यासाठी कायदेशीर व सनदशीर मार्गाने प्रयत्न करणे.
            - **शेतकरी संघटन:** जिल्ह्यातील व राज्यातील शेतकरी बांधवांना संघटित करून त्यांच्या कायदेशीर हक्कांचे व न्याय्य हितसंबंधांचे रक्षण करणे.
            - **कायदेशीर मार्गदर्शन व प्रेरणा:** जमीन अधिग्रहण प्रकरणांमध्ये बाधित शेतकऱ्यांना कायदेशीर मार्गदर्शन, तांत्रिक सहाय्य आणि मानसिक व कायदेशीर बळ मिळवून देणे.
            - **समस्या निवारण व सनदशीर लढा:** शेतकऱ्यांच्या समस्यांसाठी संबंधित शासकीय व निमशासकीय कार्यालये आणि तहसील कार्यालयांकडे निवेदने देणे; शांततापूर्ण आंदोलने, मोर्चे व सनदशीर लढा आयोजित करणे.
            - **शाश्वत शेती विकास:** शेतीचा विकास, आधुनिक तंत्रज्ञानाचा प्रसार आणि शाश्वत शेती पद्धतींबाबत जनजागृती करणे.
            - **संस्थापक सदस्य व कार्यकारी समिती (Governing Body):** संस्थेचे कामकाज व दैनंदिन व्यवहार चालवण्यासाठी पंचवीस संस्थापक सदस्य जबाबदार राहतील. कार्यकारी मंडळाची माहिती “कार्यकारी मंडळ” विभागात दिली आहे.
            """)
        st.markdown("*आम्ही खाली स्वाक्षरी करणारे सर्व सदस्य, या ज्ञापन पत्रात नमूद केलेल्या समाजोपयोगी व शेतकरी हिताच्या उद्देशांसाठी संस्था नोंदणी अधिनियम, १८६० अंतर्गत एकत्र येऊन ही संघटना स्थापन केल्याचे जाहीर करतो.*")
        st.divider()
        st.markdown("**संस्थेचे नियम व नियमावली (Rules & Regulations)**")
        st.markdown("**संस्थेचे नाव:** बळीराजा शेतकरी संघटना  \n**मुख्य कार्यालय:** २१, कृषी उत्पन्न बाजार समिती कॉम्प्लेक्स, मु. पो. कळमेश्वर, जी. नागपूर, महाराष्ट्र-४४१५०१")
        with st.expander("१. व्याख्या (Definitions)"):
            st.markdown("- **संस्था:** बळीराजा शेतकरी संघटना.\n- **समिती:** संस्थेची कार्यकारी समिती (Executive Committee).\n- **वर्ष:** आर्थिक वर्ष (१ एप्रिल ते ३१ मार्च).")
        with st.expander("२. सदस्यत्व (Membership)"):
            st.markdown("- **पात्रता:** १८ वर्षे पूर्ण असलेली कोणतीही भारतीय व्यक्ती, जी संस्थेच्या शेतकरी कल्याण व न्याय्य हक्कांच्या उद्दिष्टांशी सहमत आहे.\n- **प्रवेश फी:** ₹२५०/- (एकदाच).\n- **वार्षिक वर्गणी:** ₹५००/- प्रतिवर्ष.\n- **सदस्यत्वाचे प्रकार:** संस्थापक सदस्य, आजीवन सदस्य आणि साधारण सदस्य.")
        with st.expander("३. सदस्यत्व रद्द होणे (Cessation of Membership)"):
            st.markdown("- सदस्याचा लेखी राजीनामा.\n- सलग २ वर्षे वार्षिक वर्गणी न भरणे.\n- संस्थेच्या हिताविरोधी कृत्य किंवा शिस्तभंग सिद्ध झाल्यास (कार्यकारी समितीच्या २/३ बहुमताने).\n- सदस्याचा मृत्यू.")
        with st.expander("४. सर्वसाधारण सभा (General Body Meeting)"):
            st.markdown("- **वार्षिक सभा:** आर्थिक वर्ष संपल्यानंतर ६ महिन्यांच्या आत.\n- **सूचना:** किमान १५ दिवस आधी लेखी किंवा डिजिटल माध्यमातून.\n- **कोरम:** एकूण सदस्यसंख्येच्या ३/५ सदस्यांची उपस्थिती. कोरम अभावी सभा स्थगित झाल्यास त्याच दिवशी १ तासानंतर त्याच ठिकाणी सभा घेता येईल; त्या सभेस कोरमची अट नसेल.")
        with st.expander("५. कार्यकारी समिती (Executive Committee)"):
            st.markdown("- **रचना:** दैनंदिन कारभारासाठी किमान ७ आणि कमाल १९ सदस्यांची कार्यकारी समिती.\n- **पदाधिकारी:** अध्यक्ष (१), उपाध्यक्ष (२), सचिव (१), सहसचिव (२), कोषाध्यक्ष (१) आणि कार्यकारी सदस्य (१२).\n- **कार्यकाळ:** ३ वर्षे.")
        with st.expander("६. अधिकाऱ्यांचे अधिकार व कर्तव्ये (Powers & Duties)"):
            st.markdown("- **अध्यक्ष:** सभांचे अध्यक्षस्थान भूषवणे, कामकाजावर नियंत्रण ठेवणे आणि समान मते पडल्यास निर्णायक मत देणे.\n- **उपाध्यक्ष:** अध्यक्षांच्या अनुपस्थितीत त्यांची कर्तव्ये पार पाडणे.\n- **सचिव:** सभेचे इतिवृत्त लिहिणे, पत्रव्यवहार सांभाळणे आणि अधिकृत दस्तऐवज सुरक्षित ठेवणे.\n- **कोषाध्यक्ष:** हिशोब ठेवणे, बँक व्यवहार पाहणे आणि वार्षिक आर्थिक ताळेबंद (Audit Report) सभेत सादर करणे.")
        with st.expander("७. संस्थेचे बँक खाते (Bank Account Operation)"):
            st.markdown("- संस्थेच्या नावाने राष्ट्रीयीकृत किंवा शेड्युल्ड बँकेत खाते उघडले जाईल.\n- खाते अध्यक्ष किंवा सचिव यांपैकी एक आणि कोषाध्यक्ष यांच्या संयुक्त स्वाक्षरीने चालवले जाईल.")
        with st.expander("८. नियमावलीत दुरुस्ती व विसर्जन (Amendments & Dissolution)"):
            st.markdown("- **दुरुस्ती:** उपस्थित सदस्यांच्या २/३ बहुमताने सर्वसाधारण सभेत ठराव मंजूर करणे आवश्यक.\n- **विसर्जन:** संस्था नोंदणी अधिनियम, १८६० च्या कलम १३ व १४ नुसार विशेष सभेत ३/५ बहुमताने ठराव मंजूर करून संस्था विसर्जित करता येईल.")
    st.caption("बळीराजा शेतकरी संघटना")
    st.stop()

# Additional ledger for income and expenditure not already recorded as
# member payments. Kept separate so membership receipts are never counted twice.
execute('''CREATE TABLE IF NOT EXISTS cash_book_entries(
    id INT AUTO_INCREMENT PRIMARY KEY,
    entry_type ENUM('Income','Expenditure') NOT NULL,
    category VARCHAR(120) NOT NULL,
    description TEXT,
    amount DECIMAL(12,2) NOT NULL,
    entry_date DATE NOT NULL,
    payment_method ENUM('Cash','UPI','Bank') NOT NULL DEFAULT 'Cash',
    created_by INT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(created_by) REFERENCES users(id)
)''')
payment_type_column = query('''SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='payments' AND COLUMN_NAME='payment_type' ''')
if payment_type_column and "Other Contribution" not in payment_type_column[0]["COLUMN_TYPE"]:
    execute("ALTER TABLE payments MODIFY payment_type ENUM('Membership Fee','Other Contribution','Donation') NOT NULL")
for table_name in ("members", "payments"):
    date_column = query('''SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s''',
        (table_name, "registration_date" if table_name == "members" else "payment_date"))
    if date_column and date_column[0]["IS_NULLABLE"] == "NO":
        date_field = "registration_date" if table_name == "members" else "payment_date"
        execute(f"ALTER TABLE {table_name} MODIFY {date_field} DATE NULL")

whatsapp_opt_in_column = query('''SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='members' AND COLUMN_NAME='whatsapp_opt_in' ''')
if not whatsapp_opt_in_column:
    execute("ALTER TABLE members ADD COLUMN whatsapp_opt_in TINYINT(1) NOT NULL DEFAULT 0")
execute('''CREATE TABLE IF NOT EXISTS whatsapp_message_logs(
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    batch_id CHAR(36) NOT NULL,
    member_id INT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    status ENUM('accepted','failed') NOT NULL,
    provider_message_id VARCHAR(255),
    error_text TEXT,
    sent_by INT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_whatsapp_batch(batch_id),
    FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE SET NULL,
    FOREIGN KEY(sent_by) REFERENCES users(id) ON DELETE SET NULL
)''')

if not login():
    st.stop()

user = st.session_state.user

st.sidebar.image(str(LOGO), use_container_width=True)
st.sidebar.title("बळीराजा")
st.sidebar.caption("शॉप न.२१, कृषी उत्पन्न बाजार समिती संकुल, कळमेश्वर,जी. नागपूर-५५१५०१")
st.sidebar.caption(
    f"{user['full_name']} — {user['role']}"
)

menu = [
    "🏠 Dashboard",
    "👨‍🌾 Members",
    "💰 Payments",
    "🧾 Receipts",
    "📒 Cash Book",
    "📌 बाकी वर्गणी",
    "📊 Reports",
    "📲 WhatsApp संदेश",
    "📷 Gallery",
    "🏘️ Masters",
    "⚙️ Admin"
]
if not is_admin():
    menu.remove("📲 WhatsApp संदेश")

page = st.sidebar.radio("Menu", menu)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

def next_number(prefix, table, column):
    year = datetime.date.today().year
    row = query(
        f"SELECT {column} AS last_no FROM {table} "
        "ORDER BY id DESC LIMIT 1"
    )

    number = 1

    if row and row[0]["last_no"]:
        try:
            number = int(
                str(row[0]["last_no"]).split("-")[-1]
            ) + 1
        except Exception:
            number = 1

    return f"{prefix}-{year}-{number:05d}"

# ---------------- Dashboard ----------------
if page == "🏠 Dashboard":
    st.markdown("""
    <style>
    [data-testid="stMain"]:has(.dashboard-hero) .block-container{padding-top:1.35rem;max-width:1440px}
    [data-testid="stMain"]:has(.dashboard-hero) [data-testid="stMetric"]{background:#fff;border:1px solid #e2e9e2;border-top:3px solid #43815a;border-radius:8px;padding:15px 17px;min-height:105px;box-shadow:0 2px 8px rgba(26,55,35,.045)}
    [data-testid="stMain"]:has(.dashboard-hero) [data-testid="stMetricLabel"]{color:#53645a;font-size:.88rem;font-weight:600}
    [data-testid="stMain"]:has(.dashboard-hero) [data-testid="stMetricValue"]{color:#183e2a;font-size:1.55rem;font-weight:700}
    [data-testid="stMain"]:has(.dashboard-hero) [data-testid="stDataFrame"]{border:1px solid #e1e8e1;border-radius:8px;overflow:hidden}
    .dashboard-hero{display:flex;align-items:center;gap:20px;padding:21px 25px;margin:0 0 22px;background:#174d32;border-radius:8px;color:#fff}
    .dashboard-hero img{width:74px;height:74px;object-fit:contain;background:#fff;border-radius:6px;padding:5px;flex:0 0 auto}
    .dashboard-hero h1{font-size:1.6rem;line-height:1.3;margin:0;color:#fff;font-weight:700}
    .dashboard-hero p{margin:5px 0 0;color:#e1eee4;font-size:.95rem}
    .dashboard-hero .dashboard-meta{margin-left:auto;text-align:right;color:#d8e8dc;font-size:.85rem;line-height:1.7}
    [data-testid="stMain"]:has(.dashboard-hero) h2{font-size:1.08rem;color:#203b2b;margin:1.25rem 0 .7rem}
    @media(max-width:700px){.dashboard-hero{padding:15px;gap:12px;align-items:flex-start}.dashboard-hero img{width:52px;height:52px}.dashboard-hero h1{font-size:1.2rem}.dashboard-hero .dashboard-meta{font-size:.75rem}}
    </style>
    """, unsafe_allow_html=True)

    logo_data = base64.b64encode(LOGO.read_bytes()).decode("ascii")
    st.markdown(
        f"<section class='dashboard-hero'><img src='data:image/jpeg;base64,{logo_data}' alt=''>"
        f"<div><h1>बळीराजा शेतकरी संघटना</h1><p>कर्मचारी डॅशबोर्ड</p></div>"
        f"<div class='dashboard-meta'>{html.escape(user['full_name'])}<br>{datetime.date.today().strftime('%d-%m-%Y')}</div></section>",
        unsafe_allow_html=True,
    )

    members = query("SELECT COUNT(*) AS n FROM members WHERE active=1")[0]["n"]
    payment_totals = query('''SELECT
        COALESCE(SUM(CASE WHEN payment_type='Membership Fee' THEN amount ELSE 0 END),0) AS fee,
        COALESCE(SUM(CASE WHEN payment_type='Other Contribution' THEN amount ELSE 0 END),0) AS contribution,
        COALESCE(SUM(CASE WHEN payment_type='Donation' THEN amount ELSE 0 END),0) AS donation
        FROM payments''')[0]
    book_totals = query('''SELECT
        COALESCE(SUM(CASE WHEN entry_type='Income' THEN amount ELSE 0 END),0) AS income,
        COALESCE(SUM(CASE WHEN entry_type='Expenditure' THEN amount ELSE 0 END),0) AS expenditure
        FROM cash_book_entries''')[0]

    fee = float(payment_totals["fee"] or 0)
    contribution = float(payment_totals["contribution"] or 0)
    donation = float(payment_totals["donation"] or 0)
    receipts = fee + contribution + donation
    total_income = receipts + float(book_totals["income"] or 0)
    expenses = float(book_totals["expenditure"] or 0)
    balance = total_income - expenses

    st.subheader("संस्थेची सद्यस्थिती")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("सक्रिय सभासद", f"{int(members):,}")
    k2.metric("एकूण जमा", f"₹ {total_income:,.2f}")
    k3.metric("एकूण खर्च", f"₹ {expenses:,.2f}")
    k4.metric("सध्याची शिल्लक", f"₹ {balance:,.2f}")

    st.subheader("जमा रकमेचा तपशील")
    f1, f2, f3 = st.columns(3)
    f1.metric("सभासद फी", f"₹ {fee:,.2f}")
    f2.metric("इतर वर्गणी", f"₹ {contribution:,.2f}")
    f3.metric("देणगी", f"₹ {donation:,.2f}")

    st.subheader("अलीकडील पेमेंट")
    recent_payments = payments_report().head(8).rename(columns={
        "receipt_no": "पावती क्रमांक", "member_no": "सभासद क्रमांक",
        "name": "सभासदाचे नाव", "mobile": "मोबाईल", "village": "गाव",
        "taluka": "तालुका", "payment_type": "पेमेंट प्रकार", "amount": "रक्कम",
        "payment_method": "भरणा पद्धत", "transaction_no": "व्यवहार क्रमांक",
        "payment_date": "दिनांक", "note": "नोंद",
    })
    show_table(recent_payments, use_container_width=True, hide_index=True)

# ---------------- Members ----------------
elif page == "👨‍🌾 Members":
    st.title("👨‍🌾 सभासद नोंदणी")

    villages = query(
        '''SELECT v.id,v.name AS village,t.name AS taluka
        FROM villages v
        JOIN talukas t ON t.id=v.taluka_id
        WHERE v.active=1
        ORDER BY t.name,v.name'''
    )

    village_labels = ["--"] + [
        f"{v['taluka']} / {v['village']}"
        for v in villages
    ]

    fee_setting = query("SELECT value FROM settings WHERE `key`='membership_fee'")
    suggested_fee = float(fee_setting[0]["value"]) if fee_setting else 0.0

    with st.form("member_form", clear_on_submit=True):
        a,b = st.columns(2)

        name = a.text_input("नाव *")
        mobile = b.text_input("मोबाईल नंबर")

        village_label = a.selectbox(
            "गाव / तालुका", village_labels
        )

        address = b.text_area("पत्ता")

        identity = a.text_input(
            "आधार / ओळख माहिती — आवश्यक असल्यास"
        )

        whatsapp_opt_in = st.checkbox(
            "WhatsApp वर संघटनेचे संदेश मिळण्यास सभासदाची संमती आहे",
            value=False, help="फक्त स्पष्ट संमती नोंदवल्यावरच निवडा. संमती नसल्यास रिकामे ठेवा."
        )

        registration_date_pending = b.checkbox(
            "नोंदणी तारीख नंतर भरा", key="member_registration_date_pending"
        )
        registration_date = b.date_input(
            "नोंदणी तारीख", datetime.date.today(), disabled=registration_date_pending
        )

        photo = a.file_uploader(
            "फोटो",
            type=["jpg","jpeg","png"]
        )

        st.markdown("**नोंदणी पेमेंट तपशील (अनिवार्य)**")
        pay_a, pay_b = st.columns(2)
        registration_payment_type = pay_a.selectbox(
            "पेमेंट प्रकार", ["Membership Fee", "Other Contribution", "Donation"],
            format_func=lambda x: {
                "Membership Fee": "सभासद फी",
                "Other Contribution": "इतर वर्गणी",
                "Donation": "देणगी"
            }[x]
        )
        registration_payment_amount = pay_b.number_input(
            "आलेली रक्कम ₹ *", min_value=0.0, value=suggested_fee,
            step=100.0, help="सभासद फी Admin पॅनेलमधील सेटिंगनुसार सुचवली आहे."
        )
        registration_payment_method = pay_a.selectbox(
            "पेमेंट पद्धत", ["Cash", "UPI", "Bank"],
            format_func=lambda x: {"Cash": "रोख", "UPI": "UPI", "Bank": "बँक"}[x]
        )
        registration_transaction_no = pay_b.text_input("UTR / व्यवहार क्रमांक")
        registration_payment_date = pay_a.date_input("पेमेंट तारीख", datetime.date.today())
        registration_payment_note = pay_b.text_input("पेमेंट नोंद")

        save = st.form_submit_button(
            "💾 सभासद नोंदवा"
        )

    if save:
        if not name.strip():
            st.error("नाव आवश्यक आहे.")
        elif registration_payment_amount <= 0:
            st.error("पेमेंट रक्कम अनिवार्य आहे आणि शून्यापेक्षा जास्त असावी. सभासद नोंदणी झाली नाही.")
        else:
            member_no = next_number(
                "MEM","members","member_no"
            )

            village_id = None

            if village_label != "--":
                index = village_labels.index(
                    village_label
                ) - 1
                village_id = villages[index]["id"]

            photo_path = ""

            if photo:
                filename = (
                    f"{member_no}_{photo.name}"
                )
                target = UPLOADS / filename
                target.write_bytes(photo.getbuffer())
                photo_path = str(target)

            member_id = execute(
                '''INSERT INTO members
                (member_no,name,mobile,village_id,address,
                 identity_info,photo_path,registration_date,whatsapp_opt_in,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (
                    member_no,
                    name.strip(),
                    mobile,
                    village_id,
                    address,
                    identity,
                    photo_path,
                    None if registration_date_pending else str(registration_date),
                    int(whatsapp_opt_in),
                    user["id"]
                )
            )

            receipt_no = next_number("RCT", "payments", "receipt_no")
            execute(
                '''INSERT INTO payments
                (receipt_no,member_id,payment_type,amount,payment_method,
                 transaction_no,payment_date,note,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (receipt_no, member_id, registration_payment_type,
                 registration_payment_amount, registration_payment_method,
                 registration_transaction_no.strip(),
                 str(registration_payment_date),
                 registration_payment_note.strip(), user["id"])
            )

            success_message = f"सभासद नोंदणी यशस्वी — {member_no}"
            success_message += f" | पावती क्रमांक — {receipt_no}"
            st.success(success_message)

    st.subheader("सभासद यादी")

    df = members_report()

    search = st.text_input(
        "🔎 नाव / मोबाईल / गाव शोधा"
    )

    if search and not df.empty:
        mask = df.astype(str).apply(
            lambda col: col.str.contains(
                search,
                case=False,
                na=False
            )
        )
        df = df[mask.any(axis=1)]

    show_table(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("सभासद निवडून संपादन / हटवणे")
    if not is_admin():
        st.info("सभासद माहिती संपादित किंवा निष्क्रिय करण्यासाठी Admin अधिकार आवश्यक आहेत.")
    else:
        editable_members = query('''SELECT id,member_no,name,mobile,village_id,address,
            identity_info,registration_date,active,whatsapp_opt_in FROM members ORDER BY id DESC''')
        if editable_members:
            editable_options = {
                f"{m['member_no']} — {m['name']}" : m for m in editable_members
            }
            chosen_member_label = st.selectbox(
                "संपादित / हटवण्यासाठी सभासद निवडा",
                list(editable_options), key="members_page_selected_member"
            )
            chosen_member = editable_options[chosen_member_label]
            villages_for_edit = query("SELECT id,name FROM villages ORDER BY name")
            edit_village_ids = [None] + [v["id"] for v in villages_for_edit]
            edit_village_names = ["-- गाव निवडा --"] + [v["name"] for v in villages_for_edit]
            selected_village_index = (
                edit_village_ids.index(chosen_member["village_id"])
                if chosen_member["village_id"] in edit_village_ids else 0
            )
            with st.form("members_page_edit_form"):
                edit_col_a, edit_col_b = st.columns(2)
                member_edit_name = edit_col_a.text_input("नाव", chosen_member["name"])
                member_edit_mobile = edit_col_b.text_input("मोबाईल", chosen_member["mobile"] or "")
                member_edit_village = edit_col_a.selectbox(
                    "गाव", edit_village_names, index=selected_village_index
                )
                member_edit_address = edit_col_b.text_area("पत्ता", chosen_member["address"] or "")
                member_edit_identity = edit_col_a.text_input(
                    "आधार / ओळख माहिती", chosen_member["identity_info"] or ""
                )
                member_edit_date_pending = edit_col_b.checkbox(
                    "नोंदणी तारीख नंतर भरा",
                    value=chosen_member["registration_date"] is None,
                    key=f"members_page_reg_date_pending_{chosen_member['id']}"
                )
                member_edit_date = edit_col_b.date_input(
                    "नोंदणी तारीख", chosen_member["registration_date"] or datetime.date.today(),
                    disabled=member_edit_date_pending
                )
                member_edit_active = st.checkbox(
                    "सभासद सक्रिय", value=bool(chosen_member["active"]),
                    key="members_page_active"
                )
                member_edit_whatsapp_opt_in = st.checkbox(
                    "WhatsApp संदेशांसाठी स्पष्ट संमती नोंदलेली आहे",
                    value=bool(chosen_member["whatsapp_opt_in"]),
                    help="सभासदाने संमती दिलेली असल्याची खात्री करूनच निवडा."
                )
                save_member_changes = st.form_submit_button("निवडलेल्या सभासदाची माहिती जतन करा")
            if save_member_changes:
                if not member_edit_name.strip():
                    st.error("नाव आवश्यक आहे.")
                else:
                    edit_village_id = edit_village_ids[edit_village_names.index(member_edit_village)]
                    execute('''UPDATE members SET name=%s,mobile=%s,village_id=%s,address=%s,
                        identity_info=%s,registration_date=%s,active=%s,whatsapp_opt_in=%s WHERE id=%s''',
                        (member_edit_name.strip(), member_edit_mobile.strip(), edit_village_id,
                         member_edit_address.strip(), member_edit_identity.strip(),
                         None if member_edit_date_pending else str(member_edit_date),
                         int(member_edit_active), int(member_edit_whatsapp_opt_in), chosen_member["id"]))
                    st.success("निवडलेल्या सभासदाची माहिती अद्ययावत झाली.")
                    st.rerun()
            confirm_member_deactivate = st.checkbox(
                f"{chosen_member['name']} यांना निष्क्रिय करण्याची खात्री आहे",
                key="members_page_confirm_deactivate"
            )
            if st.button(
                "निवडलेला सभासद निष्क्रिय करा",
                disabled=not confirm_member_deactivate,
                key="members_page_deactivate"
            ):
                execute("UPDATE members SET active=0 WHERE id=%s", (chosen_member["id"],))
                st.success("सभासद निष्क्रिय केला. त्याच्या पावत्या आणि व्यवहार जतन राहतील.")
                st.rerun()
            associated_receipts = query(
                "SELECT COUNT(*) AS n FROM payments WHERE member_id=%s",
                (chosen_member["id"],)
            )[0]["n"]
            st.warning(
                f"कायमचे हटवल्यास या सभासदाच्या {associated_receipts} पावत्या आणि त्यांची जमा नोंदही हटेल."
            )
            confirm_member_delete = st.checkbox(
                "सभासद आणि त्याच्या पावत्या कायमच्या हटवण्याची खात्री आहे",
                key="members_page_confirm_delete"
            )
            if st.button(
                "निवडलेला सभासद कायमचा हटवा",
                disabled=not confirm_member_delete,
                key="members_page_delete"
            ):
                execute("DELETE FROM payments WHERE member_id=%s", (chosen_member["id"],))
                execute("DELETE FROM members WHERE id=%s", (chosen_member["id"],))
                st.success("सभासद आणि त्याच्या पावत्या कायमच्या हटवल्या.")
                st.rerun()
        else:
            st.info("सभासद उपलब्ध नाहीत.")

# ---------------- Payments ----------------
elif page == "💰 Payments":
    st.title("💰 वर्गणी / देणगी")

    members = query(
        '''SELECT id,member_no,name,mobile
        FROM members WHERE active=1
        ORDER BY name'''
    )

    if not members:
        st.warning("प्रथम सभासद नोंदवा.")
        st.stop()

    labels = [
        f"{m['member_no']} — {m['name']} — {m['mobile'] or ''}"
        for m in members
    ]

    with st.form("payment_form", clear_on_submit=True):
        selected = st.selectbox(
            "सभासद",
            labels
        )

        a,b = st.columns(2)

        payment_type = a.selectbox(
            "प्रकार",
            ["Membership Fee", "Other Contribution", "Donation"],
            format_func=lambda x: {
                "Membership Fee": "सभासद फी",
                "Other Contribution": "इतर वर्गणी",
                "Donation": "देणगी"
            }[x]
        )

        amount = b.number_input(
            "रक्कम ₹",
            min_value=1.0,
            step=100.0
        )

        payment_method = a.selectbox(
            "पेमेंट पद्धत",
            ["Cash","UPI","Bank"]
        )

        transaction_no = b.text_input(
            "UTR / व्यवहार क्रमांक"
        )

        payment_date = a.date_input(
            "तारीख",
            datetime.date.today()
        )

        note = b.text_area("नोंद")

        save = st.form_submit_button(
            "🧾 पेमेंट नोंदवा"
        )

    if save:
        member = members[labels.index(selected)]

        receipt_no = next_number(
            "RCT","payments","receipt_no"
        )

        execute(
            '''INSERT INTO payments
            (receipt_no,member_id,payment_type,amount,
             payment_method,transaction_no,payment_date,
             note,created_by)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (
                receipt_no,
                member["id"],
                payment_type,
                amount,
                payment_method,
                transaction_no,
                str(payment_date),
                note,
                user["id"]
            )
        )

        st.success(
            f"पेमेंट नोंदवले — पावती क्रमांक {receipt_no}"
        )

    show_table(
        payments_report().head(100),
        use_container_width=True,
        hide_index=True
    )

# ---------------- Receipts ----------------
elif page == "🧾 Receipts":
    st.title("🧾 पावत्या")

    df = payments_report()

    if df.empty:
        st.info("पावत्या उपलब्ध नाहीत.")
        st.stop()

    receipt_no = st.selectbox(
        "पावती निवडा",
        df["receipt_no"].tolist()
    )

    copies = st.selectbox(
        "Print Format",
        [1,2,3],
        format_func=lambda x: (
            "1 — Single" if x == 1
            else "2 — A4 वर 2 पावत्या"
            if x == 2
            else "3 — A4 वर 3 पावत्या"
        )
    )

    if st.button("📄 PDF तयार करा"):
        row = df[
            df["receipt_no"] == receipt_no
        ].iloc[0].to_dict()

        filename = f"{receipt_no}_{copies}up.pdf"
        path = RECEIPTS / filename

        make_receipt(
            row,
            setting(
                "ORG_NAME",
                "बळीराजा शेतकरी संघटना"
            ),
            path,
            copies
        )

        st.download_button(
            "⬇️ PDF डाउनलोड",
            path.read_bytes(),
            filename,
            "application/pdf"
        )

# ---------------- Cash Book ----------------
elif page == "📒 Cash Book":
    st.title("📒 जमा-खर्च वही")
    st.caption("सभासदांच्या पावत्या जमा म्हणून आपोआप दिसतात. त्यांची पुन्हा स्वतंत्र नोंद करू नका.")

    with st.form("cash_book_form", clear_on_submit=True):
        a, b = st.columns(2)
        entry_type = a.selectbox(
            "नोंदीचा प्रकार", ["Income", "Expenditure"],
            format_func=lambda x: "जमा / उत्पन्न" if x == "Income" else "खर्च"
        )
        category = b.text_input("वर्ग / कारण *")
        description = a.text_area("तपशील")
        cash_amount = b.number_input("रक्कम ₹", min_value=0.01, step=100.0)
        entry_date = a.date_input("तारीख", datetime.date.today())
        entry_method = b.selectbox("पद्धत", ["Cash", "UPI", "Bank"])
        add_entry = st.form_submit_button("नोंद जतन करा")

    if add_entry:
        if not category.strip():
            st.error("वर्ग / कारण भरणे आवश्यक आहे.")
        else:
            execute('''INSERT INTO cash_book_entries
                (entry_type,category,description,amount,entry_date,payment_method,created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s)''',
                (entry_type, category.strip(), description.strip(), cash_amount,
                 str(entry_date), entry_method, user["id"]))
            st.success("नोंद जतन झाली.")
            st.rerun()

    ledger = query('''SELECT p.payment_date AS entry_date, 'Income' AS entry_type,
        p.receipt_no, p.payment_type AS category,
        CONCAT('पावती ',p.receipt_no,' — ',m.name) AS description,
        p.amount, p.payment_method, 'Member Receipt' AS source, p.id AS source_id
        FROM payments p JOIN members m ON m.id=p.member_id
        UNION ALL
        SELECT entry_date,entry_type,NULL AS receipt_no,category,description,amount,payment_method,
        'Cash Book' AS source,id AS source_id FROM cash_book_entries
        ORDER BY entry_date,source,source_id''')
    if ledger:
        running_balance = 0.0
        for row in ledger:
            amount = float(row["amount"] or 0)
            running_balance += amount if row["entry_type"] == "Income" else -amount
            row["running_balance"] = running_balance
        income_total = sum(float(row["amount"]) for row in ledger if row["entry_type"] == "Income")
        expense_total = sum(float(row["amount"]) for row in ledger if row["entry_type"] == "Expenditure")
        fee_total = sum(float(row["amount"]) for row in ledger if row["entry_type"] == "Income" and row["category"] == "Membership Fee")
        contribution_total = sum(float(row["amount"]) for row in ledger if row["entry_type"] == "Income" and row["category"] == "Other Contribution")
        donation_total = sum(float(row["amount"]) for row in ledger if row["entry_type"] == "Income" and row["category"] == "Donation")
        x, y, z = st.columns(3)
        x.metric("सभासद फी जमा", f"₹ {fee_total:,.2f}")
        y.metric("इतर वर्गणी जमा", f"₹ {contribution_total:,.2f}")
        z.metric("देणगी जमा", f"₹ {donation_total:,.2f}")
        p, q, r = st.columns(3)
        p.metric("एकूण जमा", f"₹ {income_total:,.2f}")
        q.metric("एकूण खर्च", f"₹ {expense_total:,.2f}")
        r.metric("अखेरची शिल्लक", f"₹ {running_balance:,.2f}")
        display_ledger = list(reversed(ledger))
        show_table(pd.DataFrame(display_ledger), use_container_width=True, hide_index=True)
        if is_admin():
            cashbook_rows = [[row["entry_date"],
                              "जमा" if row["entry_type"] == "Income" else "खर्च",
                              row["receipt_no"] or "—", row["category"], row["description"],
                              f"₹ {float(row['amount']):,.2f}" if row["entry_type"] == "Income" else "—",
                              f"₹ {float(row['amount']):,.2f}" if row["entry_type"] == "Expenditure" else "—",
                              f"₹ {float(row['running_balance']):,.2f}", row["payment_method"]]
                             for row in ledger]
            st.download_button(
                "प्रिंटसाठी जमा-खर्च वही PDF",
                printable_pdf(
                    f"जमा-खर्चाचा हिशेब | एकूण जमा: ₹ {income_total:,.2f} | एकूण खर्च: ₹ {expense_total:,.2f} | शिल्लक: ₹ {running_balance:,.2f}",
                    ["दिनांक", "व्यवहार", "पावती क्रमांक", "वर्ग / कारण", "तपशील", "जमा रक्कम", "खर्चाची रक्कम", "शिल्लक", "भरणा पद्धत"],
                    cashbook_rows, True, [0.075, 0.07, 0.105, 0.09, 0.19, 0.10, 0.11, 0.11, 0.15]),
                "baliraja_cashbook.pdf", "application/pdf", key="cashbook_print_pdf"
            )
            manual_entries = [row for row in ledger if row["source"] == "Cash Book"]
            if manual_entries:
                selected_entry = st.selectbox("हाताने केलेली नोंद हटवा", manual_entries,
                    format_func=lambda row: f"{row['entry_date']} — {row['category']} — ₹{float(row['amount']):,.2f}")
                confirm_entry_delete = st.checkbox("ही नोंद कायमची हटवण्याची खात्री आहे")
                if st.button("निवडलेली नोंद हटवा", disabled=not confirm_entry_delete):
                    execute("DELETE FROM cash_book_entries WHERE id=%s", (selected_entry["source_id"],))
                    st.success("नोंद हटवली.")
                    st.rerun()
    else:
        st.info("अद्याप जमा किंवा खर्चाची नोंद नाही.")

# ---------------- Dues ----------------
elif page == "📌 बाकी वर्गणी":
    st.title("📌 बाकी वर्गणी रिपोर्ट")

    setting = query(
        "SELECT value FROM settings "
        "WHERE `key`='membership_fee'"
    )

    fee = float(
        setting[0]["value"]
        if setting else 0
    )

    rows = query(
        '''SELECT
        m.member_no,m.name,m.mobile,
        v.name AS village,
        t.name AS taluka,
        COALESCE(SUM(
          CASE WHEN p.payment_type='Membership Fee'
          THEN p.amount ELSE 0 END
        ),0) AS paid
        FROM members m
        LEFT JOIN payments p
          ON p.member_id=m.id
        LEFT JOIN villages v
          ON v.id=m.village_id
        LEFT JOIN talukas t
          ON t.id=v.taluka_id
        WHERE m.active=1
        GROUP BY m.id
        ORDER BY t.name,v.name,m.name'''
    )

    dues = pd.DataFrame(rows)

    if not dues.empty:
        dues["due"] = (
            fee - dues["paid"]
        ).clip(lower=0)

        st.metric(
            "प्रति सभासद Membership Fee",
            f"₹ {fee:,.2f}"
        )

        show_table(
            dues[dues["due"] > 0],
            use_container_width=True,
            hide_index=True
        )

# ---------------- Reports ----------------
elif page == "📊 Reports":
    st.title("📊 पूर्ण Reports")

    members_df = members_report()
    payments_df = payments_report()

    st.subheader("सभासद रिपोर्ट")
    show_table(
        members_df,
        use_container_width=True,
        hide_index=True
    )

    if is_admin():
        include_payments = st.checkbox("सभासदांनी भरलेल्या पेमेंटचा तपशील समाविष्ट करा")
        if include_payments:
            detail_rows = member_payments_report()
            printable_rows = [[r["member_no"], r["name"], r["mobile"] or "", r["village"] or "",
                               r["receipt_no"] or "", r["payment_type"] or "", 
                               f"₹ {float(r['amount'] or 0):,.2f}" if r["amount"] is not None else "",
                               r["payment_method"] or "", str(r["payment_date"] or "")]
                              for r in detail_rows]
            pdf_data = printable_pdf("सभासद यादी व पेमेंट तपशील",
                ["सभासद क्रमांक", "नाव", "मोबाईल", "गाव", "पावती क्रमांक", "पेमेंट प्रकार", "रक्कम", "पद्धत", "तारीख"],
                printable_rows, True)
            filename = "baliraja_members_with_payments.pdf"
        else:
            printable_rows = [[r.get("member_no", ""), r.get("name", ""), r.get("mobile") or "",
                               r.get("village") or "", r.get("taluka") or "", str(r.get("registration_date") or "")]
                              for r in members_df.to_dict("records")]
            pdf_data = printable_pdf("सभासद यादी",
                ["सभासद क्रमांक", "नाव", "मोबाईल", "गाव", "तालुका", "नोंदणी तारीख"], printable_rows, True)
            filename = "baliraja_members.pdf"
        st.download_button("प्रिंटसाठी सभासद यादी PDF", pdf_data, filename, "application/pdf", key="members_print_pdf")

    st.subheader("पेमेंट रिपोर्ट")
    show_table(
        payments_df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "📥 Complete Excel Workbook",
        excel_report(),
        "baliraja_complete_reports.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.download_button(
        "📥 Members CSV",
        members_df.to_csv(index=False).encode(
            "utf-8-sig"
        ),
        "members.csv"
    )

    st.download_button(
        "📥 Payments CSV",
        payments_df.to_csv(index=False).encode(
            "utf-8-sig"
        ),
        "payments.csv"
    )

# ---------------- Gallery ----------------
elif page == "📷 Gallery":
    st.title("📷 सभासद Photo Gallery")

    images = list(UPLOADS.glob("*"))

    if not images:
        st.info(
            "सभासद फोटो अजून उपलब्ध नाहीत."
        )
    else:
        cols = st.columns(4)

        for i,image in enumerate(images):
            try:
                cols[i % 4].image(
                    str(image),
                    caption=image.name,
                    use_container_width=True
                )
            except Exception:
                pass

# ---------------- Masters ----------------
elif page == "🏘️ Masters":
    st.title("🏘️ Village / Taluka Master")

    if not is_admin():
        st.warning(
            "हे module फक्त Admin साठी आहे."
        )
        st.stop()

    st.subheader("तालुका")

    with st.form("taluka_form", clear_on_submit=True):
        taluka_name = st.text_input(
            "नवीन तालुका"
        )
        add_taluka = st.form_submit_button(
            "➕ तालुका जोडा"
        )

    if add_taluka:
        clean_taluka_name = taluka_name.strip()
        if not clean_taluka_name:
            st.warning("तालुक्याचे नाव लिहा.")
        elif query("SELECT id FROM talukas WHERE name=%s", (clean_taluka_name,)):
            st.warning("हा तालुका आधीपासून उपलब्ध आहे.")
        else:
            try:
                execute("INSERT INTO talukas(name) VALUES(%s)", (clean_taluka_name,))
                st.success(f"{clean_taluka_name} तालुका जोडला.")
            except Exception as exc:
                st.error("तालुका जतन होऊ शकला नाही. डेटाबेसमधील अडचण तपासा.")
                st.caption(str(exc))

    talukas = query(
        "SELECT * FROM talukas "
        "WHERE active=1 ORDER BY name"
    )

    if talukas:
        labels = [
            t["name"] for t in talukas
        ]

        selected = st.selectbox(
            "तालुका निवडा",
            labels
        )

        selected_id = talukas[
            labels.index(selected)
        ]["id"]

        with st.form("village_form"):
            village_name = st.text_input(
                "नवीन गाव"
            )

            add_village = st.form_submit_button(
                "➕ गाव जोडा"
            )

        if add_village and village_name.strip():
            try:
                execute(
                    '''INSERT INTO villages
                    (taluka_id,name)
                    VALUES(%s,%s)''',
                    (
                        selected_id,
                        village_name.strip()
                    )
                )

                st.success("गाव जोडले.")

            except Exception:
                st.error(
                    "हे गाव या तालुक्यात आधीपासून आहे."
                )

    st.subheader("सध्याचे गाव")

    villages = query(
        '''SELECT t.name AS taluka,
        v.name AS village
        FROM villages v
        JOIN talukas t ON t.id=v.taluka_id
        ORDER BY t.name,v.name'''
    )

    show_table(
        pd.DataFrame(villages),
        use_container_width=True,
        hide_index=True
    )

# ---------------- WhatsApp ----------------
elif page == "📲 WhatsApp संदेश":
    st.title("📲 सभासदांना WhatsApp संदेश")
    if not is_admin():
        st.warning("WhatsApp संदेश पाठवण्यासाठी Admin अधिकार आवश्यक आहेत.")
        st.stop()

    config = whatsapp_configuration()
    missing = missing_configuration(config)
    if missing:
        st.warning(
            "Cloud API सुरू करण्यासाठी सर्व्हरच्या `.env` मध्ये WhatsApp API सेटिंग्ज भरा. "
            "Access token ॲपमध्ये किंवा चॅटमध्ये टाकू नका."
        )
        st.code(
            "WHATSAPP_ACCESS_TOKEN=\n"
            "WHATSAPP_PHONE_NUMBER_ID=\n"
        "WHATSAPP_API_VERSION=<सध्या समर्थित Graph API version>\n"
            "WHATSAPP_TEMPLATE_NAME=\n"
            "WHATSAPP_TEMPLATE_LANGUAGE=mr"
        )
    st.caption(
        "फक्त सक्रिय आणि WhatsApp संदेशांसाठी स्पष्ट संमती नोंदवलेल्या सभासदांनाच संदेश जाईल. "
        "संघटनेने Meta कडून मंजूर केलेला template वापरणे आवश्यक आहे."
    )

    eligible_members = query('''SELECT id,member_no,name,mobile FROM members
        WHERE active=1 AND whatsapp_opt_in=1 ORDER BY name''')
    recipients = []
    invalid_numbers = []
    for member in eligible_members:
        normalized = normalize_indian_mobile(member["mobile"])
        if normalized:
            recipients.append((member, normalized))
        else:
            invalid_numbers.append(member)

    st.metric("संमती असलेले सक्रिय सभासद", len(eligible_members))
    st.caption(f"पाठवण्यायोग्य क्रमांक: {len(recipients)} · चुकीचा / नसलेला क्रमांक: {len(invalid_numbers)}")
    if invalid_numbers:
        with st.expander("क्रमांक दुरुस्त करावेत"):
            show_table(pd.DataFrame([
                {"सभासद क्रमांक": m["member_no"], "नाव": m["name"], "मोबाईल": m["mobile"] or ""}
                for m in invalid_numbers
            ]), hide_index=True)

    if not eligible_members:
        st.info("सध्या कोणत्याही सक्रिय सभासदाची WhatsApp संमती नोंदलेली नाही. Members पृष्ठावर संमती नोंदवा.")
    elif not recipients:
        st.info("संमती असलेल्या सभासदांचे वैध भारतीय मोबाईल क्रमांक उपलब्ध नाहीत.")
    elif not missing:
        option_by_label = {
            f"{m['member_no']} — {m['name']} ({m['mobile']})": (m, phone)
            for m, phone in recipients
        }
        selected_labels = st.multiselect(
            "प्राप्तकर्ते", list(option_by_label), default=list(option_by_label),
            key="whatsapp_recipients"
        )
        message = st.text_area(
            "सामायिक संदेश (मंजूर template मधील {{1}} जागी दिसेल)",
            max_chars=1024, key="whatsapp_common_message"
        )
        st.info(
            f"मंजूर template: `{config['template_name']}` · भाषा: `{config['template_language']}` · "
            f"निवडलेले प्राप्तकर्ते: {len(selected_labels)}"
        )
        confirm_send = st.checkbox(
            f"मी {len(selected_labels)} प्राप्तकर्त्यांना हा संदेश पाठवण्याची पुष्टी करतो/करते.",
            key="whatsapp_confirm_send"
        )
        send_now = st.button(
            "📤 WhatsApp संदेश पाठवा", type="primary",
            disabled=not (confirm_send and bool(message.strip()) and bool(selected_labels)),
            key="whatsapp_send_button"
        )
        if send_now:
            batch_id = str(uuid.uuid4())
            progress = st.progress(0, text="संदेश पाठवत आहे…")
            sent_count = failed_count = 0
            results = []
            for index, label in enumerate(selected_labels, start=1):
                member, phone = option_by_label[label]
                provider_id, error = send_template_message(config, phone, message.strip())
                status = "accepted" if not error else "failed"
                execute('''INSERT INTO whatsapp_message_logs
                    (batch_id,member_id,recipient_phone,template_name,status,
                     provider_message_id,error_text,sent_by)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (batch_id, member["id"], phone, config["template_name"],
                     status, provider_id, error, user["id"]))
                sent_count += status == "accepted"
                failed_count += status == "failed"
                results.append({"नाव": member["name"], "मोबाईल": phone,
                                "स्थिती": "API ने स्वीकारली" if status == "accepted" else "अयशस्वी",
                                "तपशील": provider_id or error})
                progress.progress(index / len(selected_labels), text=f"{index}/{len(selected_labels)} पूर्ण")
                time.sleep(0.15)
            st.success(f"API ने {sent_count} विनंत्या स्वीकारल्या; {failed_count} विनंत्या अयशस्वी झाल्या.")
            st.caption("API acceptance म्हणजे फोनवर संदेश पोहोचल्याची खात्री नाही; वितरणाची स्थिती WhatsApp webhook मधून कळते.")
            show_table(pd.DataFrame(results), hide_index=True)

    recent_batches = query('''SELECT batch_id,MIN(created_at) AS created_at,
        COUNT(*) AS total,SUM(status='accepted') AS accepted,SUM(status='failed') AS failed
        FROM whatsapp_message_logs GROUP BY batch_id ORDER BY MIN(created_at) DESC LIMIT 10''')
    if recent_batches:
        st.subheader("अलीकडील पाठवणी")
        show_table(pd.DataFrame(recent_batches), hide_index=True)

# ---------------- Admin ----------------
elif page == "⚙️ Admin":
    st.title("⚙️ Admin Panel")

    if not is_admin():
        st.warning(
            "Admin अधिकार आवश्यक आहेत."
        )
        st.stop()

    st.subheader("👨‍🌾 सभासद संपादन / हटवणे")
    admin_members = query('''SELECT id,member_no,name,mobile,village_id,address,
        identity_info,registration_date,active,whatsapp_opt_in FROM members ORDER BY id DESC''')
    if admin_members:
        member_options = {f"{m['member_no']} — {m['name']}" : m for m in admin_members}
        member_label = st.selectbox("सभासद निवडा", list(member_options), key="admin_member_select")
        selected_member = member_options[member_label]
        villages_admin = query("SELECT id,name FROM villages ORDER BY name")
        village_ids = [None] + [v["id"] for v in villages_admin]
        village_names = ["-- गाव निवडा --"] + [v["name"] for v in villages_admin]
        current_village_index = village_ids.index(selected_member["village_id"]) if selected_member["village_id"] in village_ids else 0
        with st.form("admin_member_edit"):
            ma, mb = st.columns(2)
            edit_name = ma.text_input("नाव", selected_member["name"])
            edit_mobile = mb.text_input("मोबाईल", selected_member["mobile"] or "")
            edit_village = ma.selectbox("गाव", village_names, index=current_village_index)
            edit_address = mb.text_area("पत्ता", selected_member["address"] or "")
            edit_identity = ma.text_input("ओळख माहिती", selected_member["identity_info"] or "")
            edit_registration_date_pending = mb.checkbox(
                "नोंदणी तारीख नंतर भरा",
                value=selected_member["registration_date"] is None,
                key=f"admin_reg_date_pending_{selected_member['id']}"
            )
            edit_registration_date = mb.date_input(
                "नोंदणी तारीख", selected_member["registration_date"] or datetime.date.today(),
                disabled=edit_registration_date_pending
            )
            edit_member_active = st.checkbox("सभासद सक्रिय", value=bool(selected_member["active"]))
            edit_member_whatsapp_opt_in = st.checkbox(
                "WhatsApp संदेशांसाठी स्पष्ट संमती नोंदलेली आहे",
                value=bool(selected_member["whatsapp_opt_in"]),
                help="सभासदाने संमती दिलेली असल्याची खात्री करूनच निवडा."
            )
            save_member = st.form_submit_button("सभासद माहिती जतन करा")
        if save_member:
            if not edit_name.strip():
                st.error("नाव आवश्यक आहे.")
            else:
                village_id_value = village_ids[village_names.index(edit_village)]
                execute('''UPDATE members SET name=%s,mobile=%s,village_id=%s,address=%s,
                    identity_info=%s,registration_date=%s,active=%s,whatsapp_opt_in=%s WHERE id=%s''',
                    (edit_name.strip(), edit_mobile.strip(), village_id_value,
                     edit_address.strip(), edit_identity.strip(),
                     None if edit_registration_date_pending else str(edit_registration_date),
                     int(edit_member_active), int(edit_member_whatsapp_opt_in), selected_member["id"]))
                st.success("सभासद माहिती अद्ययावत झाली.")
                st.rerun()
        delete_member_confirm = st.checkbox("हा सभासद निष्क्रिय करण्याची खात्री आहे", key="delete_member_confirm")
        if st.button("सभासद निष्क्रिय करा", disabled=not delete_member_confirm, key="deactivate_member"):
            execute("UPDATE members SET active=0 WHERE id=%s", (selected_member["id"],))
            st.success("सभासद निष्क्रिय केला. त्याच्या पावत्या आणि व्यवहार जतन राहतील.")
            st.rerun()
    else:
        st.info("सभासद उपलब्ध नाहीत.")

    st.divider()
    st.subheader("🧾 पावती संपादन / हटवणे")
    admin_receipts = query('''SELECT p.id,p.receipt_no,p.member_id,p.payment_type,p.amount,
        p.payment_method,p.transaction_no,p.payment_date,p.note,m.name,m.member_no
        FROM payments p JOIN members m ON m.id=p.member_id ORDER BY p.id DESC''')
    if admin_receipts:
        receipt_options = {f"{r['receipt_no']} — {r['name']} — ₹{float(r['amount']):,.2f}" : r for r in admin_receipts}
        receipt_label = st.selectbox("पावती निवडा", list(receipt_options), key="admin_receipt_select")
        selected_receipt = receipt_options[receipt_label]
        member_list = query("SELECT id,member_no,name FROM members ORDER BY name")
        member_ids = [m["id"] for m in member_list]
        member_select_labels = [f"{m['member_no']} — {m['name']}" for m in member_list]
        with st.form("admin_receipt_edit"):
            selected_member_index = member_ids.index(selected_receipt["member_id"])
            edit_receipt_member = st.selectbox("सभासद", member_select_labels, index=selected_member_index)
            ra, rb = st.columns(2)
            receipt_types = ["Membership Fee", "Other Contribution", "Donation"]
            edit_payment_type = ra.selectbox("प्रकार", receipt_types, index=receipt_types.index(selected_receipt["payment_type"]), format_func=lambda x: {"Membership Fee": "सभासद फी", "Other Contribution": "इतर वर्गणी", "Donation": "देणगी"}[x])
            edit_amount = rb.number_input("रक्कम ₹", min_value=0.01, value=float(selected_receipt["amount"]), step=100.0)
            edit_payment_method = ra.selectbox("पेमेंट पद्धत", ["Cash", "UPI", "Bank"], index=["Cash", "UPI", "Bank"].index(selected_receipt["payment_method"]))
            edit_transaction_no = rb.text_input("UTR / व्यवहार क्रमांक", selected_receipt["transaction_no"] or "")
            edit_payment_date_pending = ra.checkbox(
                "तारीख नंतर भरा", value=selected_receipt["payment_date"] is None,
                key=f"admin_receipt_date_pending_{selected_receipt['id']}"
            )
            edit_payment_date = ra.date_input(
                "तारीख", selected_receipt["payment_date"] or datetime.date.today(),
                disabled=edit_payment_date_pending
            )
            edit_payment_note = rb.text_area("नोंद", selected_receipt["note"] or "")
            save_receipt = st.form_submit_button("पावती माहिती जतन करा")
        if save_receipt:
            execute('''UPDATE payments SET member_id=%s,payment_type=%s,amount=%s,
                payment_method=%s,transaction_no=%s,payment_date=%s,note=%s WHERE id=%s''',
                (member_ids[member_select_labels.index(edit_receipt_member)], edit_payment_type,
                 edit_amount, edit_payment_method, edit_transaction_no.strip(),
                 None if edit_payment_date_pending else str(edit_payment_date),
                 edit_payment_note.strip(), selected_receipt["id"]))
            st.success("पावती अद्ययावत झाली.")
            st.rerun()
        delete_receipt_confirm = st.checkbox("ही पावती आणि संबंधित जमा नोंद कायमची हटवण्याची खात्री आहे", key="delete_receipt_confirm")
        if st.button("पावती कायमची हटवा", disabled=not delete_receipt_confirm, key="delete_receipt"):
            execute("DELETE FROM payments WHERE id=%s", (selected_receipt["id"],))
            st.success("पावती हटवली.")
            st.rerun()
    else:
        st.info("पावत्या उपलब्ध नाहीत.")

    st.divider()

    st.subheader("👤 Staff Account तयार करा")

    with st.form("staff_form"):
        username = st.text_input(
            "Username"
        )

        full_name = st.text_input(
            "पूर्ण नाव"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        create = st.form_submit_button(
            "Create Staff"
        )

    if create and username and password:
        try:
            execute(
                '''INSERT INTO users
                (username,password_hash,full_name,role)
                VALUES(%s,%s,%s,'staff')''',
                (
                    username,
                    hash_password(password),
                    full_name
                )
            )

            st.success(
                "Staff account तयार झाले."
            )

        except Exception:
            st.error(
                "Username आधीपासून उपलब्ध आहे."
            )

    st.divider()

    st.subheader("💳 UPI QR")

    upi_id = st.text_input(
        "UPI ID",
        setting("UPI_ID","yourupi@bank")
    )

    upi_name = st.text_input(
        "UPI Name",
        setting(
            "UPI_NAME",
            "बळीराजा शेतकरी संघटना"
        )
    )

    amount = st.number_input(
        "QR Amount ₹",
        min_value=1.0,
        value=100.0
    )

    if st.button("Generate UPI QR"):
        path = EXPORTS / "upi_qr.png"

        uri = create_upi_qr(
            upi_id,
            upi_name,
            amount,
            "सभासद वर्गणी / देणगी",
            path
        )

        st.image(
            str(path),
            width=250
        )

        st.code(uri)

    st.divider()

    st.subheader("💰 Membership Fee")

    current = query(
        "SELECT value FROM settings "
        "WHERE `key`='membership_fee'"
    )

    current_fee = float(
        current[0]["value"]
        if current else 0
    )

    new_fee = st.number_input(
        "प्रति सभासद वर्गणी ₹",
        min_value=0.0,
        value=current_fee
    )

    if st.button("Save Membership Fee"):
        execute(
            '''INSERT INTO settings(`key`,`value`)
            VALUES('membership_fee',%s)
            ON DUPLICATE KEY UPDATE value=%s''',
            (str(new_fee),str(new_fee))
        )

        st.success(
            "Membership Fee updated."
        )

    st.divider()

    st.subheader("🗄️ MySQL Backup")

    st.info(
        "Production server वर scheduled mysqldump backup "
        "ठेवणे आवश्यक आहे. MySQL database ची साधी file-copy "
        "backup पद्धत वापरू नका."
    )
