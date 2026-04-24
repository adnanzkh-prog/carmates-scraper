def is_valid_listing_au(l):

    text = (l.title + l.description).lower()

    junk = ["wrecking", "parts", "engine", "tyres", "rims", "rent"]
    if any(k in text for k in junk):
        return False

    if l.price and (l.price < 1000 or l.price in [1,123,999]):
        return False

    return True
