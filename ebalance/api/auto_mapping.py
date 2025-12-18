# -*- coding: utf-8 -*-
# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false

"""
MOF Account Auto-Mapping Module (Optimized v1.1)

Provides intelligent auto-mapping between ERPNext Chart of Accounts
and Mongolian Standard MOF Account Codes (НББОУС).

Performance Optimizations:
- Precompiled keyword patterns
- Batch database operations
- Cached lookups
- Single-pass account processing

Matching Strategy:
1. Exact account number match (1111 -> 1111)
2. Account number prefix match (111x -> 1110 group)
3. Name similarity matching using keywords
4. Root type + name keyword combination
5. Manual mapping for special cases
"""

from functools import lru_cache

import frappe
from frappe import _

# Keyword mappings from English/Mongolian terms to MOF codes
ACCOUNT_KEYWORDS = {
    # Cash and Cash Equivalents (1110-1114)
    "1111": ["cash on hand", "petty cash", "касс", "бэлэн мөнгө", "кассан дахь"],
    "1112": ["bank", "checking", "current account", "mnt", "төгрөг", "харилцах данс"],
    "1113": ["foreign currency", "usd", "eur", "cny", "гадаад валют"],
    "1114": ["restricted cash", "escrow", "хязгаарлагдсан"],
    "1120": ["short-term deposit", "savings", "хадгаламж", "богино хугацаат"],

    # Receivables (1200-1205)
    "1200": ["receivables", "авлага"],
    "1201": ["trade receivable", "domestic receivable", "customer receivable", "debtor", "дотоодын", "харилцагчаас авах"],
    "1202": ["foreign receivable", "export receivable", "гадаадын"],
    "1203": ["notes receivable", "вексел"],
    "1204": ["employee receivable", "staff loan", "ажилтнуудаас"],
    "1205": ["allowance", "doubtful", "bad debt reserve", "нөөц"],

    # Inventory (1300-1306)
    "1300": ["inventory", "stock", "бараа материал"],
    "1301": ["raw material", "supplies", "түүхий эд", "материал"],
    "1302": ["work in progress", "wip", "дуусаагүй үйлдвэрлэл"],
    "1303": ["finished goods", "бэлэн бүтээгдэхүүн"],
    "1304": ["merchandise", "goods for resale", "бараа бүтээгдэхүүн"],
    "1305": ["goods in transit", "замд"],
    "1306": ["inventory write-down", "obsolete", "бууралт"],

    # Other Current Assets (1400-1470)
    "1400": ["other current asset", "бусад эргэлтийн"],
    "1410": ["short-term investment", "санхүүгийн хөрөнгө"],
    "1420": ["short-term loan issued", "loan receivable", "зээл олгосон"],
    "1430": ["vat receivable", "input vat", "нөат авлага"],
    "1440": ["excise receivable", "онцгой албан татвар"],
    "1450": ["other tax receivable", "бусад татвар"],
    "1460": ["prepaid expense", "prepayment", "урьдчилж төлсөн"],
    "1470": ["advance to supplier", "supplier advance", "урьдчилгаа"],
    "1500": ["held for sale", "disposal group", "борлуулж буй"],
    "1600": ["biological current", "биологийн"],
    "1700": ["other current", "miscellaneous", "ангилагдаагүй"],

    # Property, Plant & Equipment (1800-1829)
    "1800": ["ppe", "fixed asset", "property plant equipment", "үндсэн хөрөнгө"],
    "1801": ["land", "газар"],
    "1802": ["building", "structure", "барилга", "байгууламж"],
    "1803": ["machinery", "equipment", "machine", "машин", "тоног төхөөрөмж"],
    "1804": ["vehicle", "car", "truck", "тээврийн хэрэгсэл"],
    "1805": ["mining equipment", "specialized", "уул уурхай", "тусгай"],
    "1810": ["construction in progress", "cwip", "баригдаж буй"],
    "1820": ["accumulated depreciation building", "building depreciation", "барилгын элэгдэл"],
    "1821": ["accumulated depreciation machinery", "equipment depreciation", "машин элэгдэл"],
    "1822": ["accumulated depreciation vehicle", "vehicle depreciation", "тээврийн элэгдэл"],
    "1829": ["accumulated depreciation other", "other depreciation", "бусад элэгдэл"],

    # Intangible Assets (1900-1910)
    "1900": ["intangible", "биет бус хөрөнгө"],
    "1901": ["software", "license", "программ хангамж"],
    "1902": ["license", "right", "patent", "лиценз", "эрх"],
    "1903": ["goodwill", "гүүдвилл"],
    "1910": ["amortization", "intangible depreciation", "биет бус элэгдэл"],

    # Long-term investments (1950-1990)
    "1950": ["long-term investment", "урт хугацаат хөрөнгө оруулалт"],
    "1951": ["equity investment", "shares investment", "хувьцаа"],
    "1952": ["debt investment", "bond investment", "өрийн хэрэгсэл"],
    "1960": ["long-term loan issued", "урт хугацаат зээл"],
    "1970": ["biological non-current", "биологийн урт"],
    "1980": ["deferred tax asset", "dta", "хойшлогдсон татвар хөрөнгө"],
    "1990": ["other non-current", "бусад эргэлтийн бус"],

    # Current Liabilities (2100-2330)
    "2110": ["trade payable", "accounts payable", "supplier payable", "creditor", "нийлүүлэгчид"],
    "2120": ["short-term bank loan", "bank overdraft", "банкны зээл богино"],
    "2130": ["current portion", "long-term due", "богино хугацаат хэсэг"],
    "2140": ["related party borrowing", "intercompany loan", "холбогдох этгээд"],
    "2150": ["advance from customer", "deferred revenue", "урьдчилгаа авсан"],
    "2160": ["salary payable", "wages payable", "цалин өглөг"],
    "2170": ["social insurance payable", "нийгмийн даатгал"],
    "2180": ["personal income tax payable", "pit payable", "хувийн орлогын татвар"],
    "2190": ["other payable", "accrued expense", "бусад өглөг"],
    "2200": ["taxes payable", "татварын өглөг"],
    "2210": ["vat payable", "output vat", "нөат өглөг"],
    "2220": ["excise payable", "онцгой албан татвар өглөг"],
    "2230": ["corporate income tax", "cit payable", "ааноат"],
    "2240": ["customs duty", "import duty", "гаалийн"],
    "2250": ["environmental fee", "байгаль орчин"],
    "2300": ["provision current", "резерв"],
    "2310": ["provision bonus", "vacation accrual", "шагнал", "амралт"],
    "2320": ["warranty provision", "баталгаат"],
    "2330": ["tax provision", "penalty provision", "торгууль"],

    # Non-current Liabilities (2400-2490)
    "2400": ["non-current liability", "урт хугацаат өр"],
    "2410": ["long-term bank loan", "урт хугацаат банкны зээл"],
    "2420": ["bonds issued", "bond payable", "гаргасан бонд"],
    "2430": ["lease liability", "finance lease", "түрээс"],
    "2440": ["related party long-term", "холбогдох урт"],
    "2450": ["deferred tax liability", "dtl", "хойшлогдсон татвар өр"],
    "2460": ["decommissioning", "asset retirement", "нөхөн сэргээлт"],
    "2490": ["other non-current liability", "бусад урт хугацаат"],

    # Equity (3000-3600)
    "3100": ["share capital", "capital stock", "хувь нийлүүлсэн"],
    "3110": ["ordinary share", "common stock", "энгийн хувьцаа"],
    "3120": ["preferred share", "preference share", "давуу эрхтэй"],
    "3200": ["additional paid-in", "share premium", "давхардуулан"],
    "3300": ["retained earnings", "accumulated profit", "хуримтлагдсан ашиг"],
    "3310": ["current year profit", "net income", "тайлант жилийн"],
    "3400": ["reserve", "нөөцийн сан"],
    "3410": ["legal reserve", "statutory reserve", "хуулийн"],
    "3420": ["other reserve", "бусад нөөц"],
    "3500": ["treasury share", "share buyback", "дахин худалдаж"],
    "3600": ["non-controlling interest", "minority interest", "хяналтын бус"],

    # Revenue (4000-4400)
    "4100": ["sales revenue excise", "онцгой албан татвартай бараа"],
    "4110": ["sales revenue", "revenue from goods", "борлуулалтын орлого"],
    "4120": ["service revenue", "үйлчилгээний орлого"],
    "4130": ["export revenue", "экспорт"],
    "4140": ["domestic revenue", "дотоодын"],
    "4200": ["other operating income", "үйл ажиллагааны бусад"],
    "4210": ["subsidy", "grant income", "татаас"],
    "4220": ["gain on disposal", "ppe disposal gain", "борлуулалтын олз"],
    "4230": ["penalty income", "fine income", "торгууль орлого"],
    "4300": ["finance income", "санхүүгийн орлого"],
    "4310": ["interest income", "хүүгийн орлого"],
    "4320": ["forex gain", "exchange gain", "ханшийн ашиг"],
    "4330": ["fair value gain", "revaluation gain", "үнэлгээний олз"],
    "4400": ["other non-operating income", "бусад үйл ажиллагааны бус"],

    # Cost of Sales (5000-5130)
    "5100": ["cost of goods sold excise", "онцгой албан татвартай өртөг"],
    "5110": ["cost of goods sold", "cogs", "борлуулсан барааны өртөг"],
    "5120": ["cost of services", "үйлчилгээний өртөг"],
    "5130": ["cost of resale goods", "дахин борлуулах"],

    # Operating Expenses (6000-6800)
    "6100": ["selling expense", "distribution cost", "борлуулалт"],
    "6110": ["advertising", "marketing", "сурталчилгаа"],
    "6120": ["transportation", "logistics", "тээвэр"],
    "6130": ["sales salary", "commission", "борлуулалтын цалин"],
    "6200": ["administrative expense", "general expense", "удирдлагын"],
    "6210": ["office salary", "admin salary", "оффис цалин"],
    "6220": ["social insurance expense", "ндш"],
    "6230": ["rent expense", "office rent", "түрээс"],
    "6240": ["utilities", "electricity", "коммунал"],
    "6250": ["travel expense", "business travel", "томилолт"],
    "6260": ["professional fee", "consulting fee", "audit fee", "мэргэжлийн"],
    "6300": ["depreciation expense", "элэгдлийн зардал"],
    "6310": ["depreciation ppe", "үндсэн хөрөнгийн элэгдэл"],
    "6320": ["amortization intangible", "биет бус элэгдэл"],
    "6400": ["other tax expense", "бусад татвар"],
    "6410": ["property tax", "хөрөнгийн татвар"],
    "6420": ["vehicle tax", "road fee", "авто зам"],
    "6500": ["repair", "maintenance", "засвар"],
    "6600": ["bad debt expense", "авлагын алдагдал"],
    "6700": ["inventory write-down", "бараа бууралт"],
    "6800": ["impairment", "хөрөнгийн бууралт"],

    # Finance Costs (7000-7300)
    "7100": ["interest expense", "хүүгийн зардал"],
    "7200": ["forex loss", "exchange loss", "ханшийн алдагдал"],
    "7300": ["bank fee", "bank charge", "банкны шимтгэл"],

    # Other Expenses (8000-8300)
    "8100": ["loss on disposal", "ppe disposal loss", "борлуулалтын алдагдал"],
    "8200": ["penalty expense", "fine expense", "торгууль зардал"],
    "8300": ["charity", "donation", "sponsorship", "буцалтгүй тусламж"],

    # Tax (9000-9300)
    "9100": ["current tax expense", "cit expense", "тухайн үеийн татвар"],
    "9200": ["deferred tax expense", "хойшлогдсон татвар"],
    "9300": ["excise tax expense", "онцгой албан татвар зардал"],
}

