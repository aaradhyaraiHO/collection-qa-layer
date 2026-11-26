"""Title tags used by assortment checks.

Tags are inferred from the public title and stored on the spec. They are a
reading of the title, not a Headout taxonomy.
"""

from __future__ import annotations


def infer_tags(
    title: str,
    *,
    multi_variant: bool = False,
    combo: bool = False,
    category: str | None = None,
) -> list[str]:
    text = title.lower()
    tags: list[str] = []
    if combo:
        tags.append("combo")
    if "fly-in" in text or "fly in" in text:
        tags.append("fly_in")
    if "helicopter" in text:
        tags.append("helicopter")
    if "day trip" in text or "day tour" in text or "private day trip" in text:
        tags.append("day_trip")
    if "queenstown" in text:
        tags.append("from_queenstown")
    if "te anau" in text:
        tags.append("from_te_anau")
    if "manapouri" in text or "doubtful" in text:
        tags.append("doubtful_sound")
    if "nakuru" in text:
        tags.append("lake_nakuru")
    if "naivasha" in text:
        tags.append("lake_naivasha")
    if "amboseli" in text:
        tags.append("amboseli")
    if "glowworm" in text:
        tags.append("glowworm")
    if any(word in text for word in ("luxury", "business class", "ultra premium", "vip")):
        tags.append("luxury")
    if "budget" in text or "camping" in text:
        tags.append("budget_camping")
    if "private" in text:
        tags.append("private")
    if "small-group" in text or "small group" in text or "boutique" in text:
        tags.append("small_group")
    if "overnight" in text:
        tags.append("overnight")
    if multi_variant:
        tags.append("multi_variant")
    if "masai mara" in text or "maasai mara" in text:
        tags.append("masai_mara")
        if not any(tag in tags for tag in ("lake_nakuru", "lake_naivasha", "amboseli")):
            tags.append("mara_only")
    if "milford" in text:
        tags.append("milford_sound")
    terminal_cruise = (
        "cruise" in text
        and "day trip" not in text
        and "day tour" not in text
        and "overnight" not in text
        and "from queenstown" not in text
        and "from te anau" not in text
        and "from manapouri" not in text
    )
    if terminal_cruise:
        tags.append("terminal_cruise")
    if category:
        tags.append("category:" + category.lower().replace(" & ", "_").replace(" ", "_"))
    return tags
