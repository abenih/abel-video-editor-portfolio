import os
import sqlite3
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/home/benji/Downloads/littlekingo-portfolio"
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")
THUMB_DIR = os.path.join(BASE_DIR, "media", "projects", "thumbnails")
os.makedirs(THUMB_DIR, exist_ok=True)

PROJECTS_DATA = [
    {
        "title": "Agent Mesh — Multi-Agent Hub & Zero-Trust Secret Broker",
        "category": "Software & AI",
        "client": "Open Source / SatiraLabs",
        "description": "Ultra-lightweight, zero-cost, secure multi-agent communication hub, handover synchronization engine, and zero-trust secret broker with native desktop control GUI.",
        "video_url": "https://github.com/abenih/agent-mesh",
        "thumb_file": "projects/thumbnails/thumb_agent_mesh.png",
        "bg_color": (15, 23, 42),
        "accent_color": (99, 102, 241),
        "tag": "MULTI-AGENT ENGINE",
        "icon_label": "AGENT MESH"
    },
    {
        "title": "Barehands — Vision Gesture Engine & Tracker",
        "category": "Computer Vision",
        "client": "Open Source / SatiraLabs",
        "description": "Webcam hand-tracked spatial interface and gesture engine with live Gesture Lab, neural classifier trainer, and touchless desktop control.",
        "video_url": "https://github.com/abenih/barehands",
        "thumb_file": "projects/thumbnails/thumb_barehands.png",
        "bg_color": (13, 24, 20),
        "accent_color": (16, 185, 129),
        "tag": "SPATIAL INTERACTION",
        "icon_label": "BAREHANDS"
    },
    {
        "title": "ScopeDesk — Metasploit Module Atlas",
        "category": "Cybersecurity",
        "client": "Open Source / SatiraLabs",
        "description": "Searchable Metasploit module atlas and authorized, check-first security engagement planner built on Metasploit Framework metadata.",
        "video_url": "https://github.com/abenih/msf-scopedesk",
        "thumb_file": "projects/thumbnails/thumb_scopedesk.png",
        "bg_color": (26, 15, 20),
        "accent_color": (244, 63, 94),
        "tag": "OFFENSIVE SECURITY",
        "icon_label": "SCOPEDESK"
    },
    {
        "title": "PhoneStream — Android Remote Studio",
        "category": "Mobile & Systems",
        "client": "Open Source / SatiraLabs",
        "description": "Low-latency Android phone streaming, real-time remote canvas rendering, and interactive desktop control workstation.",
        "video_url": "https://github.com/abenih/phone-stream",
        "thumb_file": "projects/thumbnails/thumb_phonestream.png",
        "bg_color": (26, 21, 14),
        "accent_color": (245, 158, 11),
        "tag": "LOW-LATENCY STREAMING",
        "icon_label": "PHONESTREAM"
    },
    {
        "title": "IPLoc — Network Intelligence & Geo-Locator",
        "category": "Networking & OSINT",
        "client": "Open Source / SatiraLabs",
        "description": "Fast IP geolocation, ASN routing intelligence, and threat-reconnaissance discovery utility.",
        "video_url": "https://github.com/abenih/IPLoc",
        "thumb_file": "projects/thumbnails/thumb_iploc.png",
        "bg_color": (14, 21, 33),
        "accent_color": (6, 182, 212),
        "tag": "OSINT & RECONNAISSANCE",
        "icon_label": "IPLOC"
    },
    {
        "title": "AgentLedger — Cryptographic Action Attestation & Governance",
        "category": "AI Safety & Governance",
        "client": "Open Source / SatiraLabs",
        "description": "Cryptographic action attestation, SHA-256 Merkle audit trail, and zero-trust execution guardrails for autonomous AI agent tool execution.",
        "video_url": "https://github.com/abenih/agent-ledger",
        "thumb_file": "projects/thumbnails/thumb_agent_ledger.png",
        "bg_color": (17, 24, 39),
        "accent_color": (59, 130, 246),
        "tag": "AI SAFETY & MERKLE AUDIT",
        "icon_label": "AGENTLEDGER"
    },
    {
        "title": "DialectMesh — Edge Semantic Router for Low-Resource Languages",
        "category": "Edge AI & NLP",
        "client": "Open Source / SatiraLabs",
        "description": "Offline-first edge semantic router & NLU engine for Amharic, Afaan Oromo, and Kiswahili mapping vernacular queries to structured tool dispatch.",
        "video_url": "https://github.com/abenih/dialect-mesh",
        "thumb_file": "projects/thumbnails/thumb_dialect_mesh.png",
        "bg_color": (20, 26, 15),
        "accent_color": (34, 197, 94),
        "tag": "OFFLINE-FIRST NLU",
        "icon_label": "DIALECTMESH"
    },
    {
        "title": "SovereignSentinel — Verifiable OSINT & Fact Graph Engine",
        "category": "OSINT & Civic Tech",
        "client": "Open Source / SatiraLabs",
        "description": "Verifiable OSINT and counter-disinformation knowledge graph engine with tamper-proof source lineage and belief propagation.",
        "video_url": "https://github.com/abenih/sovereign-sentinel",
        "thumb_file": "projects/thumbnails/thumb_sovereign_sentinel.png",
        "bg_color": (24, 18, 33),
        "accent_color": (168, 85, 247),
        "tag": "PROVENANCE GRAPH",
        "icon_label": "SENTINEL"
    },
    {
        "title": "EdgeStream AI — Low-Resource Computer Vision & Event Trigger",
        "category": "Edge Computer Vision",
        "client": "Open Source / SatiraLabs",
        "description": "Ultra-low-resource computer vision and motion activity engine running under 15MB RAM on edge CPUs with instant webhook alerts.",
        "video_url": "https://github.com/abenih/edge-stream-ai",
        "thumb_file": "projects/thumbnails/thumb_edge_stream_ai.png",
        "bg_color": (28, 20, 14),
        "accent_color": (245, 158, 11),
        "tag": "ZERO-GPU STREAM CV",
        "icon_label": "EDGESTREAM"
    },
    {
        "title": "ProvableFair AI — Algorithmic Fairness & Audit Sandbox",
        "category": "Algorithmic Transparency",
        "client": "Open Source / SatiraLabs",
        "description": "Algorithmic fairness evaluation sandbox and cryptographic commit-reveal verification framework for digital decision systems.",
        "video_url": "https://github.com/abenih/provable-fair-ai",
        "thumb_file": "projects/thumbnails/thumb_provable_fair_ai.png",
        "bg_color": (14, 28, 36),
        "accent_color": (6, 182, 212),
        "tag": "MATHEMATICAL FAIRNESS",
        "icon_label": "PROVABLEFAIR"
    }
]

