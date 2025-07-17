from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal
from pydantic import BaseModel, condecimal, ConfigDict, conint, Field, UUID4

from .models import PurchasedMovie


class GenreBase(BaseModel):
    name: str


class GenreCreate(GenreBase):
    pass


class GenreUpdate(GenreBase):
    name: Optional[str] = None


class GenreRead(GenreBase):
    id: int
    movie_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class StarBase(BaseModel):
    name: str


class StarCreate(StarBase):
    pass


class StarUpdate(BaseModel):
    name: Optional[str] = None


class StarRead(StarBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class DirectorBase(BaseModel):
    name: str


class DirectorCreate(DirectorBase):
    pass


class DirectorRead(DirectorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


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

    genre_ids: Optional[List[int]] = None
    director_ids: Optional[List[int]] = None
    star_ids: Optional[List[int]] = None


class MovieOut(MovieBase):
    id: int
    uuid: UUID4

    genres: Optional[List[GenreRead]] = []
    directors: Optional[List[DirectorRead]] = []
    stars: Optional[List[StarRead]] = []


    model_config = ConfigDict(from_attributes=True)


class CertificationRead(CertificationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class LikeBase(BaseModel):
    target_type: Literal["movie", "comment"]
    target_id: int
    is_like: bool


class LikeCreate(LikeBase):
    pass


class LikeRead(LikeBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


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

    certification: Optional[CertificationRead] = None
    genres: Optional[List[GenreRead]] = []
    directors: Optional[List[DirectorRead]] = []
    stars: Optional[List[StarRead]] = []

    model_config = ConfigDict(from_attributes=True)


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


class MovieRatingCreate(BaseModel):
    rating: conint(ge=1, le=10)


class MovieRatingRead(MovieRatingCreate):
    movie_id: int

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    text: str
    parent_id: Optional[int] = None


class CommentRead(BaseModel):
    id: int
    user_id: int
    movie_id: int
    parent_id: Optional[int] = None
    text: str
    created_at: datetime
    replies: Optional[List["CommentRead"]] = []

    model_config = ConfigDict(from_attributes=True)


CommentRead.model_rebuild()


class PurchasedMovieBase(BaseModel):
    movie_id: int


class PurchasedMovieCreate(PurchasedMovieBase):
    pass


class PurchasedMovieOut(BaseModel):
    id: int
    movie_id: int
    purchased_at: datetime
    name: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_purchased_movie(cls, purchased_movie: PurchasedMovie):
        return cls(
            id=purchased_movie.id,
            movie_id=purchased_movie.movie_id,
            purchased_at=purchased_movie.purchased_at,
            name=purchased_movie.movie.name,
        )
