def american_to_decimal(american):
    """ 
    Converts American formatted betting odds to decimal formatted betting odds.
    Implicitly returns None is `american` is None (or falsy).
    """
    if american:
        american = int(american)

        if american > 0:
            return (american / 100) + 1
        elif american < 0:
            return 1 - (100 / american)