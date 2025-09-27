import json
from .db import SessionLocal
from .models import Category, SubCategory

def seed_data():
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(SubCategory).delete()
        db.query(Category).delete()
        db.commit()

        data = [
    {
        "title": "Human",
        "description": "Human",
        "image": "",
        "id": 1,
        "subcategories": [
            {
                "title": "Omics",
                "description": "Omics",
                "image": "",
                "id": 1,
                "category_id": 1
            },
            {
                "title": "Physiology",
                "description": "Physiology",
                "image": "",
                "id": 2,
                "category_id": 1
            }
        ]
    },
    {
        "title": "Plant",
        "description": "Plant",
        "image": "",
        "id": 3,
        "subcategories": [
            {
                "title": "Gravitropism",
                "description": "Gravitropism",
                "image": "",
                "id": 3,
                "category_id": 3
            },
            {
                "title": "Cultivation",
                "description": "",
                "image": "Cultivation",
                "id": 4,
                "category_id": 3
            }
        ]
    },
    {
        "title": "Microbiology",
        "description": "Microbiology",
        "image": "",
        "id": 4,
        "subcategories": [
            {
                "title": "Microbiome",
                "description": "Microbiome",
                "image": "",
                "id": 5,
                "category_id": 4
            },
            {
                "title": "Pathogens",
                "description": "Pathogens",
                "image": "",
                "id": 6,
                "category_id": 4
            }
        ]
    },
    {
        "title": "Genomics & Multi-omics",
        "description": "Genomics & Multi-omics",
        "image": "",
        "id": 5,
        "subcategories": [
            {
                "title": "Platforms",
                "description": "Platforms",
                "image": "",
                "id": 7,
                "category_id": 5
            },
            {
                "title": "Genomics",
                "description": "Genomics",
                "image": "",
                "id": 8,
                "category_id": 5
            }
        ]
    },
    {
        "title": "Technology & Methods",
        "description": "Technology & Methods",
        "image": "",
        "id": 6,
        "subcategories": [
            {
                "title": "Microfluidics",
                "description": "Microfluidics",
                "image": "",
                "id": 9,
                "category_id": 6
            },
            {
                "title": "Biotech",
                "description": "Biotech",
                "image": "",
                "id": 10,
                "category_id": 6
            }
        ]
    }
]

        for category_data in data:
            subcategories_data = category_data.pop("subcategories", [])
            category = Category(**category_data)
            db.add(category)
            db.commit()
            db.refresh(category)
            for subcategory_data in subcategories_data:
                subcategory_data["category_id"] = category.id
                subcategory = SubCategory(**subcategory_data)
                db.add(subcategory)
            db.commit()

    finally:
        print("Data seeded successfully")
        db.close()

if __name__ == "__main__":
    seed_data()