# Root type to MOF account range mapping
ROOT_TYPE_RANGES: dict[str, list[str]] = {
    "Asset": ["1"],
    "Liability": ["2"],
    "Equity": ["3"],
    "Income": ["4"],
    "Expense": ["5", "6", "7", "8", "9"]
}

# Precompiled keyword data for fast lookup
_KEYWORD_CACHE: dict[str, tuple[set[str], int]] = {}
_MOF_CODES_BY_ROOT: dict[str, list[str]] = {}


def _init_keyword_cache():
    """Initialize precompiled keyword data structures"""
    global _KEYWORD_CACHE, _MOF_CODES_BY_ROOT

    if _KEYWORD_CACHE:
        return  # Already initialized

    # Build keyword cache with lowercase keywords and word counts
    for mof_code, keywords in ACCOUNT_KEYWORDS.items():
        keyword_set = set()
        max_words = 0
        for kw in keywords:
            kw_lower = kw.lower()
            keyword_set.add(kw_lower)
            max_words = max(max_words, len(kw.split()))
        _KEYWORD_CACHE[mof_code] = (keyword_set, max_words)

    # Build MOF codes by root type for fast filtering
    for mof_code in ACCOUNT_KEYWORDS.keys():
        prefix = mof_code[0]
        for root_type, ranges in ROOT_TYPE_RANGES.items():
            if prefix in ranges:
                if root_type not in _MOF_CODES_BY_ROOT:
                    _MOF_CODES_BY_ROOT[root_type] = []
                _MOF_CODES_BY_ROOT[root_type].append(mof_code)
                break


