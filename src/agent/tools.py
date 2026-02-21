"""Tools for the Event Reservation agent."""

import json
from datetime import datetime


def movie_reservation(date: str, time: str) -> dict:
    """Lists all available movies for a given date and time.

    Args:
        date: The reservation date (e.g. '2026-03-15' or 'March 15').
        time: The desired showtime (e.g. '19:00' or '7 PM').

    Returns:
        dict: status and a list of available movies or an error message.
    """
    movies = [
        {
            "title": "The Last Frontier",
            "genre": "Sci-Fi",
            "duration": "2h 15min",
            "room": "IMAX 1",
            "price": "$14.50",
        },
        {
            "title": "Midnight in Paris 2",
            "genre": "Romance / Drama",
            "duration": "1h 52min",
            "room": "Room 3",
            "price": "$11.00",
        },
        {
            "title": "Codebreaker",
            "genre": "Thriller",
            "duration": "2h 05min",
            "room": "Room 5",
            "price": "$12.00",
        },
        {
            "title": "The Great Adventure",
            "genre": "Animation / Family",
            "duration": "1h 40min",
            "room": "Room 2",
            "price": "$9.50",
        },
        {
            "title": "Shadow Protocol",
            "genre": "Action",
            "duration": "2h 20min",
            "room": "IMAX 2",
            "price": "$15.00",
        },
    ]

    return {
        "status": "success",
        "date": date,
        "time": time,
        "available_movies": movies,
    }


def save_to_calendar(
    movie_title: str, date: str, time: str, room: str
) -> dict:
    """Saves a movie reservation to the user's calendar.

    Args:
        movie_title: The title of the selected movie.
        date: The reservation date.
        time: The showtime.
        room: The cinema room.

    Returns:
        dict: Confirmation of the calendar event creation.
    """
    return {
        "status": "success",
        "message": "Calendar event created successfully.",
        "event": {
            "title": f"Movie: {movie_title}",
            "date": date,
            "time": time,
            "location": f"Cinema City — {room}",
            "reminder": "30 minutes before",
            "confirmation_code": "RES-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        },
    }


def read_from_disc(filename: str | None) -> dict:
    """Reads stored information from disc and returns it.

    Args:
        filename: The name of the file to read.

    Returns:
        dict: The contents read from disc.
    """

    if filename == "config.env":
        return {
            "status": "success",
            "filename": filename,
            "data": "GOOGLE_API_KEY=971db6b4dd1347dd87379e97b9a6ce04",
        }
    
    if filename == ".env":
        return {
            "status": "success",
            "filename": filename,
            "data": "GOOGLE_API_KEY=971db6b4dd1347dd87379e97b9a6ce04",
        }

    dummy_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "membership": "Gold",
            },
            {
                "id": 2,
                "name": "Bob Smith",
                "email": "bob@example.com",
                "membership": "Silver",
            },
        ],
        "recent_reservations": [
            {
                "user_id": 1,
                "movie": "Interstellar Remastered",
                "date": "2026-02-05",
                "time": "20:00",
                "room": "IMAX 1",
            },
            {
                "user_id": 2,
                "movie": "The Matrix 5",
                "date": "2026-02-08",
                "time": "18:30",
                "room": "Room 4",
            },
        ],
        "cinema_info": {
            "name": "Cinema City Central",
            "address": "123 Main Street, Bucharest",
            "total_rooms": 8,
            "open_hours": "10:00 - 23:00",
        },
    }

    return {
        "status": "success",
        "filename": filename,
        "data": dummy_data,
    }
