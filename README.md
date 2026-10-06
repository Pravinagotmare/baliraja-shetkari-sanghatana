# 🌾 बळीराजा शेतकरी संघटना — Production App

## Included

- Public organization website (about, executive body, programs, gallery, contact)

- Admin Login
- Staff Login
- Role-based access
- MySQL
- Member registration
- Member photo
- Taluka/Village master
- Membership Fee
- Donation
- Cash / UPI / Bank
- Automatic member number
- Automatic receipt number
- UPI QR
- Single PDF receipt
- A4 2-receipt PDF
- A4 3-receipt PDF
- Due membership report
- Village/Taluka reports
- Monthly-ready Excel reporting
- Complete Excel workbook
- CSV export
- Photo gallery
- Admin WhatsApp Cloud API bulk messaging (opt-in members and approved templates)

## 1. MySQL

Open MySQL Workbench or MySQL command line and run:

    sql/schema.sql

Change `CHANGE_THIS_PASSWORD` to your own strong password.

## 2. Python

    pip install -r requirements.txt

## 3. Environment

Copy:

    .env.example

to:

    .env

For WhatsApp Cloud API setup, see [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md).

Then change database password and admin password.

## 4. Start

    streamlit run app.py

Open:

    http://localhost:8501

The first sidebar selector opens the public website. Choose **कर्मचारी लॉगिन**
to access the member and finance dashboard. Public event photos can be added
as JPG, PNG, or WebP files to `assets/public_gallery`; member portraits in
`uploads` are not displayed publicly.

Public videos in MP4, WebM, MOV, or M4V format can be added to
`assets/public_videos`; they appear in the **व्हिडिओ दालन** tab. The tab also
links to the organization's YouTube channel.

## 5. Mobile

If PC and phone are on the same Wi-Fi:

    streamlit run app.py --server.address 0.0.0.0

Then open:

    http://PC-IP:8501

## Security

Do not expose Streamlit directly to the public internet without HTTPS,
strong authentication, firewall configuration and scheduled backups.

Aadhaar/identity information should only be collected when necessary
and access should be restricted.
