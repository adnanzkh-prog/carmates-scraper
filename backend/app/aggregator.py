from scraper_fb import scrape_facebook

async def aggregate(query):
    fb = await scrape_facebook(query)

    # placeholders for future
    carsales = []
    gumtree = []

    return fb + carsales + gumtree
