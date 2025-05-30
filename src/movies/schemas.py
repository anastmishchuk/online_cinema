from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, condecimal, UUID4, Field


class GenreBase(BaseModel):
    name: str


class GenreCreate(GenreBase):
    pass


class GenreUpdate(GenreBase):
    name: Optional[str] = None


class GenreRead(GenreBase):
    id: int

    class Config:
        orm_mode = True


class StarBase(BaseModel):
    name: str


class StarCreate(StarBase):
    pass


class StarUpdate(BaseModel):
    name: Optional[str] = None


class StarRead(StarBase):
    id: int

    class Config:
        orm_mode = True


class DirectorBase(BaseModel):
    name: str


class DirectorCreate(DirectorBase):
    pass


class CertificationBase(BaseModel):
    name: str


class CertificationCreate(CertificationBase):
    pass


class MovieBase(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: condecimal(max_digits=10, decimal_places=2)
    certification_id: int


class MovieCreate(MovieBase):
    genre_ids: List[int] = Field(default_factory=list)
    director_ids: List[int] = Field(default_factory=list)
    star_ids: List[int] = Field(default_factory=list)


class MovieUpdate(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[condecimal(max_digits=10, decimal_places=2)] = None
    certification_id: Optional[int] = None


class MovieOut(MovieBase):
    id: int
    uuid: str

    class Config:
        orm_mode = True




class StarRead(StarBase):
    id: int

    class Config:
        orm_mode = True


class DirectorRead(DirectorBase):
    id: int

    class Config:
        orm_mode = True


class CertificationRead(CertificationBase):
    id: int

    class Config:
        orm_mode = True


class MovieRead(BaseModel):
    id: int
    uuid: UUID4
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: Decimal

    certification: CertificationRead
    genres: List[GenreRead]
    directors: List[DirectorRead]
    stars: List[StarRead]

    class Config:
        orm_mode = True


class MovieFilter(BaseModel):
    year: Optional[int] = None
    min_imdb: Optional[float] = None
    max_imdb: Optional[float] = None
    min_meta_score: Optional[float] = None
    max_meta_score: Optional[float] = None
    certification_id: Optional[int] = None
    star_name: Optional[str] = None
    director_name: Optional[str] = None
    search: Optional[str] = None
    sort: Optional[str] = None
    page: int = 1
    page_size: int = 10
