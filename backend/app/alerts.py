def detect_underpriced(listings):

    avg_price = sum([l.price for l in listings if l.price]) / max(len(listings),1)

    deals = []

    for l in listings:
        if l.price and l.price < avg_price * 0.7:
            deals.append(l)

    return deals
