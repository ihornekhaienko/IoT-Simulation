from math import log

def inv_cdf(params):
    return -log(1 - params['e']) / params.get('y', 5)
    
