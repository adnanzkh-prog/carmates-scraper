def score_listing_au(l):

    score = 0
    text = (l.title + l.description).lower()

    brands = ["toyota","mazda","ford","hyundai","kia"]
    for b in brands:
        if b in text:
            score += 2

    if l.price and 3000 <= l.price <= 80000:
        score += 3

    if l.contact_numbers:
        score += 2

    return score