@lru_cache(maxsize=1000)
def _get_existing_mof_codes() -> frozenset:
    """Get set of existing MOF codes (cached)"""
    codes = frappe.get_all("MOF Account Mapping", pluck="name")
    return frozenset(codes)


@lru_cache(maxsize=5000)
def _normalize_text(text: str) -> str:
    """Normalize text for matching (cached)"""
    return text.lower().strip()


def auto_map_accounts(company=None, dry_run=False):
    """
    Auto-map ERPNext accounts to MOF codes (Optimized).

    Performance improvements:
    - Single batch query for all accounts
    - Precompiled keyword patterns
    - Batch insert operations
    - Cached MOF code lookups

    Args:
        company: Company name (optional, maps all companies if None)
        dry_run: If True, only return suggestions without saving

    Returns:
        dict: Mapping results with matched, unmatched, and suggestions
    """
    # Initialize keyword cache
    _init_keyword_cache()

    results = {
        "matched": [],
        "unmatched": [],
        "suggestions": [],
        "errors": []
    }

    # Get all ERPNext accounts in single query
    filters = {"is_group": 0}  # Only leaf accounts
    if company:
        filters["company"] = company

    accounts = frappe.get_all(
        "Account",
        filters=filters,
        fields=["name", "account_number", "account_name", "root_type", "company"],
        order_by="account_number, name"
    )

    # Preload existing MOF codes for fast lookup
    existing_mof_codes = _get_existing_mof_codes()

    # Preload existing mappings to avoid duplicates
    existing_mappings = set()
    if not dry_run:
        existing_items = frappe.get_all(
            "MOF Account Mapping Item",
            fields=["parent", "account"]
        )
        existing_mappings = {(item.parent, item.account) for item in existing_items}

    # Batch processing
    batch_inserts = []  # [(mof_code, account_name), ...]

    for account in accounts:
        try:
            mof_code = find_best_mof_match_fast(account, existing_mof_codes)

            if mof_code:
                match_result = {
                    "account": account.name,
                    "account_number": account.account_number,
                    "account_name": account.account_name,
                    "mof_code": mof_code,
                    "root_type": account.root_type
                }

                if not dry_run and (mof_code, account.name) not in existing_mappings:
                    batch_inserts.append((mof_code, account.name))

                results["matched"].append(match_result)
            else:
                results["unmatched"].append({
                    "account": account.name,
                    "account_number": account.account_number,
                    "account_name": account.account_name,
                    "root_type": account.root_type,
                    "suggestions": get_suggestions_fast(account, existing_mof_codes)
                })

        except Exception as e:
            results["errors"].append({
                "account": account.name,
                "error": str(e)
            })

    # Batch insert mappings
    if batch_inserts:
        _batch_add_mappings(batch_inserts)

    return results


