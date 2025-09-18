def convert_to_decimal(american):
    """ 
    Converts American format betting odds to decimal form.
    """
    if american < 0:
        return (american / 100) + 1
    if american > 0:
        return 1 - (100 / american)