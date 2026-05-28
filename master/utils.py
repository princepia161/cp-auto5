import random
from logger import LOGGER
from master.server import scraper


async def send_random_photo():
    """Return a random photo URL for bot messages. Add your telegra.ph URLs here."""
    regex_photo = [
        # Add telegra.ph image URLs here:
        # "https://telegra.ph/file/your-image.jpg",
    ]
    if not regex_photo:
        return None
    pht = random.choice(regex_photo)
    try:
        response = await scraper.get(pht)
        if response.status_code == 200:
            return pht
        return None
    except:
        return None