def create_thumbnail(item):
    w, h = 800, 450
    img = Image.new("RGBA", (w, h), item["bg_color"] + (255,))
    draw = ImageDraw.Draw(img)

    # Decorative grid lines
    for x in range(0, w, 40):
        draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 8), width=1)
    for y in range(0, h, 40):
        draw.line([(0, y), (w, y)], fill=(255, 255, 255, 8), width=1)

    # Accent border
    acc = item["accent_color"]
    draw.rounded_rectangle([(16, 16), (w - 16, h - 16)], radius=16, outline=acc + (120,), width=2)

    # Badge pill top-left
    draw.rounded_rectangle([(40, 40), (320, 72)], radius=8, fill=acc + (40,), outline=acc + (180,), width=1)
    draw.text((54, 48), item["tag"], fill=acc + (255,))

    # Main Card Symbol
    draw.rounded_rectangle([(w // 2 - 140, h // 2 - 80), (w // 2 + 140, h // 2 + 30)], radius=20, fill=(0, 0, 0, 140), outline=acc + (160,), width=2)
    draw.text((w // 2 - 70, h // 2 - 35), item["icon_label"], fill=(255, 255, 255, 240))

    # Title bottom
    draw.text((40, h - 70), item["title"].split(" — ")[0], fill=(255, 255, 255, 240))
    draw.text((40, h - 45), item["category"], fill=acc + (220,))

    out_path = os.path.join(BASE_DIR, "media", item["thumb_file"])
    img.save(out_path, "PNG")
    print(f"Created: {out_path}")

def sync_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, item in enumerate(PROJECTS_DATA, start=1):
        create_thumbnail(item)
        cur.execute("SELECT id FROM portfolio_project WHERE title = ?;", (item["title"],))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE portfolio_project
                SET category = ?, client = ?, description = ?, video_url = ?, thumbnail = ?, is_featured = 1, "order" = ?, updated_at = ?
                WHERE id = ?;
            """, (item["category"], item["client"], item["description"], item["video_url"], item["thumb_file"], idx, now_str, row[0]))
            print(f"Updated: {item['title']} (ID {row[0]})")
        else:
            cur.execute("""
                INSERT INTO portfolio_project (title, category, client, description, video_file, video_url, thumbnail, is_featured, "order", created_at, updated_at)
                VALUES (?, ?, ?, ?, '', ?, ?, 1, ?, ?, ?);
            """, (item["title"], item["category"], item["client"], item["description"], item["video_url"], item["thumb_file"], idx, now_str, now_str))
            print(f"Inserted: {item['title']} (Order {idx})")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    sync_db()
