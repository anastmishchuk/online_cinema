from sqlalchemy.orm import Session, configure_mappers

from src.config.database import sync_engine, SessionLocal
from src.movies.models import *
from src.users.models import *
from src.orders.models import *
from src.cart.models import *
from src.payment.models import *

configure_mappers()


def create_test_data():
    """Create all test data for the movie database in a single function"""
    Base.metadata.create_all(bind=sync_engine)

    db = SessionLocal()

    try:
        test_data = {
            "genres": ["Action", "Comedy", "Drama", "Sci-Fi", "Thriller", "Crime"],
            "certifications": ["PG-13", "R"],
            "directors": [
                "Christopher Nolan",
                "Quentin Tarantino",
                "Denis Villeneuve"
            ],
            "stars": [
                "Leonardo DiCaprio", "Brad Pitt", "Marion Cotillard", "Tom Hardy",
                "Cillian Murphy", "Ryan Gosling", "Harrison Ford", "Ana de Armas",
                "Margot Robbie", "John Travolta", "Samuel L. Jackson", "Uma Thurman"
            ],
            "movies": [
                {
                    "name": "Inception",
                    "year": 2010,
                    "time": 148,
                    "imdb": 8.8,
                    "votes": 2400000,
                    "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.",
                    "price": 12.99,
                    "certification": "PG-13",
                    "genres": ["Action", "Sci-Fi", "Thriller"],
                    "directors": ["Christopher Nolan"],
                    "stars": ["Leonardo DiCaprio", "Marion Cotillard", "Tom Hardy", "Cillian Murphy"]
                },
                {
                    "name": "Blade Runner 2049",
                    "year": 2017,
                    "time": 164,
                    "imdb": 8.0,
                    "votes": 520000,
                    "description": "Young Blade Runner K's discovery of a long-buried secret leads him to track down former Blade Runner Rick Deckard, who's been missing for thirty years.",
                    "price": 14.99,
                    "certification": "R",
                    "genres": ["Action", "Drama", "Sci-Fi"],
                    "directors": ["Denis Villeneuve"],
                    "stars": ["Ryan Gosling", "Harrison Ford", "Ana de Armas"]
                },
                {
                    "name": "Pulp Fiction",
                    "year": 1994,
                    "time": 154,
                    "imdb": 8.9,
                    "votes": 2100000,
                    "description": "The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.",
                    "price": 11.99,
                    "certification": "R",
                    "genres": ["Crime", "Drama"],
                    "directors": ["Quentin Tarantino"],
                    "stars": ["John Travolta", "Samuel L. Jackson", "Uma Thurman"]
                }
            ]
        }

        def get_or_create(model_class, **kwargs):
            obj = db.query(model_class).filter_by(**kwargs).first()
            if not obj:
                obj = model_class(**kwargs)
                db.add(obj)
            return obj

        genre_objects = {}
        for genre_name in test_data["genres"]:
            genre_objects[genre_name] = get_or_create(Genre, name=genre_name)

        cert_objects = {}
        for cert_name in test_data["certifications"]:
            cert_objects[cert_name] = get_or_create(Certification, name=cert_name)

        director_objects = {}
        for director_name in test_data["directors"]:
            director_objects[director_name] = get_or_create(Director, name=director_name)

        star_objects = {}
        for star_name in test_data["stars"]:
            star_objects[star_name] = get_or_create(Star, name=star_name)

        db.commit()

        movies_created = 0
        for movie_data in test_data["movies"]:
            existing_movie = db.query(Movie).filter_by(name=movie_data["name"]).first()
            if existing_movie:
                continue

            movie = Movie(
                name=movie_data["name"],
                year=movie_data["year"],
                time=movie_data["time"],
                imdb=movie_data["imdb"],
                votes=movie_data["votes"],
                description=movie_data["description"],
                price=movie_data["price"],
                certification_id=cert_objects[movie_data["certification"]].id
            )
            db.add(movie)
            db.commit()

            for genre_name in movie_data["genres"]:
                if genre_name in genre_objects:
                    movie.genres.append(genre_objects[genre_name])

            for director_name in movie_data["directors"]:
                if director_name in director_objects:
                    movie.directors.append(director_objects[director_name])

            for star_name in movie_data["stars"]:
                if star_name in star_objects:
                    movie.stars.append(star_objects[star_name])

            movies_created += 1

        db.commit()

        print("Test data created successfully!")
        print(f"Added {movies_created} movies to the database!")
        print(f"Added {len(test_data['genres'])} genres")
        print(f"Added {len(test_data['certifications'])} certifications")
        print(f"Added {len(test_data['directors'])} directors")
        print(f"Added {len(test_data['stars'])} stars")

    except Exception as e:
        print(f"Error creating test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()