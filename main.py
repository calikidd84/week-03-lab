from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, conint, field_validator
from typing import Optional, Literal

app = FastAPI(title="Book Tracker API", version="1.0.0")

# Pydantic models for validation
BookStatus = Literal["want_to_read", "reading", "read"]

class BookCreate(BaseModel):
    title: str
    author: str
    status: BookStatus = "want_to_read"
    rating: Optional[conint(ge=1, le=5)] = None

    @field_validator("rating")
    def rating_only_for_read(cls, value, info):
        if value is not None and info.data.get("status") != "read":
            raise ValueError('rating is only allowed when status is "read"')
        return value

class BookUpdate(BaseModel):
    status: Optional[BookStatus] = None
    rating: Optional[conint(ge=1, le=5)] = None

# In-memory storage
books_db = [
    {
        "title": "Python Crash Course",
        "author": "Eric Matthes",
        "status": "want_to_read",
        "rating": None,
    },
    {
        "title": "Automate the Boring Stuff with Python",
        "author": "Al Sweigart",
        "status": "reading",
        "rating": None,
    },
    {
        "title": "Fluent Python",
        "author": "Luciano Ramalho",
        "status": "read",
        "rating": 5,
    },
    {
        "title": "Effective Python",
        "author": "Brett Slatkin",
        "status": "read",
        "rating": 4,
    },
    {
        "title": "Python Cookbook",
        "author": "David Beazley & Brian K. Jones",
        "status": "want_to_read",
        "rating": None,
    },
]
next_id = 1

# create an in init book id field for each book in the books_db list, starting from 1 using a constructor
# use the next_id variable to keep track of the next id to assign, and increment it for each book in the list. You can do this in a loop after defining the books_db list, before defining the API endpoints.
def initialize_books_db():
    global books_db
    global next_id
    for book in books_db:
        book["id"] = next_id
        next_id += 1

initialize_books_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to Book Tracker API"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/books")
def get_books(status: Optional[BookStatus] = None):
    if status:
        return [book for book in books_db if book["status"] == status]
    return books_db

@app.get("/books/stats")
def get_stats():
    total = len(books_db)
    # Count by status
    want_to_read = sum(1 for book in books_db if book["status"] == "want_to_read")
    reading = sum(1 for book in books_db if book["status"] == "reading")
    read = sum(1 for book in books_db if book["status"] == "read")
    # Calculate average rating for "read" books (avoid division by zero!)
    read_books = [book for book in books_db if book["status"] == "read"]
    average_rating = sum(book["rating"] for book in read_books) / len(read_books) if read_books else 0
    # Return a stats dict
    return {
        "total": total,
        "want_to_read": want_to_read,
        "reading": reading,
        "read": read,
        "average_rating": average_rating
    }

@app.get("/books/{book_id}")
def get_book(book_id: int):
    # Find the book with matching id
    book = next((b for b in books_db if b["id"] == book_id), None)
    # If not found, raise HTTPException(status_code=404, detail="Book not found")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.post("/books", status_code=201)
def create_book(book: BookCreate):
    global next_id
    # Create a dict from the Pydantic model + add id
    book_dict = book.model_dump()   
    book_dict["id"] = next_id
    # Append to books_db
    books_db.append(book_dict)
    # Increment next_id
    next_id += 1
    # Return the created book
    return book_dict

@app.put("/books/{book_id}")
def update_book(book_id: int, updates: BookUpdate):
    # Find the book
    book = next((b for b in books_db if b["id"] == book_id), None)
    # If not found, raise HTTPException(status_code=404, detail="Book not found")
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # Validate rating/status combination before applying updates.
    requested_status = updates.status if updates.status is not None else book["status"]
    if updates.rating is not None and requested_status != "read":
        raise HTTPException(
            status_code=400,
            detail='rating is only allowed when status is "read"',
        )
    # Update only the fields that are provided (not None)
    for field, value in updates.model_dump().items():
        if value is not None:
            book[field] = value
    # Return the updated book
    return book

@app.delete("/books/{book_id}", status_code=204)
def delete_book(book_id: int):
    # Find the book by id
    book = next((b for b in books_db if b["id"] == book_id), None)
    # Return 404 if not found
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # Remove it from books_db
    books_db.remove(book)
    # Return a confirmation message
    return Response(status_code=204)