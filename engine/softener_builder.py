import os
import json
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/water-softener-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6").strip()
CUSTOM_SOFTENER = os.environ.get("CUSTOM_SOFTENER", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_softeners.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (System / Scenario Name, Nominal Grains, Resin Cu Ft, Household People, Default Hardness GPG, Default Iron ppm, Flow GPM)
SEED_SOFTENERS = [
    ("Fleck 5600SXT 48,000 Grain Digital Metered Softener", 48000, 1.5, 4, 15, 0.5, 12.0),
    ("Fleck 5600SXT 64,000 Grain Whole-House Softener", 64000, 2.0, 5, 20, 1.0, 15.0),
    ("Fleck 5600SXT 32,000 Grain Compact Water Softener", 32000, 1.0, 2, 12, 0.0, 10.0),
    ("Aquasure Harmony Series 48,000 Grain Water Softener", 48000, 1.5, 4, 16, 0.5, 12.5),
    ("Aquasure Harmony Series 64,000 Grain High-Capacity", 64000, 2.0, 6, 18, 1.0, 15.0),
    ("SpringWell SS1 32,000 Grain Salt-Based Softener", 32000, 1.0, 3, 12, 0.0, 11.0),
    ("SpringWell SS4 48,000 Grain Bluetooth Water Softener", 48000, 1.5, 4, 15, 0.5, 13.0),
    ("SpringWell SS+ 80,000 Grain Large Estate Softener", 80000, 2.5, 7, 22, 1.5, 20.0),
    ("Whirlpool WHES40E 40,000 Grain Demand-Initiated Softener", 40000, 1.25, 4, 14, 0.5, 10.0),
    ("Whirlpool WHES44 44,000 Grain Pro Series Softener", 44000, 1.4, 4, 16, 1.0, 11.0),
    ("Rheem Preferred Platinum 42,000 Grain WiFi Softener", 42000, 1.3, 4, 15, 0.5, 10.5),
    ("GE GXSH40V 40,200 Grain Smart Water Softener", 40000, 1.25, 4, 14, 0.5, 9.5),
    ("Clack WS1 48,000 Grain Pro-Grade 10% Crosslink Softener", 48000, 1.5, 4, 16, 1.0, 15.0),
    ("Clack WS1 64,000 Grain High-Efficiency Well Water Softener", 64000, 2.0, 5, 20, 2.0, 18.0),
    ("Fleck 9100SXT Twin-Tank 48,000 Grain Continuous Softener", 48000, 1.5, 5, 18, 1.0, 14.0),
    ("Fleck 2510SXT 64,000 Grain Heavy-Duty Well Water System", 64000, 2.0, 5, 22, 2.5, 16.0),
    ("AFWFilters Fleck 5600SXT 48K 10% Crosslink Resin System", 48000, 1.5, 4, 15, 0.5, 12.0),
    ("DuraWater Fleck 5600SXT 64,000 Grain Upflow Softener", 64000, 2.0, 5, 18, 1.0, 15.0),
    ("SoftPro Elite 48,000 Grain Upflow High-Efficiency Softener", 48000, 1.5, 4, 16, 0.5, 13.0),
    ("SoftPro IronMaster AIO + 64,000 Grain Well Water Combo", 64000, 2.0, 5, 20, 3.0, 15.0),
    ("WaterBoss 36,400 Grain High-Efficiency Cabinet Softener", 36000, 1.1, 3, 15, 1.5, 10.0),
    ("Morton M30 30,000 Grain Compact Whole-Home Softener", 30000, 1.0, 3, 12, 0.0, 9.0),
    ("Culligan Medallist Series 45,000 Grain Replacement Sizing", 45000, 1.5, 4, 16, 0.5, 12.0),
    ("Kinetico Premier Series Twin-Tank Non-Electric Sizing", 48000, 1.5, 4, 18, 1.0, 14.0),
    ("4-Person Family Home with 15 GPG Hard Water", 48000, 1.5, 4, 15, 0.5, 12.0),
    ("5-Person Household with 20 GPG Very Hard Water", 64000, 2.0, 5, 20, 1.0, 15.0),
    ("6-Person Large Home with 25 GPG Extreme Hard Water", 80000, 2.5, 6, 25, 1.5, 18.0),
    ("Private Well Water with 18 GPG Hardness & 3 ppm Iron", 64000, 2.0, 4, 18, 3.0, 15.0),
    ("Phoenix & Las Vegas Desert Hard Water (19 GPG / 280 ppm)", 64000, 2.0, 4, 19, 0.0, 14.0),
    ("Texas & Midwest Limestone Well Water (22 GPG / 375 ppm)", 64000, 2.0, 4, 22, 1.5, 15.0)
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=48000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_softener_queries():
    """Mengambil kueri model Water Softener & ukuran Grain dari Google Autocomplete US."""
    discovered = []
    seeds = [
        "what size water softener for ",
        "fleck 5600sxt ",
        "aquasure harmony ",
        "water softener salt setting for "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|settings|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        grain_match = re.search(r"(32000|40000|48000|64000|80000|32k|48k|64k|80k)", cleaned, flags=re.IGNORECASE)
                        g_val = 48000
                        if grain_match:
                            raw_g = grain_match.group(1).lower().replace("k", "000")
                            g_val = int(raw_g)
                        cu_ft = round(g_val / 32000.0, 2)
                        discovered.append((cleaned.title(), g_val, cu_ft, 4, 15, 0.5, 12.5))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_softener_data(soft_tuple):
    """Mesin Fisika Ion-Exchange Resin WQA & Dosis Garam (100% bebas gagal)."""
    sys_name, grains, resin_cuft, people, gpg, iron_ppm, flow_gpm = soft_tuple

    # Rumus WQA (Water Quality Association):
    # Pemakaian air = 75 galon/orang/hari.
    # Kompensasi Kesadahan Total (Compensated GPG) = GPG + (Iron ppm * 4)
    comp_gpg = round(gpg + (iron_ppm * 4.0), 1)
    daily_gallons = people * 75
    daily_grains = int(round(daily_gallons * comp_gpg))
    # Target siklus regenerasi optimal = setiap 7 hari (+ 15% reserve capacity)
    weekly_grains_needed = int(round(daily_grains * 7 * 1.15))

    # Dosis garam optimal (High-Efficiency 8 lbs per Cu Ft menghasilkan ~24,000 grains/Cu Ft)
    optimal_salt_lbs_per_regen = round(resin_cuft * 8.0, 1)
    working_capacity_grains = int(round(resin_cuft * 24000))
    days_between_regens = max(3, int(round(working_capacity_grains / max(500, daily_grains))))
    monthly_salt_lbs = int(round((30.0 / days_between_regens) * optimal_salt_lbs_per_regen))
    yearly_40lb_bags = int(round((monthly_salt_lbs * 12) / 40.0))

    return {
        "system_name": sys_name,
        "seo_title": f"{sys_name} Sizing, Salt Dose & GPG Hardness Calculator (2026)",
        "meta_description": f"Calculate exact daily grain load ({daily_grains:,} grains/day), optimal brine salt dosage ({optimal_salt_lbs_per_regen} lbs), regeneration frequency ({days_between_regens} days), and RO pairing for {sys_name}.",
        "specs": {
            "nominal_grains": grains,
            "resin_volume_cuft": resin_cuft,
            "household_people": people,
            "hardness_gpg": gpg,
            "iron_ppm": iron_ppm,
            "service_flow_gpm": flow_gpm,
            "daily_grain_load": daily_grains,
            "optimal_salt_dose_lbs": optimal_salt_lbs_per_regen
        },
        "engineering_verdict": f"For a {people}-person household (~{daily_gallons} gallons/day) with {gpg} GPG water hardness and {iron_ppm} ppm dissolved iron ({comp_gpg} compensated GPG), your daily mineral load is {daily_grains:,} grains/day. The {sys_name} ({grains:,} nominal grains / {resin_cuft} cu. ft. of 8%–10% crosslink cation resin) operating at an efficient 8 lb/cu.ft salt dose ({optimal_salt_lbs_per_regen} lbs per cycle) will regenerate every {days_between_regens} days, consuming roughly {monthly_salt_lbs} lbs of pellet salt per month ({yearly_40lb_bags} bags/year).",
        "hardware_bundle": [
            {
                "badge": f"{grains // 1000}K-Grain Softener",
                "title": f"{sys_name} Digital Metered Whole-House System",
                "price_range": "$569 - $1,199",
                "amazon_query": f"{grains} Grain Whole House Water Softener System Fleck Aquasure",
                "water_note": f"Contains {resin_cuft} cu. ft. of high-capacity ion-exchange resin rated for {flow_gpm} GPM continuous service flow."
            },
            {
                "badge": "20\" Big Blue Pre-Filter",
                "title": "Whole-House 20\" x 4.5\" Dual/Triple Big Blue Sediment & Catalytic Carbon Pre-Filter",
                "price_range": "$179 - $369",
                "amazon_query": "Whole House 20x4.5 Big Blue Sediment Carbon Water Filter System",
                "water_note": "Traps sand, rust, and municipal chlorine/chloramines before they strip crosslink polymer bonds inside your softener resin bed."
            },
            {
                "badge": "Tankless RO Drinking Tap",
                "title": "800 GPD Tankless Under-Sink Reverse Osmosis System with Alkaline Remineralization",
                "price_range": "$249 - $499",
                "amazon_query": "800 GPD Tankless Reverse Osmosis Water Filter System Under Sink",
                "water_note": "Ion-exchange softening adds ~7.5 mg/L of sodium per GPG removed; an under-sink RO system removes 99% of sodium for pure drinking & coffee water."
            },
            {
                "badge": "Resin Cleaner & Test Kit",
                "title": "Pro Liquid Resin Bed Cleaner (1-Gallon Feeder) + Digital TDS & Hach 5-B GPG Test Kit",
                "price_range": "$29 - $64",
                "amazon_query": "Pro Products ResCare Liquid Water Softener Cleaner Hardness Test Kit",
                "water_note": f"Flushes ferric iron fouling from {resin_cuft} cu. ft. resin beads to restore 100% ion-exchange capacity."
            }
        ],
        "calibration_checklist": [
            f"Set your digital control valve capacity to Working Grains ({working_capacity_grains:,} grains at 8 lbs/cu.ft salt) rather than maximum factory {grains:,} nominal grains to save 35% on annual salt consumption.",
            f"Program your Hardness setting to {int(round(comp_gpg))} GPG ({gpg} GPG calcium/magnesium + {int(round(iron_ppm * 4))} GPG compensated for {iron_ppm} ppm ferrous iron).",
            "Verify your Brine Line Flow Control (BLFC) sticker (typically 0.25 GPM or 0.50 GPM, where 1 gallon of water dissolves 3.0 lbs of salt) before entering minutes of Brine Fill.",
            "Install a 5-micron 20\"x4.5\" spun polypropylene sediment pre-filter upstream of the control head to prevent silt from scoring the ceramic/piston seal pack."
        ],
        "faqs": [
            {
                "q": f"How many bags of salt does the {sys_name} use per month?",
                "a": f"With {people} people and {comp_gpg} compensated GPG ({daily_grains:,} grains/day), regenerating every {days_between_regens} days at {optimal_salt_lbs_per_regen} lbs per cycle uses approximately {monthly_salt_lbs} lbs of salt per month—or about {yearly_40lb_bags} standard 40-lb bags per year."
            },
            {
                "q": f"Should I use 8% or 10% crosslink resin for the {sys_name}?",
                "a": f"If you are on chlorinated city water, always choose 10% crosslink cation resin paired with a carbon pre-filter. Chlorine oxidizes standard 8% resin into mush within 4–6 years, causing severe water pressure drops."
            },
            {
                "q": f"Is softened water from the {sys_name} safe to drink?",
                "a": f"Softened water is safe for most adults, but at {gpg} GPG hardness the ion-exchange process adds roughly {int(round(gpg * 7.5))} mg of sodium per liter of water. Water treatment engineers strongly recommend installing an under-sink Reverse Osmosis (RO) faucet at the kitchen sink for drinking and cooking."
            }
        ]
    }


def generate_softener_data(soft_tuple):
    """Memanggil Gemini 2.5 Flash API; jika gagal otomatis memakai Deterministic WQA Resin Engine."""
    if not GEMINI_API_KEY:
        return build_deterministic_softener_data(soft_tuple)

    sys_name, grains, resin_cuft, people, gpg, iron_ppm, flow_gpm = soft_tuple
    comp_gpg = round(gpg + (iron_ppm * 4.0), 1)
    daily_grains = int(round(people * 75 * comp_gpg))
    optimal_salt_lbs = round(resin_cuft * 8.0, 1)

    prompt = f"""
You are a WQA Certified Master Water Specialist (MWS) & Residential Treatment Engineer. Create an accurate 2026 water softener grain sizing, salt dosage, valve programming, and RO filtration guide for: "{sys_name}".
Baseline reference specs: Nominal Capacity={grains} Grains ({resin_cuft} Cu Ft Resin), Household={people} People, Hardness={gpg} GPG, Iron={iron_ppm} ppm, Daily Load={daily_grains} Grains/day, Optimal Salt Dose={optimal_salt_lbs} lbs, Flow Rate={flow_gpm} GPM.
Return ONLY a valid JSON object matching this exact schema:
{{
  "system_name": "{sys_name}",
  "seo_title": "{sys_name} Sizing, Salt Dose & GPG Hardness Calculator (2026)",
  "meta_description": "Calculate exact daily grain load, optimal brine salt dosage, regeneration frequency, and under-sink RO pairing for {sys_name}.",
  "specs": {{
    "nominal_grains": {grains},
    "resin_volume_cuft": {resin_cuft},
    "household_people": {people},
    "hardness_gpg": {gpg},
    "iron_ppm": {iron_ppm},
    "service_flow_gpm": {flow_gpm},
    "daily_grain_load": {daily_grains},
    "optimal_salt_dose_lbs": {optimal_salt_lbs}
  }},
  "engineering_verdict": "3-sentence technical summary stating daily gallons, compensated GPG, daily grain load, working capacity at 8 lb/cu.ft salt dose, and days between regenerations.",
  "hardware_bundle": [
    {{
      "badge": "Whole-House Softener",
      "title": "{sys_name}",
      "price_range": "$569 - $1,199",
      "amazon_query": "{grains} Grain Whole House Water Softener System",
      "water_note": "1-sentence resin crosslink and GPM flow note"
    }},
    {{
      "badge": "Big Blue Pre-Filter",
      "title": "20x4.5 Whole-House Sediment & Catalytic Carbon Pre-Filter System",
      "price_range": "$179 - $359",
      "amazon_query": "20x4.5 Big Blue Whole House Water Filter System",
      "water_note": "1-sentence chlorine and sediment resin protection note"
    }},
    {{
      "badge": "Tankless Under-Sink RO",
      "title": "800 GPD Tankless Reverse Osmosis Under-Sink Drinking Water Filter",
      "price_range": "$249 - $499",
      "amazon_query": "800 GPD Tankless Reverse Osmosis System Under Sink",
      "water_note": "1-sentence sodium removal note for drinking water"
    }},
    {{
      "badge": "Resin Cleaner & GPG Kit",
      "title": "Pro Liquid Resin Bed Cleaner + Drop-Count GPG Water Hardness Test Kit",
      "price_range": "$29 - $64",
      "amazon_query": "ResCare Water Softener Resin Cleaner Hardness Test Kit",
      "water_note": "1-sentence iron fouling removal note"
    }}
  ],
  "calibration_checklist": [
    "Step 1 regarding Working Capacity vs Nominal Grain programming",
    "Step 2 regarding Compensated Hardness (GPG + 4x Iron ppm)",
    "Step 3 regarding BLFC brine fill minutes calculation",
    "Step 4 regarding sediment/carbon pre-filtration"
  ],
  "faqs": [
    {{"q": "How many bags of salt does the {sys_name} use per month?", "a": "Exact lbs per month and 40-lb bags per year."}},
    {{"q": "What settings should I program on the {sys_name} valve?", "a": "Exact hardness, working grains, reserve %, and brine fill settings."}},
    {{"q": "Do I need a Reverse Osmosis system with the {sys_name}?", "a": "Direct technical answer explaining sodium ion exchange per GPG."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{sys_name}': {e}")

    return build_deterministic_softener_data(soft_tuple)


def build_softener_html_page(data, slug, mon_cfg):
    sys_name = data.get("system_name", "Whole-House Water Softener")
    sp = data.get("specs", {})
    grains = int(safe_float(sp.get("nominal_grains", 48000), 48000))
    resin_cuft = round(safe_float(sp.get("resin_volume_cuft", round(grains / 32000.0, 2)), 1.5), 2)
    people = int(safe_float(sp.get("household_people", 4), 4))
    gpg = int(safe_float(sp.get("hardness_gpg", 15), 15))
    iron_ppm = round(safe_float(sp.get("iron_ppm", 0.5), 0.5), 1)
    flow_gpm = round(safe_float(sp.get("service_flow_gpm", 12.0), 12.0), 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Whole+House+Water+Softener+System+48000+Grain"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{sys_name} Grain Capacity & Salt Setting Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Water Softener System")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-indigo-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Water System')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$179+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🚰 {item.get('water_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Resin Capacity vs Salt Efficiency Matrix Table
    resin_tiers = [
        ("32,000 Grain (1.0 Cu Ft)", "9\" × 48\" Tank", "24,000 Grains @ 8 lbs Salt", "6.0 lbs (2.0 Gal Brine)", "10 GPM"),
        ("40,000 Grain (1.25 Cu Ft)", "10\" × 44\" Tank", "30,000 Grains @ 10 lbs Salt", "7.5 lbs (2.5 Gal Brine)", "11 GPM"),
        ("48,000 Grain (1.5 Cu Ft)", "10\" × 54\" Tank", "36,000 Grains @ 12 lbs Salt", "9.0 lbs (3.0 Gal Brine)", "12.5 GPM"),
        ("64,000 Grain (2.0 Cu Ft)", "12\" × 52\" Tank", "48,000 Grains @ 16 lbs Salt", "12.0 lbs (4.0 Gal Brine)", "15 GPM"),
        ("80,000 Grain (2.5 Cu Ft)", "13\" × 54\" Tank", "60,000 Grains @ 20 lbs Salt", "15.0 lbs (5.0 Gal Brine)", "18.5 GPM")
    ]
    matrix_rows_html = ""
    for cap_s, tank_s, work_s, low_s, gpm_s in resin_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{cap_s}</td>
          <td class="py-3 px-4 text-slate-300">{tank_s}</td>
          <td class="py-3 px-4 font-bold text-indigo-400">{work_s}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{low_s}</td>
          <td class="py-3 px-4 text-xs text-slate-400">{gpm_s} Peak</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("calibration_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-indigo-500 rounded cursor-pointer soft-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>Valve Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', sys_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', sys_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-indigo-500 text-white px-2 py-0.5 rounded font-black">GRAIN</span>SoftenerIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Water Softeners →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-indigo-500 text-white px-3 py-1 rounded-full">{grains:,} Grains ({resin_cuft} Cu Ft)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Flow Rate: {flow_gpm} GPM</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">Baseline: {people} People @ {gpg} GPG + {iron_ppm} ppm Iron</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', sys_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-indigo-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>WQA Master Water Specialist Verdict:</strong> {data.get('engineering_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE GRAIN CAPACITY, SALT DOSE & REGENERATION CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {sys_name} Grain Load & Salt Dose Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your household size, water hardness (GPG), and dissolved iron (ppm) to compute exact daily grain load, required resin capacity, and monthly salt usage.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="peopleSlider" class="text-slate-300">Number of People in Household (75 Gal/Person/Day)</label>
              <span class="text-indigo-400 font-bold"><span id="peopleVal">{people}</span> People</span>
            </div>
            <input id="peopleSlider" type="range" min="1" max="10" step="1" value="{people}" class="w-full accent-indigo-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="gpgSlider" class="text-slate-300">Water Hardness Level (GPG — 1 GPG = 17.1 ppm)</label>
              <span class="text-indigo-400 font-bold"><span id="gpgVal">{gpg}</span> GPG</span>
            </div>
            <input id="gpgSlider" type="range" min="3" max="45" step="1" value="{gpg}" class="w-full accent-indigo-500 cursor-pointer">
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="ironSlider" class="text-slate-300">Clear-Water Ferrous Iron (ppm — Adds +4 GPG per ppm)</label>
              <span class="text-indigo-400 font-bold"><span id="ironVal">{iron_ppm}</span> ppm</span>
            </div>
            <input id="ironSlider" type="range" min="0" max="8" step="0.5" value="{iron_ppm}" class="w-full accent-indigo-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-indigo-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-indigo-400 font-bold">Required System Size</span>
            <div id="recGrainOut" class="text-xl sm:text-2xl font-black text-white mt-1">{grains:,} Grain</div>
            <p id="dailyGrainOut" class="text-xs text-slate-400 mt-1">Load: 4,500 Grains/Day</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Salt Usage & Cycle</span>
            <div class="text-xl sm:text-2xl font-black text-emerald-400 mt-1"><span id="saltBagsOut">9</span> <span class="text-xs font-normal text-slate-400">Bags/yr</span></div>
            <p id="regenDaysOut" class="text-xs text-slate-400 mt-1">Regen Every 7 Days</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="softenerAdviceBanner" class="text-sm text-indigo-100 font-medium"></div>
        <a id="dynamicSoftenerBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Water Softener on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {sys_name} Pre-Filter & Drinking Water Bundle</h2>
        <span class="text-xs text-slate-400">NSF/ANSI-44 & WQA Gold Seal Components</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- RESIN CAPACITY & SALT EFFICIENCY TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Water Softener Grain Capacity, Resin Volume & Brine Salt Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">System Rating (Resin)</th>
              <th class="py-3.5 px-4">Mineral Tank Size</th>
              <th class="py-3.5 px-4 text-indigo-400">Working Capacity (8 lb/ft³)</th>
              <th class="py-3.5 px-4 text-emerald-400">Low-Salt Mode (6 lb/ft³)</th>
              <th class="py-3.5 px-4">Service Flow</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- VALVE PROGRAMMING CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Digital Control Valve (SXT / Clack) Programming Checklist</h2>
        <span id="softBadge" class="text-xs font-bold bg-slate-800 text-indigo-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({sys_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} GrainSoftenerIndex. Independent WQA Water Softener & Filtration Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const peopleSlider = document.getElementById('peopleSlider');
    const gpgSlider = document.getElementById('gpgSlider');
    const ironSlider = document.getElementById('ironSlider');
    const peopleVal = document.getElementById('peopleVal');
    const gpgVal = document.getElementById('gpgVal');
    const ironVal = document.getElementById('ironVal');
    const recGrainOut = document.getElementById('recGrainOut');
    const dailyGrainOut = document.getElementById('dailyGrainOut');
    const saltBagsOut = document.getElementById('saltBagsOut');
    const regenDaysOut = document.getElementById('regenDaysOut');
    const softenerAdviceBanner = document.getElementById('softenerAdviceBanner');
    const dynamicSoftenerBtn = document.getElementById('dynamicSoftenerBtn');

    function recalculateSoftener() {{
      const pCount = parseInt(peopleSlider.value, 10);
      const rawGpg = parseInt(gpgSlider.value, 10);
      const ironPpm = parseFloat(ironSlider.value);

      peopleVal.textContent = pCount;
      gpgVal.textContent = rawGpg;
      ironVal.textContent = ironPpm.toFixed(1);

      const compGpg = Math.round(rawGpg + (ironPpm * 4.0));
      const dailyGals = pCount * 75;
      const dailyGrains = dailyGals * compGpg;
      const target7DayGrains = dailyGrains * 7 * 1.15;

      let nominalSize = 32000;
      let cuFt = 1.0;
      if (target7DayGrains <= 24000) {{
        nominalSize = 32000;
        cuFt = 1.0;
      }} else if (target7DayGrains <= 36000) {{
        nominalSize = 48000;
        cuFt = 1.5;
      }} else if (target7DayGrains <= 48000) {{
        nominalSize = 64000;
        cuFt = 2.0;
      }} else {{
        nominalSize = 80000;
        cuFt = 2.5;
      }}

      const workCap = cuFt * 24000;
      const saltPerRegen = cuFt * 8.0;
      const regenDays = Math.max(3, Math.round(workCap / Math.max(400, dailyGrains)));
      const yearlyLbs = (365.0 / regenDays) * saltPerRegen;
      const bags40 = Math.ceil(yearlyLbs / 40.0);

      recGrainOut.textContent = `${{nominalSize.toLocaleString()}} Grain`;
      dailyGrainOut.textContent = `Load: ${{dailyGrains.toLocaleString()}} Gr/Day (${{compGpg}} GPG)`;
      saltBagsOut.textContent = bags40;
      regenDaysOut.textContent = `Regen Every ${{regenDays}} Days (${{saltPerRegen}} lbs)`;

      softenerAdviceBanner.innerHTML = `🚰 <strong>Valve Programming Spec:</strong> Install a <strong>${{nominalSize.toLocaleString()}} Grain (${{cuFt}} Cu Ft) System</strong>. Program Hardness = <strong>${{compGpg}} GPG</strong>, Capacity = <strong>${{workCap.toLocaleString()}} Grains</strong>, and Brine Salt = <strong>${{saltPerRegen}} lbs</strong>.`;
      dynamicSoftenerBtn.href = `https://${{amzDomain}}/s?k=${{nominalSize}}+Grain+Whole+House+Water+Softener+System&tag=${{amzTag}}`;
    }}

    peopleSlider.addEventListener('input', recalculateSoftener);
    gpgSlider.addEventListener('input', recalculateSoftener);
    ironSlider.addEventListener('input', recalculateSoftener);
    recalculateSoftener();

    const checks = document.querySelectorAll('.soft-check');
    const badge = document.getElementById('softBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Whole+House+Water+Softener+System+48000+Grain"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-indigo-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-indigo-500 text-white px-2.5 py-0.5 rounded">{item.get('grains', 48000):,} Grain ({item.get('cuft', 1.5)} ft³)</span>
            <span class="text-xs text-slate-400">{item.get('flow_gpm', 12.0)} GPM Flow</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-indigo-400 transition">{item['system_name']} Calculator</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-indigo-400">Calculate Grain Size & Salt Dose →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GrainSoftenerIndex — Water Softener Grain Capacity, GPG Hardness & Salt Calculator (2026)</title>
  <meta name="description" content="Calculate exact water softener grain capacity (32K, 48K, 64K, 80K), Fleck 5600SXT & Clack WS1 salt settings, well water iron compensation, and RO sizing.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="GrainSoftenerIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-indigo-500 text-white px-2 py-0.5 rounded font-black">GRAIN</span>SoftenerIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Water Softeners →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Water Softener Grain Capacity & Salt Dosage Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your water softener system or household hardness profile below to calculate daily grain load, optimal brine salt dosage (lbs), and valve programming specs.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search model or hardness (e.g. Fleck 5600SXT, Aquasure 64000, SpringWell, Clack WS1, Well Water Iron...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-indigo-500">
      </div>
    </div>

    <div id="softGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} GrainSoftenerIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('softGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>GrainSoftenerIndex WQA Water Softener Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Whole-House Water Softener Grain Capacity, GPG Hardness & Salt Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_SOFTENER:
        candidates.append((CUSTOM_SOFTENER.strip(), 48000, 1.5, 4, 15, 0.5, 12.5))
    candidates.extend(SEED_SOFTENERS)
    candidates.extend(discover_google_softener_queries())

    new_urls = []
    count = 0

    for soft_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        sys_name = soft_tuple[0]
        slug = slugify(f"{sys_name}-grain-salt-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating water softener grain & salt calculator for: {sys_name}...")
        try:
            data = generate_softener_data(soft_tuple)
            build_softener_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "system_name": data.get("system_name", sys_name),
                "slug": slug,
                "title": data.get("seo_title", f"{sys_name} Grain Calculator"),
                "description": data.get("meta_description", ""),
                "grains": int(safe_float(sp.get("nominal_grains", soft_tuple[1]), soft_tuple[1])),
                "cuft": round(safe_float(sp.get("resin_volume_cuft", soft_tuple[2]), soft_tuple[2]), 2),
                "flow_gpm": round(safe_float(sp.get("service_flow_gpm", soft_tuple[6]), soft_tuple[6]), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {sys_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new water softener grain calculator pages.")


if __name__ == "__main__":
    main()
