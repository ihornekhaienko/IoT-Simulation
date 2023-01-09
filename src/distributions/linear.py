from math import sqrt

# pdf(x) = 2x, x in [0, 1]
# cdf(x) = x^2, x in [0, 1]
# inv_cdf(e) = x, e in [0, 1]
def inv_cdf(params):
    return sqrt(params['e'])
    