def find_best_mof_match_fast(account, existing_mof_codes: frozenset) -> str | None:
    """
    Find the best MOF code match (optimized version).

    Args:
        account: ERPNext Account dict
        existing_mof_codes: Set of existing MOF codes

    Returns:
        str: MOF code or None
    """
    # Strategy 1: Exact account number match
    if account.account_number:
        if account.account_number in existing_mof_codes:
            return account.account_number

    # Strategy 2: Account number prefix match (4 digits)
    if account.account_number and len(account.account_number) >= 4:
        prefix = account.account_number[:4]
        if prefix in existing_mof_codes:
            return prefix

    # Strategy 3: Optimized keyword matching
    account_text = _normalize_text(account.account_name or "")
    if not account_text:
        return None

    # Get compatible MOF codes based on root type
    compatible_codes = _MOF_CODES_BY_ROOT.get(account.root_type, list(ACCOUNT_KEYWORDS.keys()))

    best_match = None
    best_score = 0

    for mof_code in compatible_codes:
        if mof_code not in existing_mof_codes:
            continue

        keyword_data = _KEYWORD_CACHE.get(mof_code)
        if not keyword_data:
            continue

        keyword_set, max_words = keyword_data
        score = _calculate_keyword_score_fast(account_text, keyword_set, max_words)

        if score > best_score:
            best_score = score
            best_match = mof_code

    # Only return if confidence is high enough
    if best_score >= 2:
        return best_match

    return None


