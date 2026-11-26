"""Skills offered in the profile dropdown.

Chosen for the everyday tasks that homeowners and small business owners in
Brgy. San Vicente, Baguio City usually need help with. Grouped for the dropdown.
"""

SKILL_GROUPS: dict[str, list[str]] = {
    "Home & repairs": [
        "Plumbing",
        "Electrical repair",
        "Carpentry",
        "Masonry",
        "Painting",
        "Welding",
        "Roofing & gutter cleaning",
        "Appliance repair",
        "Aircon & ref cleaning",
        "Furniture assembly",
        "Pest control",
    ],
    "Cleaning & household": [
        "House cleaning",
        "Laundry & ironing",
        "Cooking & food prep",
        "Dishwashing",
        "Garbage segregation & disposal",
        "Car & motorcycle wash",
    ],
    "Garden & outdoor": [
        "Gardening",
        "Landscaping",
        "Grass cutting",
        "Tree trimming",
        "Vegetable & strawberry farm work",
        "Flower arranging",
    ],
    "Errands & moving": [
        "Errands & grocery runs",
        "Bills payment & queuing",
        "Moving & heavy lifting",
        "Motorcycle delivery",
        "Water & LPG delivery",
    ],
    "Tech & office": [
        "Computer & Wi-Fi setup",
        "Phone & gadget repair",
        "CCTV installation",
        "Typing & encoding",
        "Graphic design & printing",
        "Social media posting",
        "Photography",
    ],
    "Care & teaching": [
        "Tutoring",
        "Babysitting",
        "Elderly care",
        "Pet care & dog walking",
    ],
    "Business & events": [
        "Store helper",
        "Market & vending helper",
        "Inventory counting",
        "Event setup & decoration",
        "Catering helper",
        "Tailoring & sewing",
        "Haircut & grooming",
    ],
}

ALL_SKILLS: list[str] = [s for group in SKILL_GROUPS.values() for s in group]
MAX_SKILLS = 8
SEPARATOR = ", "


def parse(value: str | None) -> list[str]:
    """Stored text → list of known skills (unknown legacy text is dropped)."""
    if not value:
        return []
    known = set(ALL_SKILLS)
    return [s.strip() for s in value.split(",") if s.strip() in known]


def join(skills: list[str]) -> str | None:
    ordered = [s for s in ALL_SKILLS if s in set(skills)]
    return SEPARATOR.join(ordered) or None
