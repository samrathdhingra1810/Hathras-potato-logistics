"""English / Hindi display strings shared by the templates and the voice features.

Display only: block ids match core.dataset.BLOCKS, which is not changed. Hindi was
written for this project and should be reviewed by a native speaker before release.
"""
from __future__ import annotations

# Hindi names of the Hathras development blocks.
BLOCK_HI = {
    "hathras": "हाथरस",
    "sasni": "सासनी",
    "sikandra-rao": "सिकंदराराऊ",
    "sadabad": "सादाबाद",
    "mursan": "मुरसान",
    "sahpau": "सहपऊ",
    "hasayan": "हसायन",
}

# Extra spellings speech recognition commonly returns (English and Hindi script).
BLOCK_ALIASES = {
    "hathras": ["hathras", "hatras", "हाथरस", "हातरस"],
    "sasni": ["sasni", "sasani", "saasni", "सासनी", "ससनी"],
    "sikandra-rao": ["sikandra rao", "sikandrarao", "sikandra", "sikander rao", "सिकंदराराऊ", "सिकंदरा राऊ", "सिकन्दराराऊ", "सिकंदरा"],
    "sadabad": ["sadabad", "saadabad", "sadabaad", "सादाबाद", "सदाबाद"],
    "mursan": ["mursan", "mursaan", "मुरसान", "मुरसन"],
    "sahpau": ["sahpau", "sahpaw", "sahpo", "सहपऊ", "सहपउ", "सहपौ"],
    "hasayan": ["hasayan", "hasain", "hasaayan", "हसायन", "हसैन"],
}

MONTH_HI = {"Jan": "जनवरी", "Feb": "फ़रवरी", "Mar": "मार्च", "Apr": "अप्रैल", "May": "मई", "Jun": "जून",
            "Jul": "जुलाई", "Aug": "अगस्त", "Sep": "सितंबर", "Oct": "अक्टूबर", "Nov": "नवंबर", "Dec": "दिसंबर"}
MONTH_EN = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June",
            "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"}


def block_aliases(blocks: list[dict]) -> list[dict]:
    """[{id, name, hi, aliases}] for voice matching, from the dataset's block list."""
    return [{"id": b["id"], "name": b["name"], "hi": BLOCK_HI.get(b["id"], b["name"]),
             "aliases": [b["name"].lower(), *BLOCK_ALIASES.get(b["id"], [])]} for b in blocks]


def spoken_tonnes(t: float) -> str:
    """Tonnes rounded to the nearest 100 for reading aloud, e.g. 13,300."""
    return f"{int(round(t, -2)):,}"
