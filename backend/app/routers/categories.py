from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db import SessionLocal
from .. import models, schemas

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("", response_model=schemas.Category)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_category = models.Category(title=category.title, description=category.description, image=category.image)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@router.get("", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    categories = db.query(models.Category).offset(skip).limit(limit).all()
    return categories

@router.get("/{category_id}", response_model=schemas.Category)
def read_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@router.put("/{category_id}", response_model=schemas.Category)
def update_category(category_id: int, category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    db_category.title = category.title
    db_category.description = category.description
    db_category.image = category.image
    db.commit()
    db.refresh(db_category)
    return db_category

@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if db_category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if db_category.subcategories:
        raise HTTPException(status_code=400, detail="Cannot delete category with subcategories")
    db.delete(db_category)
    db.commit()
    return

@router.post("/subcategories/", response_model=schemas.SubCategory)
def create_subcategory_for_category(
    subcategory: schemas.SubCategoryCreate, db: Session = Depends(get_db)
):
    db_subcategory = models.SubCategory(**subcategory.dict())
    db.add(db_subcategory)
    db.commit()
    db.refresh(db_subcategory)
    return db_subcategory

@router.get("/subcategories/", response_model=List[schemas.SubCategory])
def read_subcategories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    subcategories = db.query(models.SubCategory).offset(skip).limit(limit).all()
    return subcategories

@router.put("/subcategories/{subcategory_id}", response_model=schemas.SubCategory)
def update_subcategory(subcategory_id: int, subcategory: schemas.SubCategoryCreate, db: Session = Depends(get_db)):
    db_subcategory = db.query(models.SubCategory).filter(models.SubCategory.id == subcategory_id).first()
    if db_subcategory is None:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    db_subcategory.title = subcategory.title
    db_subcategory.description = subcategory.description
    db_subcategory.image = subcategory.image
    db_subcategory.category_id = subcategory.category_id
    db.commit()
    db.refresh(db_subcategory)
    return db_subcategory

@router.delete("/subcategories/{subcategory_id}", status_code=204)
def delete_subcategory(subcategory_id: int, db: Session = Depends(get_db)):
    db_subcategory = db.query(models.SubCategory).filter(models.SubCategory.id == subcategory_id).first()
    if db_subcategory is None:
        raise HTTPException(status_code=404, detail="SubCategory not found")
    db.delete(db_subcategory)
    db.commit()
    return