def find_best_mof_match(account):
    """
    Find the best MOF code match for an ERPNext account.
    (Legacy method - use find_best_mof_match_fast for better performance)

    Args:
        account: ERPNext Account dict

    Returns:
        str: MOF code or None
    """
    _init_keyword_cache()
    existing_mof_codes = _get_existing_mof_codes()
    return find_best_mof_match_fast(account, existing_mof_codes)


def _calculate_keyword_score_fast(text: str, keyword_set: set[str], max_words: int) -> int:
    """Calculate keyword match score (optimized)"""
    score = 0
    for keyword in keyword_set:
        if keyword in text:
            # Longer keywords (more words) get higher scores
            score += len(keyword.split())
    return score


def is_root_type_compatible(root_type, mof_code):
    """Check if MOF code is compatible with ERPNext root type"""
    if not root_type or not mof_code:
        return True

    mof_prefix = mof_code[0]
    expected_ranges = ROOT_TYPE_RANGES.get(root_type, [])

    return mof_prefix in expected_ranges


def calculate_keyword_score(text, keywords):
    """Calculate matching score based on keywords (legacy)"""
    score = 0
    text_lower = text.lower()

    for keyword in keywords:
        if keyword.lower() in text_lower:
            # Longer keywords get higher scores
            score += len(keyword.split())

    return score


