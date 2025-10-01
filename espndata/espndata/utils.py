def american_to_decimal(american):
    """ 
    Converts American formatted betting odds to decimal formatted betting odds.
    """
    if american is None:
        return american
    elif american > 0:
        return (american / 100) + 1
    elif american < 0:
        return 1 - (100 / american)