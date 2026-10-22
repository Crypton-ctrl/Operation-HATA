import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 755, "OPERATION HATA — Full Setup & Installation Guide")
            self.drawRightString(558, 755, "Confidential / Project Manual")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 747, 558, 747)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Operation HATA (Hidden Attachment Threat Analyzer) • AI-Assisted Security Platform")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()

def build_pdf(filename="Operation_HATA_Setup_Guide.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom color palette
    c_primary = colors.HexColor("#0f172a")     # Slate 900
    c_accent = colors.HexColor("#0284c7")      # Sky 600
    c_accent_dark = colors.HexColor("#0369a1") # Sky 700
    c_text = colors.HexColor("#1e293b")        # Slate 800
    c_muted = colors.HexColor("#475569")       # Slate 600
    c_code_bg = colors.HexColor("#f1f5f9")     # Slate 100
    c_box_bg = colors.HexColor("#f8fafc")      # Slate 50
    c_border = colors.HexColor("#cbd5e1")      # Slate 300
    c_green = colors.HexColor("#16a34a")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_accent,
        spaceAfter=15
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_accent_dark,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_text,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=2,
        spaceAfter=2
    )

    note_style = ParagraphStyle(
        'NoteText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b")
    )

    def make_code_box(code_text):
        p = Paragraph(code_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)
        t = Table([[p]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_code_bg),
            ('BOX', (0,0), (-1,-1), 0.5, c_border),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        return t

    def make_callout(text, label="IMPORTANT NOTE"):
        p = Paragraph(f"<b>{label}:</b> {text}", note_style)
        t = Table([[p]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#93c5fd")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        return t

    story = []

    # Cover / Header
    story.append(Spacer(1, 10))
    story.append(Paragraph("OPERATION HATA", title_style))
    story.append(Paragraph("Hidden Attachment Threat Analyzer — Complete Setup & Installation Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=0, spaceAfter=12))

    # Executive Overview
    story.append(Paragraph(
        "<b>Operation HATA</b> is an AI-assisted cybersecurity platform that automatically monitors email inboxes "
        "for image attachments, isolates them in a secure quarantine environment, runs them through a multi-layer "
        "18-stage forensic analysis pipeline (entropy, steganography, YARA rules, OCR, QR heuristics, and AI report generation), "
        "and visualizes threat metrics on a real-time SOC dashboard.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # Section 1: Prerequisites
    story.append(Paragraph("1. System Requirements & Prerequisites", h1_style))
    story.append(Paragraph(
        "Before setting up Operation HATA, ensure your system has the following software installed:", body_style
    ))
    story.append(Paragraph("• <b>Operating System:</b> Windows 10/11, macOS, or Ubuntu Linux (20.04+).", bullet_style))
    story.append(Paragraph("• <b>Python:</b> Version 3.11 or higher (with pip enabled).", bullet_style))
    story.append(Paragraph("• <b>Node.js:</b> Version 18.0 or higher (with npm 9+).", bullet_style))
    story.append(Paragraph("• <b>Git:</b> Installed and available in terminal.", bullet_style))
    story.append(Paragraph("• <b>(Optional Forensic Tools):</b> Tesseract OCR (for image text detection) and ExifTool.", bullet_style))
    story.append(Spacer(1, 6))

    # Section 2: Cloning
    story.append(Paragraph("2. Clone the Repository", h1_style))
    story.append(Paragraph("Open PowerShell, Command Prompt, or Terminal, and run:", body_style))
    story.append(make_code_box(
        "git clone https://github.com/Crypton-ctrl/Operation-HATA.git\n"
        "cd Operation-HATA/hata"
    ))
    story.append(Spacer(1, 6))

    # Section 3: Backend Setup
    story.append(Paragraph("3. Backend Setup (FastAPI & Python)", h1_style))
    story.append(Paragraph(
        "The backend server powers the API, database, analysis pipeline, and 24/7 email monitoring loop.", body_style
    ))

    story.append(Paragraph("Step 3.1: Create & Activate Virtual Environment", h2_style))
    story.append(Paragraph("Navigate to the backend directory and set up a clean Python virtual environment:", body_style))
    story.append(make_code_box(
        "cd backend\n"
        "# Create virtual environment\n"
        "python -m venv venv\n\n"
        "# Activate on Windows (PowerShell):\n"
        ".\\venv\\Scripts\\Activate.ps1\n\n"
        "# OR activate on Linux / macOS:\n"
        "source venv/bin/activate"
    ))
    story.append(Paragraph(
        "<i>If Windows displays a script execution policy error, run:</i> "
        "<code>Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass</code> before activating.", body_style
    ))

    story.append(Paragraph("Step 3.2: Install Python Dependencies", h2_style))
    story.append(make_code_box("pip install -r requirements.txt"))

    story.append(Paragraph("Step 3.3: Configure the .env File", h2_style))
    story.append(Paragraph("Copy the example configuration to create your active <code>.env</code> file:", body_style))
    story.append(make_code_box(
        "# Windows (PowerShell):\n"
        "Copy-Item .env.example .env\n\n"
        "# Linux / macOS:\n"
        "cp .env.example .env"
    ))
    story.append(Paragraph(
        "Open <code>.env</code> in your text editor. Key variables to verify or set:", body_style
    ))

    env_table_data = [
        [Paragraph("<b>Variable</b>", code_style), Paragraph("<b>Description & Default Value</b>", code_style)],
        [Paragraph("SECRET_KEY", code_style), Paragraph("Random secret key for token encryption (e.g. <code>hata-secret-key-2026</code>)", body_style)],
        [Paragraph("CORS_ORIGINS", code_style), Paragraph("<code>http://localhost:5173,http://localhost:5174,http://localhost:5175,https://operation-hata.netlify.app</code>", body_style)],
        [Paragraph("DATABASE_URL", code_style), Paragraph("<code>sqlite:///./hata.db</code> (zero-config, local database)", body_style)],
        [Paragraph("GMAIL_CLIENT_ID", code_style), Paragraph("Your Google OAuth Web Client ID (from Google Cloud Console)", body_style)],
        [Paragraph("GMAIL_CLIENT_SECRET", code_style), Paragraph("Your Google OAuth Client Secret", body_style)],
        [Paragraph("GMAIL_REDIRECT_URI", code_style), Paragraph("<code>http://localhost:8000/api/emails/oauth/callback</code>", body_style)],
    ]
    t_env = Table(env_table_data, colWidths=[150, 354])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_env)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Step 3.4: Launch the Backend Server", h2_style))
    story.append(make_code_box(
        "# From inside the 'backend' folder:\n"
        "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    ))
    story.append(Paragraph(
        "You will see: <code>Uvicorn running on http://127.0.0.1:8000</code>. "
        "The SQLite database (<code>hata.db</code>) will be created automatically on startup!", body_style
    ))

    story.append(PageBreak())

    # Section 4: Frontend Setup
    story.append(Paragraph("4. Frontend Setup (React + Vite)", h1_style))
    story.append(Paragraph(
        "Open a <b>new terminal window</b> (keep the backend terminal running).", body_style
    ))
    story.append(Paragraph("Step 4.1: Install Node Dependencies", h2_style))
    story.append(make_code_box(
        "cd Operation-HATA/hata/frontend\n"
        "npm install"
    ))

    story.append(Paragraph("Step 4.2: Start the Frontend Dev Server", h2_style))
    story.append(make_code_box("npm run dev"))
    story.append(Paragraph(
        "Vite will start the dev server (typically on <b>http://localhost:5174</b> or <b>http://localhost:5175</b>). "
        "Open this URL in your web browser to view the application!", body_style
    ))
    story.append(Spacer(1, 6))

    # Section 5: Google Cloud Setup
    story.append(Paragraph("5. Google OAuth 2.0 & Gmail Monitoring Setup", h1_style))
    story.append(Paragraph(
        "Operation HATA allows 1-click Google Sign-in that automatically connects the user's Gmail "
        "account to 24/7 mailbox threat analysis.", body_style
    ))

    story.append(Paragraph("Step 5.1: Enable the Gmail API", h2_style))
    story.append(Paragraph(
        "1. Open the <b>Google Cloud Console</b> (<font color='#0284c7'>https://console.cloud.google.com</font>).<br/>"
        "2. Navigate to <b>APIs & Services &rarr; Library</b>.<br/>"
        "3. Search for <b>Gmail API</b> and click <b>ENABLE</b>.",
        body_style
    ))

    story.append(Paragraph("Step 5.2: Configure OAuth Consent Screen & Test Users", h2_style))
    story.append(Paragraph(
        "1. Go to <b>APIs & Services &rarr; OAuth consent screen</b> (or <b>Audience</b>).<br/>"
        "2. Select <b>External</b> User Type.<br/>"
        "3. Set App Name to <code>Operation HATA</code> and enter your support email.<br/>"
        "4. Leave <i>Application home page</i>, <i>Privacy policy</i>, and <i>Authorized domains</i> <b>BLANK</b>.<br/>"
        "5. Under <b>Test users</b>, click <b>+ ADD USERS</b> and type your friend's Gmail address (and your own). Click <b>SAVE</b>.",
        body_style
    ))

    story.append(Paragraph("Step 5.3: Create Web Client Credentials", h2_style))
    story.append(Paragraph(
        "1. Go to <b>APIs & Services &rarr; Credentials</b>.<br/>"
        "2. Click <b>+ CREATE CREDENTIALS &rarr; OAuth client ID</b>.<br/>"
        "3. Application type: <b>Web application</b>.<br/>"
        "4. <b>Authorized JavaScript origins:</b> Add:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <code>http://localhost:5173</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <code>http://localhost:5174</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <code>http://localhost:5175</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <code>https://operation-hata.netlify.app</code><br/>"
        "5. <b>Authorized redirect URIs:</b> Add:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <code>http://localhost:8000/api/emails/oauth/callback</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <code>http://127.0.0.1:8000/api/emails/oauth/callback</code><br/>"
        "6. Click <b>CREATE</b> and copy the generated <b>Client ID</b> and <b>Client Secret</b> into your <code>backend/.env</code> file.",
        body_style
    ))
    story.append(make_callout(
        "While your Google Cloud app is in Testing mode, only Gmail accounts added to 'Test users' can log in. "
        "To allow ANY person worldwide to log in, simply click 'PUBLISH APP' on the OAuth consent screen!",
        "TEST USERS VS PRODUCTION"
    ))
    story.append(Spacer(1, 6))

    # Section 6: How to Use
    story.append(Paragraph("6. Using Operation HATA", h1_style))
    story.append(Paragraph("<b>A. Logging In:</b>", h2_style))
    story.append(Paragraph(
        "Open <code>http://localhost:5175/login</code> and click <b>Sign in with Google</b>. "
        "Upon signing in, your dynamic name and registered Gmail address will appear on the dashboard.", body_style
    ))
    story.append(Paragraph(
        "<i>(Alternative Local Admin Account):</i> You can also log in with Username: <code>admin</code> and Password: <code>Admin@12345</code>.", body_style
    ))

    story.append(Paragraph("<b>B. Automatic Gmail Monitoring:</b>", h2_style))
    story.append(Paragraph(
        "Click <b>Automatic Monitoring</b> in the left sidebar. The system checks for unread emails with attachments "
        "every 60 seconds. When an image attachment arrives, it is isolated in quarantine, analyzed through the forensic "
        "pipeline, and an alert is broadcast to the dashboard in real-time.", body_style
    ))

    story.append(Paragraph("<b>C. Manual Threat Scanning:</b>", h2_style))
    story.append(Paragraph(
        "Click <b>Manual Scan</b>. Drag and drop any image file (PNG, JPG, BMP, TIFF, GIF, WEBP) to run the 18 forensic checks: "
        "Magic bytes verification, SHA-256 hash, EXIF metadata, Shannon entropy, Steganography chi-square test, appended ZIP/PE payload detection, and QR code inspection.", body_style
    ))

    story.append(Paragraph("<b>D. Quarantine & PDF Reports:</b>", h2_style))
    story.append(Paragraph(
        "View the <b>Quarantine</b> tab to inspect suspicious files safely. Click any completed scan to download a full, "
        "executive-ready forensic PDF report.", body_style
    ))

    story.append(PageBreak())

    # Section 7: Troubleshooting
    story.append(Paragraph("7. Troubleshooting & FAQ", h1_style))

    trouble_data = [
        [
            Paragraph("<b>Issue / Error</b>", code_style),
            Paragraph("<b>Root Cause & Fix</b>", code_style)
        ],
        [
            Paragraph("Error 403: access_denied", code_style),
            Paragraph("The Gmail ID is not listed under <b>Test users</b> in Google Cloud Console. Go to <i>Audience &rarr; Test users &rarr; + ADD USERS</i>.", body_style)
        ],
        [
            Paragraph("Error 400: redirect_uri_mismatch", code_style),
            Paragraph("The Authorized Redirect URI is missing. In Google Cloud Console Credentials, add <code>http://localhost:8000/api/emails/oauth/callback</code> with no trailing slash.", body_style)
        ],
        [
            Paragraph("Gmail API disabled (403)", code_style),
            Paragraph("Enable the Gmail API in your Google Cloud Project: <i>APIs & Services &rarr; Library &rarr; Search 'Gmail API' &rarr; Click Enable</i>.", body_style)
        ],
        [
            Paragraph("Port 5174 is in use", code_style),
            Paragraph("Vite automatically increments to port <code>5175</code>. Check terminal output for the active URL and open <code>http://localhost:5175</code>.", body_style)
        ],
        [
            Paragraph("Could not connect to server on Netlify", code_style),
            Paragraph("Netlify only hosts the frontend. For Netlify to work, deploy the backend to Render or AWS EC2 and add <code>VITE_API_BASE_URL</code> in Netlify Environment Variables.", body_style)
        ],
        [
            Paragraph("ExecutionPolicy error in PowerShell", code_style),
            Paragraph("Run <code>Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass</code> in PowerShell before running <code>Activate.ps1</code>.", body_style)
        ]
    ]
    t_trouble = Table(trouble_data, colWidths=[150, 354])
    t_trouble.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_trouble)
    story.append(Spacer(1, 14))

    # Section 8: Quick Command Cheat Sheet
    story.append(Paragraph("8. Quick Command Cheat Sheet", h1_style))
    story.append(Paragraph("Keep this handy whenever starting the project:", body_style))
    story.append(make_code_box(
        "# Terminal 1: Backend\n"
        "cd Operation-HATA/hata/backend\n"
        ".\\venv\\Scripts\\activate\n"
        "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload\n\n"
        "# Terminal 2: Frontend\n"
        "cd Operation-HATA/hata/frontend\n"
        "npm run dev\n\n"
        "# Access in Browser:\n"
        "Frontend:  http://localhost:5175 (or 5174)\n"
        "Backend Swagger Docs: http://localhost:8000/docs"
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<b>Need help or want to contribute?</b> Visit the project repository at: "
        "<font color='#0284c7'><u>https://github.com/Crypton-ctrl/Operation-HATA</u></font>",
        body_style
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built: {filename}")

if __name__ == '__main__':
    out_file = sys.argv[1] if len(sys.argv) > 1 else "Operation_HATA_Setup_Guide.pdf"
    build_pdf(out_file)