def get_suggestions_fast(account, existing_mof_codes: frozenset) -> list[dict]:
    """Get MOF code suggestions (optimized version)"""
    suggestions = []
    account_text = _normalize_text(account.account_name or "")

    if not account_text:
        return suggestions

    # Get compatible MOF codes based on root type
    compatible_codes = _MOF_CODES_BY_ROOT.get(account.root_type, list(ACCOUNT_KEYWORDS.keys()))

    for mof_code in compatible_codes:
        if mof_code not in existing_mof_codes:
            continue

        keyword_data = _KEYWORD_CACHE.get(mof_code)
        if not keyword_data:
            continue

        keyword_set, max_words = keyword_data
        score = _calculate_keyword_score_fast(account_text, keyword_set, max_words)

        if score > 0:
            suggestions.append({
                "mof_code": mof_code,
                "score": score
            })

    # Sort by score descending and return top 5
    suggestions.sort(key=lambda x: x["score"], reverse=True)

    # Enrich top 5 with MOF names (batch query)
    top_codes = [s["mof_code"] for s in suggestions[:5]]
    if top_codes:
        mof_docs = frappe.get_all(
            "MOF Account Mapping",
            filters={"name": ("in", top_codes)},
            fields=["name", "mof_account_name", "mof_account_name_mn"]
        )
        mof_map = {d.name: d for d in mof_docs}

        for s in suggestions[:5]:
            doc = mof_map.get(s["mof_code"])
            if doc:
                s["mof_name"] = doc.mof_account_name
                s["mof_name_mn"] = doc.mof_account_name_mn

    return suggestions[:5]


def get_suggestions(account):
    """Get MOF code suggestions for an unmatched account (legacy)"""
    _init_keyword_cache()
    existing_mof_codes = _get_existing_mof_codes()
    return get_suggestions_fast(account, existing_mof_codes)


def _batch_add_mappings(mappings: list[tuple[str, str]]):
    """Batch add account mappings"""
    if not mappings:
        return

    # Group by MOF code
    by_mof_code: dict[str, list[str]] = {}
    for mof_code, account_name in mappings:
        if mof_code not in by_mof_code:
            by_mof_code[mof_code] = []
        by_mof_code[mof_code].append(account_name)

    # Update each MOF Account Mapping
    for mof_code, accounts in by_mof_code.items():
        try:
            doc = frappe.get_doc("MOF Account Mapping", mof_code)
            for account_name in accounts:
                doc.append("accounts", {"account": account_name})
            doc.auto_mapped = 1
            doc.save(ignore_permissions=True)
        except Exception:
            pass

    frappe.db.commit()

    # Clear cache
    _get_existing_mof_codes.cache_clear()


def add_account_to_mapping(mof_code, account_name):
    """Add an ERPNext account to MOF Account Mapping"""
    if not frappe.db.exists("MOF Account Mapping", mof_code):
        return False

    # Check if already mapped
    existing = frappe.db.exists(
        "MOF Account Mapping Item",
        {"parent": mof_code, "account": account_name}
    )

    if existing:
        return False

    doc = frappe.get_doc("MOF Account Mapping", mof_code)
    doc.append("accounts", {
        "account": account_name
    })
    doc.auto_mapped = 1
    doc.save(ignore_permissions=True)

    return True


@frappe.whitelist()
def run_auto_mapping(company=None, dry_run=True):
    """
    Whitelisted method to run auto-mapping.

    Args:
        company: Company name (optional)
        dry_run: If "1" or True, only preview without saving
    """
    dry_run = dry_run in [True, "1", "true", "True"]

    results = auto_map_accounts(company, dry_run)

    if dry_run:
        frappe.msgprint(
            _("Preview: {0} accounts can be auto-mapped, {1} need manual review").format(
                len(results["matched"]),
                len(results["unmatched"])
            ),
            title=_("Auto-Mapping Preview"),
            indicator="blue"
        )
    else:
        frappe.msgprint(
            _("Auto-mapped {0} accounts. {1} accounts need manual mapping.").format(
                len(results["matched"]),
                len(results["unmatched"])
            ),
            title=_("Auto-Mapping Complete"),
            indicator="green"
        )

    return results


@frappe.whitelist()
def suggest_mof_code(account_name, account_number=None, root_type=None):
    """
    Get MOF code suggestions for a single account.

    Args:
        account_name: Account name
        account_number: Account number (optional)
        root_type: Root type (optional)
    """
    account = frappe._dict({
        "account_name": account_name,
        "account_number": account_number,
        "root_type": root_type
    })

    # Try to find best match
    best_match = find_best_mof_match(account)

    # Get suggestions
    suggestions = get_suggestions(account)

    return {
        "best_match": best_match,
        "suggestions": suggestions
    }
